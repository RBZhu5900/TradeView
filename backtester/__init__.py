"""
回测系统模块

提供策略回测功能，包括：
- 数据管理
- 回测引擎
- 性能指标计算
- 配置管理
"""

from .data_manager import DataManager, load_stock_data
from .engine import BacktestEngine, load_strategy, list_strategies, run_backtest
from .config_manager import ConfigManager, save_strategy_config, load_strategy_config, list_strategy_configs

__all__ = [
    'DataManager',
    'load_stock_data',
    'BacktestEngine',
    'load_strategy',
    'list_strategies',
    'run_backtest',
    'ConfigManager',
    'save_strategy_config',
    'load_strategy_config',
    'list_strategy_configs'
]
__version__ = '1.0.0'
