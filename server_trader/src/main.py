import time
import os
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from src.trader_engine import run_strategy
from src.config import load_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/app/logs/trader.log') if os.path.exists('/app') else logging.FileHandler('trader.log')
    ]
)
logger = logging.getLogger(__name__)

# 加载配置
load_config()

# 从环境变量读取检查间隔
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))


def job():
    """定义需要定时执行的任务"""
    try:
        logger.info("开始执行策略检查...")
        run_strategy()
        logger.info("策略检查执行完毕。")
    except Exception as e:
        logger.error(f"策略检查执行出错: {str(e)}", exc_info=True)


if __name__ == "__main__":
    logger.info("="*60)
    logger.info("交易策略监控服务启动")
    logger.info(f"检查间隔: {CHECK_INTERVAL}秒")
    logger.info("="*60)
    
    # 方式1：使用apscheduler进行精确的定时调度（适合每小时或每天运行）
    # scheduler = BlockingScheduler()
    # # 配置为每小时的0分时刻执行一次 (例如 1:00, 2:00)
    # scheduler.add_job(job, 'cron', minute=0)
    # logger.info("调度器已启动，将按时执行任务。")
    # try:
    #     scheduler.start()
    # except (KeyboardInterrupt, SystemExit):
    #     logger.info("服务已停止")

    # 方式2：简单的循环，每隔N秒执行一次
    # 更适合于需要高频轮询的场景
    try:
        while True:
            job()
            logger.info(f"等待 {CHECK_INTERVAL} 秒后执行下一次检查...")
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        logger.info("收到停止信号，服务正在关闭...")
    except Exception as e:
        logger.error(f"服务异常退出: {str(e)}", exc_info=True)
        raise
