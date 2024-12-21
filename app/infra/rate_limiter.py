import aioredis
from app.infra.config.settings import get_settings
import logging

settings = get_settings()   
logger = logging.getLogger(__name__)

class RateLimiter:
    """速率限制器"""
    def __init__(self):
        self.redis = aioredis.from_url(settings.REDIS_URL)
        self.settings = get_settings()

    async def check_and_increment(self, key: str, max_count: int) -> bool:
        """
        检查并增加计数
        
        Args:
            key: Redis 键名
            max_count: 最大允许次数
            
        Returns:
            bool: 是否允许继续执行
        """
        try:
            # 获取当前计数
            count = await self.redis.get(key)
            if count is None:
                # 如果键不存在，创建并设置过期时间
                await self.redis.set(key, 1, ex=self.settings.RATE_LIMIT_EXPIRE)
                return True
            
            count = int(count)
            if count >= max_count:
                logger.warning(f"达到速率限制: {key}, 当前: {count}, 最大: {max_count}")
                return False
            
            # 增加计数
            await self.redis.incr(key)
            return True
            
        except Exception as e:
            logger.exception(f"检查速率限制失败: {str(e)}")
            return False

    async def get_remaining(self, key: str, max_count: int) -> int:
        """获取剩余可用次数"""
        try:
            count = await self.redis.get(key)
            if count is None:
                return max_count
            return max(0, max_count - int(count))
        except Exception as e:
            logger.exception(f"获取剩余次数失败: {str(e)}")
            return 0

    def get_ai_requests_key(self) -> str:
        """获取 AI 请求限制的键名"""
        return "rate_limit:ai_requests"

    def get_mr_reviews_key(self) -> str:
        """获取 MR 审查限制的键名"""
        return "rate_limit:mr_reviews"

    def get_comment_replies_key(self, comment_id: str) -> str:
        """获取评论回复限制的键名"""
        return f"rate_limit:comment_replies:{comment_id}" 