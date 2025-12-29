"""
回测引擎

负责执行策略回测，计算性能指标。
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Type
import pandas as pd
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.base_strategy import BaseStrategy
from backtester.data_manager import DataManager


class BacktestEngine:
    """
    回测引擎类
    
    负责加载数据、运行策略、计算指标。
    """
    
    def __init__(self, strategy: BaseStrategy, data: pd.DataFrame, 
                 initial_capital: float = 100000.0):
        """
        初始化回测引擎
        
        Args:
            strategy: 策略实例
            data: OHLCV数据（DataFrame）
            initial_capital: 初始资金
        """
        self.strategy = strategy
        self.data = data.copy()
        self.initial_capital = initial_capital
        self.trades: List[Dict[str, Any]] = []
        self.equity_curve: List[Dict[str, Any]] = []
        self.signals: List[Dict[str, Any]] = []
    
    def run(self, verbose: bool = True) -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            verbose: 是否输出详细信息
        
        Returns:
            回测结果字典
        """
        if verbose:
            print(f"开始回测...")
            print(f"数据范围: {self.data.index[0]} 到 {self.data.index[-1]}")
            print(f"数据点数: {len(self.data)}")
        
        # 重置策略
        self.strategy.reset()
        self.strategy.cash = self.initial_capital
        self.trades = []
        self.equity_curve = []
        self.signals = []
        
        # 遍历每个K线
        for idx, row in self.data.iterrows():
            bar = {
                'datetime': idx,
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume']) if 'volume' in row else 0
            }
            
            # 策略处理K线
            self.strategy.on_bar(bar)
            
            # 获取当前价格用于计算持仓价值
            current_price = bar['close']
            
            # 检查买入信号
            if self.strategy.should_buy():
                # 设置入场价格用于计算仓位
                self.strategy.entry_price = current_price
                size = self.strategy.get_position_size()
                success = self.strategy.buy(current_price, size)
                
                if success:
                    trade = {
                        'datetime': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                        'type': 'BUY',
                        'price': current_price,
                        'size': self.strategy.position
                    }
                    self.trades.append(trade)
                    self.signals.append({
                        'datetime': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                        'signal': 'BUY',
                        'price': current_price
                    })
                    if verbose:
                        date_str = idx.date() if hasattr(idx, 'date') else idx
                        print(f"{date_str}: 买入 @ {current_price:.2f}, 数量: {self.strategy.position:.2f}")
            
            # 检查卖出信号
            elif self.strategy.should_sell():
                size = self.strategy.position
                success = self.strategy.sell(current_price)
                
                if success:
                    trade = {
                        'datetime': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                        'type': 'SELL',
                        'price': current_price,
                        'size': size
                    }
                    self.trades.append(trade)
                    self.signals.append({
                        'datetime': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                        'signal': 'SELL',
                        'price': current_price
                    })
                    if verbose:
                        date_str = idx.date() if hasattr(idx, 'date') else idx
                        print(f"{date_str}: 卖出 @ {current_price:.2f}, 数量: {size:.2f}")
            
            # 计算当前权益
            position_value = self.strategy.position * current_price
            total_value = self.strategy.cash + position_value
            
            self.equity_curve.append({
                'datetime': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                'value': total_value,
                'cash': self.strategy.cash,
                'position_value': position_value,
                'price': current_price
            })
        
        # 计算最终指标
        results = self._calculate_metrics()
        return results
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """
        计算性能指标
        
        Returns:
            包含各种性能指标的字典
        """
        if not self.equity_curve:
            return {
                'final_value': self.initial_capital,
                'return_pct': 0,
                'total_trades': 0,
                'error': 'No data'
            }
        
        # 权益曲线数据
        equity_values = [e['value'] for e in self.equity_curve]
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df['datetime'] = pd.to_datetime(equity_df['datetime'])
        equity_df.set_index('datetime', inplace=True)
        
        # 基本指标
        final_value = equity_values[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        # 交易统计
        buy_trades = [t for t in self.trades if t['type'] == 'BUY']
        sell_trades = [t for t in self.trades if t['type'] == 'SELL']
        total_trades = min(len(buy_trades), len(sell_trades))
        
        # 计算每笔交易盈亏
        profits = []
        for i in range(total_trades):
            buy_price = buy_trades[i]['price']
            sell_price = sell_trades[i]['price']
            profit_pct = ((sell_price - buy_price) / buy_price) * 100
            profits.append(profit_pct)
        
        won_trades = len([p for p in profits if p > 0])
        lost_trades = len([p for p in profits if p <= 0])
        
        # 最大回撤
        max_drawdown = self._calculate_max_drawdown(equity_values)
        
        # 夏普比率（假设无风险利率为0）
        sharpe_ratio = self._calculate_sharpe_ratio(equity_df['value'])
        
        # 年化收益率
        days = (self.data.index[-1] - self.data.index[0]).days
        annual_return = (total_return / 100 + 1) ** (365 / max(days, 1)) - 1
        annual_return *= 100
        
        # 最大连续亏损
        max_consecutive_losses = self._calculate_max_consecutive_losses(profits)
        
        results = {
            'initial_capital': self.initial_capital,
            'final_value': round(final_value, 2),
            'return_pct': round(total_return, 2),
            'annual_return_pct': round(annual_return, 2),
            'max_drawdown_pct': round(max_drawdown, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'total_trades': total_trades,
            'won_trades': won_trades,
            'lost_trades': lost_trades,
            'win_rate': round(won_trades / total_trades * 100, 2) if total_trades > 0 else 0,
            'avg_profit_pct': round(np.mean(profits), 2) if profits else 0,
            'max_profit_pct': round(max(profits), 2) if profits else 0,
            'max_loss_pct': round(min(profits), 2) if profits else 0,
            'max_consecutive_losses': max_consecutive_losses,
            'profit_factor': self._calculate_profit_factor(profits),
            'start_date': self.data.index[0].isoformat() if hasattr(self.data.index[0], 'isoformat') else str(self.data.index[0]),
            'end_date': self.data.index[-1].isoformat() if hasattr(self.data.index[-1], 'isoformat') else str(self.data.index[-1]),
            'trading_days': len(self.data),
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'signals': self.signals
        }
        
        return results
    
    def _calculate_max_drawdown(self, equity_values: List[float]) -> float:
        """计算最大回撤"""
        peak = equity_values[0]
        max_dd = 0
        
        for value in equity_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def _calculate_sharpe_ratio(self, equity_series: pd.Series, 
                                 risk_free_rate: float = 0.0) -> float:
        """计算夏普比率（年化）"""
        daily_returns = equity_series.pct_change().dropna()
        
        if len(daily_returns) < 2:
            return 0.0
        
        excess_returns = daily_returns - risk_free_rate / 252
        
        if excess_returns.std() == 0:
            return 0.0
        
        sharpe = np.sqrt(252) * excess_returns.mean() / excess_returns.std()
        return sharpe
    
    def _calculate_max_consecutive_losses(self, profits: List[float]) -> int:
        """计算最大连续亏损次数"""
        max_losses = 0
        current_losses = 0
        
        for p in profits:
            if p <= 0:
                current_losses += 1
                max_losses = max(max_losses, current_losses)
            else:
                current_losses = 0
        
        return max_losses
    
    def _calculate_profit_factor(self, profits: List[float]) -> float:
        """计算盈亏比"""
        gross_profit = sum(p for p in profits if p > 0)
        gross_loss = abs(sum(p for p in profits if p < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0
        
        return round(gross_profit / gross_loss, 2)
    
    def print_summary(self, results: Dict[str, Any]) -> None:
        """
        打印回测摘要
        
        Args:
            results: 回测结果字典
        """
        print(f"\n{'='*60}")
        print(f"回测结果摘要")
        print(f"{'='*60}")
        print(f"初始资金: ${results['initial_capital']:,.2f}")
        print(f"最终资产: ${results['final_value']:,.2f}")
        print(f"总收益率: {results['return_pct']:+.2f}%")
        print(f"年化收益: {results['annual_return_pct']:+.2f}%")
        print(f"最大回撤: {results['max_drawdown_pct']:.2f}%")
        print(f"夏普比率: {results['sharpe_ratio']:.2f}")
        print(f"{'='*60}")
        print(f"交易统计:")
        print(f"  总交易数: {results['total_trades']}")
        print(f"  盈利交易: {results['won_trades']}")
        print(f"  亏损交易: {results['lost_trades']}")
        print(f"  胜率: {results['win_rate']:.2f}%")
        print(f"  平均盈亏: {results['avg_profit_pct']:+.2f}%")
        print(f"  最大盈利: {results['max_profit_pct']:+.2f}%")
        print(f"  最大亏损: {results['max_loss_pct']:+.2f}%")
        print(f"  盈亏比: {results['profit_factor']:.2f}")
        print(f"  最大连亏: {results['max_consecutive_losses']}次")
        print(f"{'='*60}\n")
    
    def save_results(self, results: Dict[str, Any], filepath: str) -> None:
        """
        保存回测结果到JSON
        
        Args:
            results: 回测结果
            filepath: 文件路径
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"结果已保存到: {filepath}")


def load_strategy(strategy_name: str, params: Optional[Dict[str, Any]] = None):
    """
    动态加载策略
    
    Args:
        strategy_name: 策略名称（模块名，不含.py）
        params: 策略参数
    
    Returns:
        策略实例
    """
    import importlib
    
    try:
        module = importlib.import_module(f'strategies.{strategy_name}')
    except ImportError as e:
        raise ImportError(f"无法加载策略 '{strategy_name}': {e}")
    
    # 查找策略类（继承自BaseStrategy的类）
    strategy_class = None
    for name in dir(module):
        obj = getattr(module, name)
        if (isinstance(obj, type) and 
            issubclass(obj, BaseStrategy) and 
            obj is not BaseStrategy):
            strategy_class = obj
            break
    
    if strategy_class is None:
        raise ValueError(f"在 '{strategy_name}' 中找不到有效的策略类")
    
    return strategy_class(params)


def list_strategies() -> List[Dict[str, Any]]:
    """
    列出所有可用的策略
    
    Returns:
        策略信息列表
    """
    import importlib
    import pkgutil
    import strategies
    
    available = []
    
    for importer, modname, ispkg in pkgutil.iter_modules(strategies.__path__):
        if modname.startswith('_') or modname == 'base_strategy':
            continue
        
        try:
            module = importlib.import_module(f'strategies.{modname}')
            metadata = getattr(module, 'STRATEGY_METADATA', None)
            
            if metadata:
                available.append({
                    'module': modname,
                    **metadata
                })
            else:
                # 尝试获取基本信息
                for name in dir(module):
                    obj = getattr(module, name)
                    if (isinstance(obj, type) and 
                        issubclass(obj, BaseStrategy) and 
                        obj is not BaseStrategy):
                        available.append({
                            'module': modname,
                            'name': getattr(obj, 'name', modname),
                            'description': obj.__doc__ or ''
                        })
                        break
        except Exception as e:
            print(f"Warning: 无法加载策略 {modname}: {e}")
    
    return available


def run_backtest(strategy_name: str, symbol: str, 
                 start: str = None, end: str = None,
                 params: Dict[str, Any] = None,
                 initial_capital: float = 100000.0,
                 verbose: bool = True) -> Dict[str, Any]:
    """
    便捷函数：运行完整回测
    
    Args:
        strategy_name: 策略名称
        symbol: 股票代码
        start: 开始日期
        end: 结束日期
        params: 策略参数
        initial_capital: 初始资金
        verbose: 详细输出
    
    Returns:
        回测结果
    """
    # 加载策略
    strategy = load_strategy(strategy_name, params)
    
    # 加载数据
    dm = DataManager()
    data = dm.get_data(symbol, start, end)
    
    # 运行回测
    engine = BacktestEngine(strategy, data, initial_capital)
    results = engine.run(verbose=verbose)
    
    if verbose:
        engine.print_summary(results)
    
    return results


def main():
    """主函数 - 命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='策略回测引擎')
    parser.add_argument('--strategy', type=str, help='策略名称')
    parser.add_argument('--stock', type=str, help='股票代码')
    parser.add_argument('--start', type=str, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--capital', type=float, default=100000, help='初始资金')
    parser.add_argument('--list', action='store_true', help='列出可用策略')
    parser.add_argument('--output', type=str, help='结果输出文件')
    
    args = parser.parse_args()
    
    if args.list:
        print("\n可用策略:")
        print("="*60)
        for s in list_strategies():
            print(f"  • {s['module']}: {s.get('name', 'N/A')}")
            if s.get('description'):
                print(f"    {s['description'][:60]}...")
        print("="*60)
        return
    
    if not args.strategy or not args.stock:
        parser.print_help()
        print("\n示例:")
        print("  python engine.py --strategy ma_cross_strategy --stock AAPL")
        print("  python engine.py --list")
        return
    
    print(f"\n策略: {args.strategy}")
    print(f"股票: {args.stock}")
    if args.start and args.end:
        print(f"时间: {args.start} 到 {args.end}")
    print(f"资金: ${args.capital:,.0f}")
    print()
    
    results = run_backtest(
        strategy_name=args.strategy,
        symbol=args.stock,
        start=args.start,
        end=args.end,
        initial_capital=args.capital
    )
    
    if args.output:
        output_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, args.output)
        
        engine = BacktestEngine(None, pd.DataFrame())
        engine.save_results(results, output_path)


if __name__ == '__main__':
    main()
