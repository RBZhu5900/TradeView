#!/usr/bin/env python3
"""
PythonTradeView 启动脚本

用法:
    python run.py          # 启动 WebUI 服务
    python run.py backtest # 运行命令行回测
"""

import sys
import os

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


def run_webui():
    """启动 WebUI 服务"""
    try:
        import uvicorn
        print("=" * 60)
        print("  PythonTradeView - 策略回测系统")
        print("=" * 60)
        print()
        print("  启动 WebUI 服务...")
        print("  访问地址: http://localhost:8000")
        print()
        print("  按 Ctrl+C 停止服务")
        print("=" * 60)
        print()
        
        # 使用模块路径而非切换目录
        uvicorn.run(
            "webui.app:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=[PROJECT_ROOT]
        )
    except ImportError as e:
        print(f"错误: {e}")
        print("请先安装依赖:")
        print("  pip install -r requirements.txt")
        sys.exit(1)


def run_backtest():
    """运行命令行回测"""
    from backtester.engine import main
    main()


def main():
    """主入口"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'backtest':
            # 移除 'backtest' 参数，传递剩余参数给回测引擎
            sys.argv = [sys.argv[0]] + sys.argv[2:]
            run_backtest()
        elif command == 'webui':
            run_webui()
        elif command == 'help':
            print(__doc__)
        else:
            print(f"未知命令: {command}")
            print(__doc__)
    else:
        # 默认启动 WebUI
        run_webui()


if __name__ == '__main__':
    main()
