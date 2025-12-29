#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Telegram通知模块
"""
import os
import logging
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
import asyncio

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram通知器"""
    
    def __init__(self):
        """初始化Telegram Bot"""
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = os.getenv('TELEGRAM_ENABLED', 'true').lower() == 'true'
        
        if not self.enabled:
            logger.info("Telegram通知已禁用")
            return
        
        if not self.token or not self.chat_id:
            logger.warning("Telegram配置不完整，通知功能将不可用")
            self.enabled = False
            return
        
        self.bot = Bot(token=self.token)
        logger.info("Telegram Bot初始化成功")
    
    async def _send_message_async(self, message, parse_mode='Markdown'):
        """异步发送消息"""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.info("Telegram消息发送成功")
            return True
        except TelegramError as e:
            logger.error(f"Telegram消息发送失败: {str(e)}")
            return False
    
    def send_message(self, message, parse_mode='Markdown'):
        """
        发送消息（同步接口）
        
        Args:
            message: 消息内容
            parse_mode: 解析模式 ('Markdown' 或 'HTML')
        
        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            logger.debug("Telegram通知已禁用，跳过发送")
            return False
        
        try:
            # 在新的事件循环中运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._send_message_async(message, parse_mode))
            loop.close()
            return result
        except Exception as e:
            logger.error(f"发送Telegram消息时出错: {str(e)}")
            return False
    
    def send_signal(self, symbol, signal_type, price, strategy_info):
        """
        发送交易信号通知
        
        Args:
            symbol: 股票代码
            signal_type: 信号类型 ('BUY', 'SELL')
            price: 当前价格
            strategy_info: 策略信息字典
        """
        emoji = "🟢" if signal_type == "BUY" else "🔴"
        
        message = f"""
{emoji} *交易信号* {emoji}

📊 *股票*: `{symbol}`
💡 *信号*: *{signal_type}*
💰 *价格*: `${price:.2f}`
⏰ *时间*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📈 *策略详情*:
"""
        
        # 添加策略信息
        if strategy_info:
            for key, value in strategy_info.items():
                if isinstance(value, float):
                    message += f"  • {key}: `{value:.2f}`\n"
                else:
                    message += f"  • {key}: `{value}`\n"
        
        message += "\n⚠️ *注意*: 这只是信号提示，请自行判断后手动操作"
        
        return self.send_message(message)
    
    def send_error(self, error_message):
        """
        发送错误通知
        
        Args:
            error_message: 错误信息
        """
        message = f"""
⚠️ *系统错误*

{error_message}

⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(message)
    
    def send_daily_report(self, report_data):
        """
        发送每日报告
        
        Args:
            report_data: 报告数据字典
        """
        message = f"""
📊 *每日监控报告*

⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

监控股票数: {report_data.get('total_stocks', 0)}
发现信号数: {report_data.get('signals_found', 0)}
"""
        
        if report_data.get('signals'):
            message += "\n🔔 *今日信号*:\n"
            for signal in report_data['signals']:
                message += f"  • {signal['symbol']}: {signal['type']}\n"
        else:
            message += "\n✅ 今日无信号"
        
        return self.send_message(message)
    
    def send_startup(self):
        """发送启动通知"""
        message = """
🚀 *交易监控系统启动*

系统已启动，开始监控交易信号...

⏰ 启动时间: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return self.send_message(message)

