import asyncio
import logging
import sys

import uvicorn
from uvicorn.config import Config
from uvicorn.server import Server

from app.main import app

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


async def main():
    try:
        logger.info("正在启动调试服务器...")
        config = Config(app=app, host="0.0.0.0", port=8000, log_level="debug")
        server = Server(config=config)

        # 启动服务器
        logger.info("服务器配置完成，开始启动...")
        await server.serve()
    except Exception as e:
        logger.exception("服务器启动过程中发生错误")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("收到中断信号，服务器正在关闭...")
    except Exception as e:
        logger.exception("服务器运行过程中发生错误")
        sys.exit(1)
