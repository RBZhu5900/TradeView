import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def load_config():
    """加载.env文件到环境变量"""
    # Docker容器中.env文件可能位于不同位置，因此我们直接从环境变量读取
    # load_dotenv()更适用于本地开发
    try:
        # 尝试加载.env文件（如果存在）
        load_dotenv()
        logger.info("正在加载配置...")
        
        # 检查关键环境变量是否设置
        api_key = os.getenv("BROKER_API_KEY")
        if not api_key:
            logger.warning("环境变量 BROKER_API_KEY 未设置！数据获取将使用模拟数据。")
        else:
            logger.info("BROKER_API_KEY 已加载。")
            
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not telegram_token:
            logger.warning("环境变量 TELEGRAM_BOT_TOKEN 未设置！预警功能将无法使用。")
        else:
            logger.info("Telegram配置已加载。")
            
        logger.info("配置加载完成。")
    except Exception as e:
        logger.error(f"配置加载失败: {str(e)}", exc_info=True)
        raise

# 你可以在这里定义更多的配置变量
API_KEY = os.getenv("BROKER_API_KEY")
API_SECRET = os.getenv("BROKER_API_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
