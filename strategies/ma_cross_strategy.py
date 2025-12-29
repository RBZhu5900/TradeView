"""
金叉死叉策略 (MA Cross Strategy)

基于双均线交叉的经典趋势跟踪策略。

策略名称: MA Cross Strategy (金叉死叉)
策略说明: 使用快慢两条移动平均线的交叉信号进行交易
作者: PythonTradeView
创建日期: 2024-01-01
"""

from typing import Dict, Any, Optional, List
from .base_strategy import BaseStrategy


class MACrossStrategy(BaseStrategy):
    """
    金叉死叉策略
    
    使用两条不同周期的移动平均线，当快线上穿慢线时买入（金叉），
    当快线下穿慢线时卖出（死叉）。
    
    参数:
        fast_period (int): 快速均线周期，默认5
        slow_period (int): 慢速均线周期，默认20
        ma_type (str): 均线类型，'SMA' 或 'EMA'，默认 'SMA'
    
    信号逻辑:
        买入（金叉）: 快线从下方穿越慢线
        卖出（死叉）: 快线从上方穿越慢线
    """
    
    # 策略名称
    name = "MA Cross Strategy"
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """初始化策略"""
        super().__init__(params)
        
        # 策略参数
        self.fast_period = self.params.get('fast_period', 5)
        self.slow_period = self.params.get('slow_period', 20)
        self.ma_type = self.params.get('ma_type', 'SMA')
        
        # 数据缓存
        self.prices: List[float] = []
        self.fast_ma: Optional[float] = None
        self.slow_ma: Optional[float] = None
        self.prev_fast_ma: Optional[float] = None
        self.prev_slow_ma: Optional[float] = None
        
        # 用于EMA计算的平滑因子
        self.fast_multiplier = 2 / (self.fast_period + 1)
        self.slow_multiplier = 2 / (self.slow_period + 1)
        
        # 指标历史记录（用于可视化）
        self.fast_ma_history: List[Optional[float]] = []
        self.slow_ma_history: List[Optional[float]] = []
    
    def _calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """计算简单移动平均线"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    def _calculate_ema(self, current_price: float, prev_ema: Optional[float], 
                       multiplier: float, period: int) -> Optional[float]:
        """计算指数移动平均线"""
        if prev_ema is None:
            # 第一次计算，使用SMA作为初始值
            if len(self.prices) >= period:
                return sum(self.prices[-period:]) / period
            return None
        return (current_price - prev_ema) * multiplier + prev_ema
    
    def on_bar(self, bar: Dict[str, Any]) -> None:
        """
        处理每个K线数据
        
        Args:
            bar: K线数据，包含 open, high, low, close, volume, datetime
        """
        close = bar['close']
        self.prices.append(close)
        
        # 保存前一个均线值
        self.prev_fast_ma = self.fast_ma
        self.prev_slow_ma = self.slow_ma
        
        # 根据类型计算均线
        if self.ma_type == 'EMA':
            self.fast_ma = self._calculate_ema(
                close, self.fast_ma, self.fast_multiplier, self.fast_period
            )
            self.slow_ma = self._calculate_ema(
                close, self.slow_ma, self.slow_multiplier, self.slow_period
            )
        else:  # SMA
            self.fast_ma = self._calculate_sma(self.prices, self.fast_period)
            self.slow_ma = self._calculate_sma(self.prices, self.slow_period)
        
        # 记录历史
        self.fast_ma_history.append(self.fast_ma)
        self.slow_ma_history.append(self.slow_ma)
    
    def should_buy(self) -> bool:
        """
        买入信号：金叉（快线上穿慢线）
        
        Returns:
            True: 应该买入
            False: 不应该买入
        """
        if self.position > 0:
            return False  # 已有持仓
        
        if None in (self.fast_ma, self.slow_ma, self.prev_fast_ma, self.prev_slow_ma):
            return False  # 数据不足
        
        # 金叉：快线从下方穿越慢线
        was_below = self.prev_fast_ma <= self.prev_slow_ma
        is_above = self.fast_ma > self.slow_ma
        
        return was_below and is_above
    
    def should_sell(self) -> bool:
        """
        卖出信号：死叉（快线下穿慢线）
        
        Returns:
            True: 应该卖出
            False: 不应该卖出
        """
        if self.position <= 0:
            return False  # 无持仓
        
        if None in (self.fast_ma, self.slow_ma, self.prev_fast_ma, self.prev_slow_ma):
            return False  # 数据不足
        
        # 死叉：快线从上方穿越慢线
        was_above = self.prev_fast_ma >= self.prev_slow_ma
        is_below = self.fast_ma < self.slow_ma
        
        return was_above and is_below
    
    def get_indicator_values(self) -> Dict[str, Any]:
        """
        获取当前指标值（用于监控和可视化）
        
        Returns:
            包含指标值的字典
        """
        return {
            'fast_ma': self.fast_ma,
            'slow_ma': self.slow_ma,
            'ma_diff': (self.fast_ma - self.slow_ma) if self.fast_ma and self.slow_ma else None,
            'trend': 'bullish' if self.fast_ma and self.slow_ma and self.fast_ma > self.slow_ma else 'bearish'
        }
    
    def reset(self) -> None:
        """重置策略状态"""
        super().reset()
        self.prices = []
        self.fast_ma = None
        self.slow_ma = None
        self.prev_fast_ma = None
        self.prev_slow_ma = None
        self.fast_ma_history = []
        self.slow_ma_history = []


# 策略元数据（用于策略发现和管理）
STRATEGY_METADATA = {
    'name': 'MA Cross Strategy',
    'version': '1.0.0',
    'author': 'PythonTradeView',
    'description': '金叉死叉策略 - 基于双均线交叉的趋势跟踪策略',
    'parameters': {
        'fast_period': {
            'type': 'int',
            'default': 5,
            'min': 2,
            'max': 50,
            'description': '快速均线周期'
        },
        'slow_period': {
            'type': 'int',
            'default': 20,
            'min': 5,
            'max': 200,
            'description': '慢速均线周期'
        },
        'ma_type': {
            'type': 'str',
            'default': 'SMA',
            'options': ['SMA', 'EMA'],
            'description': '均线类型 (SMA=简单移动平均, EMA=指数移动平均)'
        }
    },
    'tags': ['trend', 'moving_average', 'classic', 'beginner']
}

