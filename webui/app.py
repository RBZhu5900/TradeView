"""
WebUI 后端服务

基于FastAPI的回测系统Web界面后端。
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.requests import Request

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backtester.engine import BacktestEngine, load_strategy, list_strategies
from backtester.data_manager import DataManager
from backtester.config_manager import ConfigManager

# 创建FastAPI应用
app = FastAPI(
    title="PythonTradeView",
    description="策略隔离交易回测系统",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件和模板
WEBUI_DIR = Path(__file__).parent
STATIC_DIR = WEBUI_DIR / "static"
TEMPLATES_DIR = WEBUI_DIR / "templates"

# 确保目录存在
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ============= Pydantic 模型 =============

class BacktestRequest(BaseModel):
    """回测请求"""
    strategy: str
    symbol: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 100000.0
    params: Optional[Dict[str, Any]] = None


class AddSymbolRequest(BaseModel):
    """添加股票请求"""
    symbol: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class SaveConfigRequest(BaseModel):
    """保存配置请求"""
    strategy: str
    params: Dict[str, Any]
    name: Optional[str] = None
    symbol: Optional[str] = None
    config_id: Optional[str] = None
    description: Optional[str] = None


class ImportConfigRequest(BaseModel):
    """导入配置请求"""
    json_data: str


# ============= 页面路由 =============

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})


# ============= API 路由 =============

@app.get("/api/strategies")
async def get_strategies() -> Dict[str, Any]:
    """获取所有可用策略"""
    try:
        strategies = list_strategies()
        return {
            "success": True,
            "data": strategies
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "data": []
        }


@app.get("/api/symbols")
async def get_symbols() -> Dict[str, Any]:
    """获取可用的股票代码列表（包括推荐的热门股票）"""
    try:
        dm = DataManager()
        symbols = dm.list_available_symbols()
        return {
            "success": True,
            "data": symbols
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "data": []
        }


@app.get("/api/symbols/local")
async def get_local_symbols() -> Dict[str, Any]:
    """获取本地已下载的股票数据详情"""
    try:
        dm = DataManager()
        data = dm.list_local_data()
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "data": []
        }


@app.post("/api/symbols/add")
async def add_symbol(request: AddSymbolRequest) -> Dict[str, Any]:
    """添加/下载新股票数据"""
    try:
        dm = DataManager()
        result = dm.add_symbol(
            request.symbol,
            request.start_date,
            request.end_date
        )
        
        if result['success']:
            return {
                "success": True,
                "message": f"成功下载 {result['symbol']} 数据，共 {result['records']} 条",
                "data": result
            }
        else:
            return {
                "success": False,
                "message": result.get('error', '下载失败'),
                "data": None
            }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "data": None
        }


@app.delete("/api/symbols/{symbol}")
async def delete_symbol(symbol: str) -> Dict[str, Any]:
    """删除股票数据"""
    try:
        dm = DataManager()
        success = dm.delete_symbol(symbol)
        
        if success:
            return {
                "success": True,
                "message": f"已删除 {symbol} 的数据"
            }
        else:
            return {
                "success": False,
                "message": f"{symbol} 数据不存在"
            }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@app.get("/api/strategy/{strategy_name}")
async def get_strategy_detail(strategy_name: str) -> Dict[str, Any]:
    """获取策略详情"""
    try:
        import importlib
        module = importlib.import_module(f'strategies.{strategy_name}')
        metadata = getattr(module, 'STRATEGY_METADATA', {})
        
        return {
            "success": True,
            "data": {
                "module": strategy_name,
                **metadata
            }
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"策略不存在: {e}")


# ============= 配置管理 API =============

@app.get("/api/configs")
async def list_configs(
    strategy: Optional[str] = None,
    symbol: Optional[str] = None
) -> Dict[str, Any]:
    """获取配置列表"""
    try:
        cm = ConfigManager()
        configs = cm.list_configs(strategy=strategy, symbol=symbol)
        return {
            "success": True,
            "data": configs
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "data": []
        }


@app.get("/api/configs/{config_id}")
async def get_config(config_id: str) -> Dict[str, Any]:
    """获取指定配置"""
    try:
        cm = ConfigManager()
        config = cm.get_config(config_id)
        
        if config:
            return {
                "success": True,
                "data": config
            }
        else:
            return {
                "success": False,
                "message": "配置不存在",
                "data": None
            }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "data": None
        }


@app.post("/api/configs")
async def save_config(request: SaveConfigRequest) -> Dict[str, Any]:
    """保存配置"""
    try:
        cm = ConfigManager()
        config = cm.save_config(
            strategy=request.strategy,
            params=request.params,
            name=request.name,
            symbol=request.symbol,
            config_id=request.config_id,
            description=request.description
        )
        
        return {
            "success": True,
            "message": "配置已保存",
            "data": config
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "data": None
        }


@app.delete("/api/configs/{config_id}")
async def delete_config(config_id: str) -> Dict[str, Any]:
    """删除配置"""
    try:
        cm = ConfigManager()
        success = cm.delete_config(config_id)
        
        if success:
            return {
                "success": True,
                "message": "配置已删除"
            }
        else:
            return {
                "success": False,
                "message": "配置不存在"
            }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@app.post("/api/configs/{config_id}/duplicate")
async def duplicate_config(config_id: str, new_name: Optional[str] = None) -> Dict[str, Any]:
    """复制配置"""
    try:
        cm = ConfigManager()
        config = cm.duplicate_config(config_id, new_name)
        
        if config:
            return {
                "success": True,
                "message": "配置已复制",
                "data": config
            }
        else:
            return {
                "success": False,
                "message": "原配置不存在"
            }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@app.get("/api/configs/{config_id}/export")
async def export_config(config_id: str) -> Dict[str, Any]:
    """导出配置"""
    try:
        cm = ConfigManager()
        json_str = cm.export_config(config_id)
        
        if json_str:
            return {
                "success": True,
                "data": json_str
            }
        else:
            return {
                "success": False,
                "message": "配置不存在"
            }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@app.post("/api/configs/import")
async def import_config(request: ImportConfigRequest) -> Dict[str, Any]:
    """导入配置"""
    try:
        cm = ConfigManager()
        config = cm.import_config(request.json_data)
        
        if config:
            return {
                "success": True,
                "message": "配置已导入",
                "data": config
            }
        else:
            return {
                "success": False,
                "message": "导入失败，请检查JSON格式"
            }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


# ============= 回测 API =============

@app.post("/api/backtest")
async def run_backtest_api(request: BacktestRequest) -> Dict[str, Any]:
    """运行回测"""
    try:
        # 验证策略存在
        try:
            strategy = load_strategy(request.strategy, request.params)
        except ImportError as e:
            return {
                "success": False,
                "message": f"策略加载失败: {e}",
                "data": None
            }
        
        # 加载数据（自动下载如果不存在）
        dm = DataManager()
        try:
            data = dm.get_data(
                request.symbol, 
                request.start_date, 
                request.end_date
            )
        except Exception as e:
            return {
                "success": False,
                "message": f"数据加载失败: {e}",
                "data": None
            }
        
        # 运行回测
        engine = BacktestEngine(strategy, data, request.initial_capital)
        results = engine.run(verbose=False)
        
        # 简化权益曲线数据（采样以减少数据量）
        equity_curve = results.get('equity_curve', [])
        if len(equity_curve) > 500:
            step = len(equity_curve) // 500
            equity_curve = equity_curve[::step]
        results['equity_curve'] = equity_curve
        
        return {
            "success": True,
            "message": "回测完成",
            "data": results
        }
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "message": f"回测执行错误: {e}",
            "data": None
        }


@app.get("/api/data/{symbol}")
async def get_stock_data(
    symbol: str,
    start: Optional[str] = None,
    end: Optional[str] = None
) -> Dict[str, Any]:
    """获取股票数据（自动下载如果不存在）"""
    try:
        dm = DataManager()
        data = dm.get_data(symbol, start, end)
        
        # 转换为JSON友好格式
        records = []
        for idx, row in data.iterrows():
            records.append({
                "date": idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": float(row.get('volume', 0))
            })
        
        # 采样以减少数据量
        if len(records) > 1000:
            step = len(records) // 1000
            records = records[::step]
        
        return {
            "success": True,
            "data": {
                "symbol": symbol.upper(),
                "records": records,
                "count": len(records)
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "data": None
        }


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


# ============= 主入口 =============

def main():
    """启动开发服务器"""
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(PROJECT_ROOT)]
    )


if __name__ == "__main__":
    main()
