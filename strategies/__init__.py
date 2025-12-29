"""
策略库模块

本模块包含所有交易策略的实现。每个策略是一个独立的Python文件。

策略开发规范：
1. 继承 BaseStrategy 基类
2. 实现必要的接口方法
3. 提供完整的参数说明
4. 编写单元测试

可用策略:
- MACrossStrategy: 金叉死叉策略（双均线交叉）
- TemplateStrategy: 策略模板
"""

from .base_strategy import BaseStrategy
from .ma_cross_strategy import MACrossStrategy
from .strategy_template import TemplateStrategy

__all__ = [
    'BaseStrategy',
    'MACrossStrategy', 
    'TemplateStrategy'
]
__version__ = '1.0.0'
