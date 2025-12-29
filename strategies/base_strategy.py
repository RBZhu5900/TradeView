"""
策略基类

所有交易策略都应该继承此基类，并实现必要的方法。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseStrategy(ABC):
    """
    交易策略基类
    
    所有自定义策略都应该继承此类，并实现抽象方法。
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化策略
        
        Args:
            params: 策略参数字典
        """
        self.params = params or {}
        self.position = 0  # 当前持仓
        self.cash = 100000.0  # 初始资金
        self.entry_price = None  # 入场价格
        
    @abstractmethod
    def on_bar(self, bar: Dict[str, Any]) -> None:
        """
        处理每个K线数据
        
        Args:
            bar: K线数据字典，包含 open, high, low, close, volume 等
        """
        pass
    
    @abstractmethod
    def should_buy(self) -> bool:
        """
        判断是否应该买入
        
        Returns:
            True: 应该买入
            False: 不应该买入
        """
        pass
    
    @abstractmethod
    def should_sell(self) -> bool:
        """
        判断是否应该卖出
        
        Returns:
            True: 应该卖出
            False: 不应该卖出
        """
        pass
    
    def get_position_size(self) -> float:
        """
        计算买入数量
        
        Returns:
            应该买入的股票数量
        """
        # 默认使用95%的资金
        return (self.cash * 0.95) / self.entry_price if self.entry_price else 0
    
    def buy(self, price: float, size: Optional[float] = None) -> bool:
        """
        执行买入操作
        
        Args:
            price: 买入价格
            size: 买入数量（如果为None，使用get_position_size计算）
        
        Returns:
            True: 买入成功
            False: 买入失败
        """
        if self.position > 0:
            return False  # 已有持仓
        
        if size is None:
            size = self.get_position_size()
        
        cost = price * size
        if cost > self.cash:
            return False  # 资金不足
        
        self.position = size
        self.entry_price = price
        self.cash -= cost
        return True
    
    def sell(self, price: float, size: Optional[float] = None) -> bool:
        """
        执行卖出操作
        
        Args:
            price: 卖出价格
            size: 卖出数量（如果为None，卖出全部）
        
        Returns:
            True: 卖出成功
            False: 卖出失败
        """
        if self.position <= 0:
            return False  # 无持仓
        
        if size is None:
            size = self.position
        
        if size > self.position:
            size = self.position
        
        proceeds = price * size
        self.cash += proceeds
        self.position -= size
        
        if self.position == 0:
            self.entry_price = None
        
        return True
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        获取策略性能指标
        
        Returns:
            包含各种性能指标的字典
        """
        total_value = self.cash + (self.position * self.entry_price if self.position > 0 and self.entry_price else 0)
        return {
            'total_value': total_value,
            'cash': self.cash,
            'position': self.position,
            'return_pct': ((total_value - 100000) / 100000) * 100
        }
    
    def reset(self) -> None:
        """
        重置策略状态（用于回测）
        """
        self.position = 0
        self.cash = 100000.0
        self.entry_price = None

