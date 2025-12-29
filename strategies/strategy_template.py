"""
策略模板

这是一个策略开发模板，展示如何创建自定义策略。
复制此文件并修改以创建您自己的策略。

策略名称: Template Strategy
策略说明: 这是一个示例策略，展示基本的策略结构
作者: Your Name
创建日期: 2024-01-01
"""

from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy


class TemplateStrategy(BaseStrategy):
    """
    模板策略类
    
    这是一个简单的移动平均线交叉策略示例。
    
    参数:
        fast_period (int): 快速均线周期，默认10
        slow_period (int): 慢速均线周期，默认20
    
    信号逻辑:
        买入: 快线上穿慢线
        卖出: 快线下穿慢线
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """初始化策略"""
        super().__init__(params)
        
        # 策略参数
        self.fast_period = self.params.get('fast_period', 10)
        self.slow_period = self.params.get('slow_period', 20)
        
        # 数据缓存
        self.prices = []
        self.fast_ma = None
        self.slow_ma = None
        self.prev_fast_ma = None
        self.prev_slow_ma = None
    
    def on_bar(self, bar: Dict[str, Any]) -> None:
        """
        处理每个K线数据
        
        Args:
            bar: K线数据，包含 open, high, low, close, volume
        """
        close = bar['close']
        self.prices.append(close)
        
        # 计算移动平均线
        if len(self.prices) >= self.fast_period:
            self.prev_fast_ma = self.fast_ma
            self.fast_ma = sum(self.prices[-self.fast_period:]) / self.fast_period
        
        if len(self.prices) >= self.slow_period:
            self.prev_slow_ma = self.slow_ma
            self.slow_ma = sum(self.prices[-self.slow_period:]) / self.slow_period
    
    def should_buy(self) -> bool:
        """
        买入信号：快线上穿慢线
        
        Returns:
            True: 应该买入
            False: 不应该买入
        """
        if self.position > 0:
            return False  # 已有持仓
        
        if self.fast_ma is None or self.slow_ma is None:
            return False  # 数据不足
        
        if self.prev_fast_ma is None or self.prev_slow_ma is None:
            return False  # 需要前一个值来判断交叉
        
        # 金叉：快线从下方穿越慢线
        cross_up = (self.prev_fast_ma <= self.prev_slow_ma and 
                   self.fast_ma > self.slow_ma)
        
        return cross_up
    
    def should_sell(self) -> bool:
        """
        卖出信号：快线下穿慢线
        
        Returns:
            True: 应该卖出
            False: 不应该卖出
        """
        if self.position <= 0:
            return False  # 无持仓
        
        if self.fast_ma is None or self.slow_ma is None:
            return False  # 数据不足
        
        if self.prev_fast_ma is None or self.prev_slow_ma is None:
            return False  # 需要前一个值来判断交叉
        
        # 死叉：快线从上方穿越慢线
        cross_down = (self.prev_fast_ma >= self.prev_slow_ma and 
                     self.fast_ma < self.slow_ma)
        
        return cross_down
    
    def reset(self) -> None:
        """重置策略状态"""
        super().reset()
        self.prices = []
        self.fast_ma = None
        self.slow_ma = None
        self.prev_fast_ma = None
        self.prev_slow_ma = None


# 策略元数据（用于策略发现和管理）
STRATEGY_METADATA = {
    'name': 'Template Strategy',
    'version': '1.0.0',
    'author': 'Your Name',
    'description': '简单的移动平均线交叉策略',
    'parameters': {
        'fast_period': {
            'type': 'int',
            'default': 10,
            'min': 5,
            'max': 50,
            'description': '快速均线周期'
        },
        'slow_period': {
            'type': 'int',
            'default': 20,
            'min': 10,
            'max': 100,
            'description': '慢速均线周期'
        }
    },
    'tags': ['trend', 'moving_average', 'simple']
}

