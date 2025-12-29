import requests
import logging
from src import config

logger = logging.getLogger(__name__)

def send_alert(message: str):
    """
    通过Telegram Bot发送预警信息。
    这是一个示例，你可以替换为邮件、钉钉、微信等其他通知方式。
    """
    logger.info(f"准备发送预警")
    logger.debug(f"预警内容: {message}")
    
    if not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("Telegram的TOKEN或CHAT_ID未配置，无法发送预警。预警内容将仅记录在日志中。")
        logger.info(f"[预警内容] {message}")
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': config.TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("预警信息发送成功！")
    except requests.exceptions.Timeout:
        logger.error("发送Telegram预警超时")
    except requests.exceptions.RequestException as e:
        logger.error(f"发送Telegram预警失败: {e}")
    except Exception as e:
        logger.error(f"发送预警时发生未知错误: {e}", exc_info=True)
