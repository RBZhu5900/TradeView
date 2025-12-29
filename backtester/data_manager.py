"""
数据管理模块

负责数据加载、下载、预处理和缓存。
支持本地CSV文件和yfinance在线数据。
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd


class DataManager:
    """
    数据管理器
    
    统一管理回测所需的行情数据。
    自动从yfinance下载缺失的数据。
    """
    
    # 默认热门股票列表
    DEFAULT_SYMBOLS = ['AAPL', 'TSLA', 'GOOGL', 'MSFT', 'AMZN', 'META', 'NVDA', 'SPY', 'QQQ']
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化数据管理器
        
        Args:
            data_dir: 数据目录路径，默认为 backtester/data
        """
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), 'data')
        self.data_dir = data_dir
        self._cache: Dict[str, pd.DataFrame] = {}
        
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)
    
    def download_from_yfinance(self, symbol: str, start: str, end: str, 
                                interval: str = '1d') -> pd.DataFrame:
        """
        从yfinance下载数据
        
        Args:
            symbol: 股票代码（如 'AAPL', 'TSLA'）
            start: 开始日期 (YYYY-MM-DD)
            end: 结束日期 (YYYY-MM-DD)
            interval: 数据周期 ('1d', '1h', '5m' 等)
        
        Returns:
            DataFrame格式的OHLCV数据
        """
        try:
            import yfinance as yf
        except ImportError:
            raise ImportError("请安装 yfinance: pip install yfinance")
        
        print(f"正在从 yfinance 下载 {symbol} 数据...")
        print(f"  时间范围: {start} 到 {end}")
        
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start, end=end, interval=interval)
        
        if df.empty:
            raise ValueError(f"无法获取 {symbol} 的数据，请检查股票代码是否正确")
        
        # 标准化列名为小写
        df.columns = df.columns.str.lower()
        
        # 只保留需要的列
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        available_cols = [col for col in required_cols if col in df.columns]
        df = df[available_cols]
        
        # 确保索引是日期类型，并重命名
        df.index.name = 'date'
        
        print(f"  下载完成: {len(df)} 条数据")
        return df
    
    def save_data(self, df: pd.DataFrame, symbol: str) -> str:
        """
        保存数据到CSV（标准格式）
        
        Args:
            df: 数据DataFrame
            symbol: 股票代码
        
        Returns:
            保存的文件路径
        """
        filepath = os.path.join(self.data_dir, f"{symbol.upper()}.csv")
        df.to_csv(filepath)
        print(f"  数据已保存: {filepath}")
        return filepath
    
    def load_csv(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        从本地CSV文件加载数据
        
        Args:
            symbol: 股票代码
        
        Returns:
            DataFrame格式的OHLCV数据，如果文件不存在返回None
        """
        filepath = os.path.join(self.data_dir, f"{symbol.upper()}.csv")
        
        if not os.path.exists(filepath):
            return None
        
        try:
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            df.columns = df.columns.str.lower()
            
            # 确保数据类型正确
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 删除无效数据
            df = df.dropna()
            
            return df
        except Exception as e:
            print(f"警告: 加载 {filepath} 失败: {e}")
            return None
    
    def get_data(self, symbol: str, start: Optional[str] = None, 
                 end: Optional[str] = None, force_download: bool = False) -> pd.DataFrame:
        """
        获取股票数据（统一接口）
        
        自动判断是否需要下载数据：
        1. 如果本地有数据且覆盖请求的时间范围，直接使用
        2. 否则从yfinance下载并保存到本地
        
        Args:
            symbol: 股票代码
            start: 开始日期 (YYYY-MM-DD)
            end: 结束日期 (YYYY-MM-DD)
            force_download: 强制重新下载
        
        Returns:
            DataFrame格式的OHLCV数据
        """
        symbol = symbol.upper()
        
        # 设置默认日期范围
        if end is None:
            end = datetime.now().strftime('%Y-%m-%d')
        if start is None:
            start = (datetime.now() - timedelta(days=365*2)).strftime('%Y-%m-%d')  # 默认2年
        
        # 缓存key
        cache_key = f"{symbol}_{start}_{end}"
        if cache_key in self._cache and not force_download:
            return self._cache[cache_key].copy()
        
        df = None
        need_download = force_download
        
        # 尝试从本地加载
        if not force_download:
            df = self.load_csv(symbol)
            
            if df is not None:
                # 检查数据是否覆盖请求的时间范围
                data_start = df.index.min().strftime('%Y-%m-%d')
                data_end = df.index.max().strftime('%Y-%m-%d')
                
                if data_start <= start and data_end >= end:
                    print(f"使用本地缓存数据: {symbol}")
                else:
                    print(f"本地数据时间范围不足，需要重新下载")
                    need_download = True
            else:
                need_download = True
        
        # 需要下载
        if need_download:
            df = self.download_from_yfinance(symbol, start, end)
            self.save_data(df, symbol)
        
        # 按日期筛选
        df = df[(df.index >= start) & (df.index <= end)]
        
        if df.empty:
            raise ValueError(f"在指定时间范围内没有 {symbol} 的数据")
        
        # 缓存数据
        self._cache[cache_key] = df.copy()
        
        return df
    
    def list_available_symbols(self) -> List[str]:
        """
        列出可用的股票代码
        
        Returns:
            本地已有数据的股票代码列表 + 推荐的热门股票
        """
        local_symbols = set()
        
        # 扫描本地文件
        if os.path.exists(self.data_dir):
            for filename in os.listdir(self.data_dir):
                if filename.endswith('.csv'):
                    symbol = filename.replace('.csv', '').upper()
                    local_symbols.add(symbol)
        
        # 合并推荐股票
        all_symbols = local_symbols.union(set(self.DEFAULT_SYMBOLS))
        
        return sorted(list(all_symbols))
    
    def list_local_data(self) -> List[Dict[str, Any]]:
        """
        列出本地已下载的数据详情
        
        Returns:
            包含股票代码和数据范围的列表
        """
        result = []
        
        if not os.path.exists(self.data_dir):
            return result
        
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.csv'):
                symbol = filename.replace('.csv', '').upper()
                filepath = os.path.join(self.data_dir, filename)
                
                try:
                    df = self.load_csv(symbol)
                    if df is not None and len(df) > 0:
                        result.append({
                            'symbol': symbol,
                            'start_date': df.index.min().strftime('%Y-%m-%d'),
                            'end_date': df.index.max().strftime('%Y-%m-%d'),
                            'records': len(df),
                            'file_size': os.path.getsize(filepath)
                        })
                except Exception:
                    pass
        
        return sorted(result, key=lambda x: x['symbol'])
    
    def add_symbol(self, symbol: str, start: Optional[str] = None, 
                   end: Optional[str] = None) -> Dict[str, Any]:
        """
        添加新股票代码（下载数据）
        
        Args:
            symbol: 股票代码
            start: 开始日期
            end: 结束日期
        
        Returns:
            下载结果信息
        """
        symbol = symbol.upper()
        
        try:
            df = self.get_data(symbol, start, end, force_download=True)
            return {
                'success': True,
                'symbol': symbol,
                'records': len(df),
                'start_date': df.index.min().strftime('%Y-%m-%d'),
                'end_date': df.index.max().strftime('%Y-%m-%d')
            }
        except Exception as e:
            return {
                'success': False,
                'symbol': symbol,
                'error': str(e)
            }
    
    def delete_symbol(self, symbol: str) -> bool:
        """
        删除股票数据
        
        Args:
            symbol: 股票代码
        
        Returns:
            是否删除成功
        """
        symbol = symbol.upper()
        filepath = os.path.join(self.data_dir, f"{symbol}.csv")
        
        if os.path.exists(filepath):
            os.remove(filepath)
            # 清除缓存
            keys_to_remove = [k for k in self._cache if k.startswith(symbol)]
            for k in keys_to_remove:
                del self._cache[k]
            return True
        return False
    
    def clear_cache(self) -> None:
        """清除内存缓存"""
        self._cache.clear()


# 便捷函数
def load_stock_data(symbol: str, start: str = None, end: str = None) -> pd.DataFrame:
    """
    快速加载股票数据
    
    Args:
        symbol: 股票代码
        start: 开始日期
        end: 结束日期
    
    Returns:
        DataFrame
    """
    manager = DataManager()
    return manager.get_data(symbol, start, end)
