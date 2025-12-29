#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
交易监控引擎 - 纯监控模式（不执行交易）
"""
import os
import sys
import pandas as pd
import numpy as np
import json
import logging
import time
import schedule
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/trader_engine.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 添加common_strategies路径
current_dir = os.path.dirname(os.path.abspath(__file__))
common_strategies_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'common_strategies', 'src')
sys.path.insert(0, common_strategies_path)

from strategies.detailed_strategy import DetailedStrategy

# 导入新模块
try:
    from src.longport_client import LongPortClient
    from src.telegram_notifier import TelegramNotifier
    HAS_LONGPORT = True
except ImportError:
    logger.warning("长桥SDK未安装，将使用yfinance作为后备")
    import yfinance as yf
    HAS_LONGPORT = False

# 从环境变量获取监控列表
WATCHLIST = os.getenv('WATCHLIST', 'AAPL,00700.HK').split(',')
WATCHLIST = [symbol.strip() for symbol in WATCHLIST]

# 数据缓存
STOCK_DATA = {}
LAST_SIGNALS = {}
MAX_HISTORY = 300

# 全局客户端
longport_client = None
telegram_notifier = None


def initialize_clients():
    """初始化客户端"""
    global longport_client, telegram_notifier
    
    # 初始化Telegram通知器
    telegram_notifier = TelegramNotifier()
    
    # 初始化长桥客户端
    if HAS_LONGPORT:
        try:
            longport_client = LongPortClient()
            logger.info("长桥API客户端初始化成功")
        except Exception as e:
            logger.error(f"长桥API初始化失败: {str(e)}")
            longport_client = None
    
    # 发送启动通知
    if telegram_notifier and telegram_notifier.enabled:
        telegram_notifier.send_startup()


def fetch_stock_data(symbol, days=300):
    """
    获取股票历史数据
    
    Args:
        symbol: 股票代码
        days: 天数
    
    Returns:
        pd.DataFrame: 历史数据
    """
    try:
        if longport_client:
            # 使用长桥API
            df = longport_client.get_candlesticks(symbol, period='day', count=days)
            if df is not None and len(df) > 0:
                logger.info(f"使用长桥API获取 {symbol} 数据成功: {len(df)} 条")
                return df
        
        # 后备：使用yfinance
        logger.info(f"使用yfinance获取 {symbol} 数据")
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{days}d")
        
        if df.empty:
            logger.warning(f"无法获取 {symbol} 的数据")
            return None
        
        # 标准化列名
        df.columns = [col.lower() for col in df.columns]
        if 'close' in df.columns:
            df = df[['open', 'high', 'low', 'close', 'volume']]
        
        logger.info(f"获取 {symbol} 数据成功: {len(df)} 条")
        return df
        
    except Exception as e:
        logger.error(f"获取 {symbol} 数据失败: {str(e)}")
        return None


def calculate_rsi(prices, period=14):
    """计算RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def check_buy_signals(symbol, data_df):
    """
    根据DetailedStrategy的买入逻辑检查买入信号
    
    Args:
        symbol: 股票代码
        data_df: pandas DataFrame包含OHLCV数据
    
    Returns:
        买入信号描述，如果没有信号则返回None
    """
    if len(data_df) < 200:  # 需要至少200个数据点来计算EMA200
        return None
    
    # 计算技术指标
    close = data_df['close'].values
    volume = data_df['volume'].values
    
    # EMA
    ema_20 = pd.Series(close).ewm(span=20, adjust=False).mean().values
    ema_50 = pd.Series(close).ewm(span=50, adjust=False).mean().values
    ema_200 = pd.Series(close).ewm(span=200, adjust=False).mean().values
    
    # MACD
    exp1 = pd.Series(close).ewm(span=12, adjust=False).mean()
    exp2 = pd.Series(close).ewm(span=26, adjust=False).mean()
    macd_line = (exp1 - exp2).values
    macd_signal = pd.Series(macd_line).ewm(span=9, adjust=False).mean().values
    
    # RSI
    rsi = calculate_rsi(pd.Series(close), 14).values
    
    # Bollinger Bands
    sma_20 = pd.Series(close).rolling(window=20).mean()
    std_20 = pd.Series(close).rolling(window=20).std()
    boll_upper = (sma_20 + 2 * std_20).values
    boll_mid = sma_20.values
    boll_lower = (sma_20 - 2 * std_20).values
    
    # 成交量均线
    vol_ma_20 = pd.Series(volume).rolling(window=20).mean().values
    
    # TIER 1: 检查必须条件
    current_close = close[-1]
    is_ema_golden = (ema_20[-1] > ema_50[-1]) and (ema_50[-1] > ema_200[-1])
    is_ema20_rising = (ema_20[-1] > ema_20[-2]) and (ema_20[-2] > ema_20[-3])
    is_macd_positive = macd_line[-1] > 0 and macd_signal[-1] > 0
    
    if not (is_ema_golden and is_ema20_rising and is_macd_positive):
        return None
    
    # TIER 2: 检查进场时机
    current_rsi = rsi[-1]
    current_volume = volume[-1]
    
    # 方案A: BOLL中轨回调
    if (boll_mid[-1] * 0.995 <= current_close <= boll_mid[-1] * 1.005 and
        40 <= current_rsi <= 60 and
        current_volume >= vol_ma_20[-1] and
        current_close > boll_mid[-1]):
        return {
            'type': '方案A: BOLL中轨回调',
            'description': '温和上升路径',
            'ema20': ema_20[-1],
            'ema50': ema_50[-1],
            'rsi': current_rsi,
            'volume_ratio': current_volume / vol_ma_20[-1]
        }
    
    # 方案B: MACD金叉
    if (macd_line[-1] > macd_signal[-1] and macd_line[-2] <= macd_signal[-2] and
        50 <= current_rsi <= 70 and
        current_volume > vol_ma_20[-1] * 1.3 and
        current_close > boll_mid[-1]):
        return {
            'type': '方案B: MACD金叉',
            'description': '趋势加速突破',
            'ema20': ema_20[-1],
            'ema50': ema_50[-1],
            'rsi': current_rsi,
            'volume_ratio': current_volume / vol_ma_20[-1]
        }
    
    # 方案C: BOLL突破
    if (current_close > boll_upper[-1] and
        50 <= current_rsi <= 70 and
        current_volume > vol_ma_20[-1] * 1.5 and
        macd_line[-1] > 0):
        return {
            'type': '方案C: BOLL突破',
            'description': '最强势突破',
            'ema20': ema_20[-1],
            'ema50': ema_50[-1],
            'rsi': current_rsi,
            'volume_ratio': current_volume / vol_ma_20[-1]
        }
    
    return None


def monitor_stocks():
    """
    监控股票并检查交易信号
    """
    signals_found = []
    
    for symbol in WATCHLIST:
        try:
            logger.info(f"开始监控 {symbol}")
            
            # 获取历史数据（如果缓存中没有或数据过旧）
            if symbol not in STOCK_DATA or len(STOCK_DATA[symbol]) < 200:
                df = fetch_stock_data(symbol, days=300)
                if df is None or len(df) < 200:
                    logger.warning(f"{symbol} 数据不足，跳过")
                    continue
                STOCK_DATA[symbol] = df
            else:
                # 更新最新数据
                new_data = fetch_stock_data(symbol, days=5)
                if new_data is not None:
                    # 合并数据，去重
                    df = pd.concat([STOCK_DATA[symbol], new_data])
                    df = df[~df.index.duplicated(keep='last')]
                    df = df.sort_index()
                    # 保留最近MAX_HISTORY条
                    df = df.tail(MAX_HISTORY)
                    STOCK_DATA[symbol] = df
                else:
                    df = STOCK_DATA[symbol]
            
            # 检查买入信号
            buy_signal = check_buy_signals(symbol, df)
            
            if buy_signal:
                current_price = df['close'].iloc[-1]
                
                # 检查是否是新信号（防止重复通知）
                last_signal_type = LAST_SIGNALS.get(symbol, {}).get('type')
                current_signal_type = buy_signal['type']
                
                if last_signal_type != current_signal_type:
                    logger.info(f"🟢 发现买入信号: {symbol} @ {current_price:.2f} - {buy_signal['type']}")
                    
                    # 构建策略信息
                    strategy_info = {
                        '信号类型': buy_signal['type'],
                        '信号描述': buy_signal['description'],
                        'EMA20': f"{buy_signal['ema20']:.2f}",
                        'EMA50': f"{buy_signal['ema50']:.2f}",
                        'RSI': f"{buy_signal['rsi']:.2f}",
                        '成交量比': f"{buy_signal['volume_ratio']:.2f}x"
                    }
                    
                    # 发送Telegram通知
                    if telegram_notifier and telegram_notifier.enabled:
                        telegram_notifier.send_signal(
                            symbol=symbol,
                            signal_type='BUY',
                            price=current_price,
                            strategy_info=strategy_info
                        )
                    
                    LAST_SIGNALS[symbol] = buy_signal
                    signals_found.append({
                        'symbol': symbol,
                        'type': 'BUY',
                        'price': current_price,
                        'signal': buy_signal['type']
                    })
                else:
                    logger.debug(f"{symbol} 信号持续: {current_signal_type}")
            else:
                # 无信号，重置
                if symbol in LAST_SIGNALS and LAST_SIGNALS[symbol]:
                    logger.info(f"{symbol} 信号消失")
                    LAST_SIGNALS[symbol] = None
                
        except Exception as e:
            logger.error(f"监控 {symbol} 时出错: {str(e)}", exc_info=True)
            if telegram_notifier and telegram_notifier.enabled:
                telegram_notifier.send_error(f"监控 {symbol} 失败: {str(e)}")
    
    return signals_found


def scheduled_job():
    """定时任务"""
    logger.info("=" * 60)
    logger.info(f"开始定时监控任务 - {datetime.now()}")
    logger.info("=" * 60)
    
    signals = monitor_stocks()
    
    # 发送每日报告
    if telegram_notifier and telegram_notifier.enabled:
        report_data = {
            'total_stocks': len(WATCHLIST),
            'signals_found': len(signals),
            'signals': signals
        }
        telegram_notifier.send_daily_report(report_data)
    
    logger.info("=" * 60)
    logger.info(f"监控任务完成 - 发现 {len(signals)} 个信号")
    logger.info("=" * 60)


if __name__ == '__main__':
    # 加载环境变量
    load_dotenv()
    
    # 确保DRY_RUN模式
    dry_run = os.getenv('DRY_RUN_MODE', 'true').lower()
    if dry_run != 'true':
        logger.warning("强制启用DRY_RUN_MODE，系统只监控不交易")
        os.environ['DRY_RUN_MODE'] = 'true'
    
    logger.info("=" * 60)
    logger.info("交易监控系统启动 (纯监控模式，不执行交易)")
    logger.info("=" * 60)
    logger.info(f"监控列表: {WATCHLIST}")
    logger.info(f"查询时间: {os.getenv('CHECK_TIME', '06:00')}")
    logger.info(f"DRY_RUN模式: {os.getenv('DRY_RUN_MODE')}")
    
    # 初始化客户端
    try:
        initialize_clients()
    except Exception as e:
        logger.error(f"初始化失败: {str(e)}", exc_info=True)
        sys.exit(1)
    
    # 获取查询时间
    check_time = os.getenv('CHECK_TIME', '06:00')
    
    # 设置定时任务
    schedule.every().day.at(check_time).do(scheduled_job)
    
    # 立即执行一次（测试）
    logger.info("执行首次监控（测试）...")
    try:
        scheduled_job()
    except Exception as e:
        logger.error(f"首次监控失败: {str(e)}", exc_info=True)
    
    # 主循环
    logger.info(f"进入定时循环，每天 {check_time} 执行监控...")
    logger.info("按 Ctrl+C 停止")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次定时任务
    except KeyboardInterrupt:
        logger.info("\n收到停止信号，系统关闭...")
        if longport_client:
            longport_client.close()
    except Exception as e:
        logger.error(f"系统错误: {str(e)}", exc_info=True)
        if telegram_notifier and telegram_notifier.enabled:
            telegram_notifier.send_error(f"系统崩溃: {str(e)}")
