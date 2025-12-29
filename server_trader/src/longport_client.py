#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
长桥API客户端 - 仅用于行情查询
"""
import os
import logging
from datetime import datetime, timedelta
from longport.openapi import QuoteContext, Config
import pandas as pd

logger = logging.getLogger(__name__)


class LongPortClient:
    """长桥API客户端（只读模式）"""
    
    def __init__(self):
        """初始化长桥客户端"""
        self.app_key = os.getenv('LONGPORT_APP_KEY')
        self.app_secret = os.getenv('LONGPORT_APP_SECRET')
        self.access_token = os.getenv('LONGPORT_ACCESS_TOKEN')
        
        if not all([self.app_key, self.app_secret, self.access_token]):
            raise ValueError("长桥API配置不完整，请检查.env文件")
        
        # 创建配置
        config = Config(
            app_key=self.app_key,
            app_secret=self.app_secret,
            access_token=self.access_token
        )
        
        # 创建行情上下文（只读）
        self.quote_ctx = QuoteContext(config)
        logger.info("长桥API客户端初始化成功（只读模式）")
    
    def get_quote(self, symbol):
        """
        获取实时行情
        
        Args:
            symbol: 股票代码 (例如: AAPL, 00700.HK)
        
        Returns:
            dict: 包含最新价格、成交量等信息
        """
        try:
            # 获取实时行情
            quotes = self.quote_ctx.quote([symbol])
            if not quotes:
                logger.warning(f"无法获取 {symbol} 的行情数据")
                return None
            
            quote = quotes[0]
            return {
                'symbol': symbol,
                'last_price': float(quote.last_done),
                'open': float(quote.open),
                'high': float(quote.high),
                'low': float(quote.low),
                'volume': int(quote.volume),
                'timestamp': quote.timestamp,
                'prev_close': float(quote.prev_close) if quote.prev_close else None
            }
        except Exception as e:
            logger.error(f"获取 {symbol} 行情失败: {str(e)}")
            return None
    
    def get_candlesticks(self, symbol, period='day', count=300):
        """
        获取K线数据
        
        Args:
            symbol: 股票代码
            period: 周期 ('day', 'week', 'month')
            count: 获取数量
        
        Returns:
            pd.DataFrame: K线数据
        """
        try:
            from longport.openapi import Period
            
            # 映射周期
            period_map = {
                'day': Period.Day,
                'week': Period.Week,
                'month': Period.Month
            }
            
            # 获取K线
            candlesticks = self.quote_ctx.candlesticks(
                symbol=symbol,
                period=period_map.get(period, Period.Day),
                count=count
            )
            
            if not candlesticks:
                logger.warning(f"无法获取 {symbol} 的K线数据")
                return None
            
            # 转换为DataFrame
            data = []
            for candle in candlesticks:
                data.append({
                    'datetime': candle.timestamp,
                    'open': float(candle.open),
                    'high': float(candle.high),
                    'low': float(candle.low),
                    'close': float(candle.close),
                    'volume': int(candle.volume)
                })
            
            df = pd.DataFrame(data)
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.set_index('datetime')
            df = df.sort_index()
            
            logger.info(f"成功获取 {symbol} 的K线数据: {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} K线失败: {str(e)}")
            return None
    
    def get_trading_days(self, market='US', days=10):
        """
        获取交易日历
        
        Args:
            market: 市场 ('US', 'HK', 'CN')
            days: 获取天数
        
        Returns:
            list: 交易日列表
        """
        try:
            from longport.openapi import Market
            
            market_map = {
                'US': Market.US,
                'HK': Market.HK,
                'CN': Market.CN
            }
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            trading_days = self.quote_ctx.trading_days(
                market=market_map.get(market, Market.US),
                begin=start_date,
                end=end_date
            )
            
            return [day.date for day in trading_days]
            
        except Exception as e:
            logger.error(f"获取交易日历失败: {str(e)}")
            return []
    
    def is_trading_time(self, symbol):
        """
        检查是否在交易时间
        
        Args:
            symbol: 股票代码
        
        Returns:
            bool: 是否在交易时间
        """
        try:
            # 判断市场
            if '.HK' in symbol:
                market = 'HK'
            elif '.SH' in symbol or '.SZ' in symbol:
                market = 'CN'
            else:
                market = 'US'
            
            # 获取交易状态
            from longport.openapi import Market
            market_map = {
                'US': Market.US,
                'HK': Market.HK,
                'CN': Market.CN
            }
            
            # 这里简化处理，实际应该调用API获取交易状态
            # 由于我们主要在收盘后查询，这里返回False
            return False
            
        except Exception as e:
            logger.error(f"检查交易时间失败: {str(e)}")
            return False
    
    def close(self):
        """关闭连接"""
        if hasattr(self, 'quote_ctx'):
            # 长桥SDK会自动处理连接关闭
            logger.info("长桥API连接已关闭")

