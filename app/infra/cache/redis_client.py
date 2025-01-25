import json
from typing import Dict, List, Optional

import aioredis
import asyncio

from app.infra.config.settings import get_settings

settings = get_settings()


class RedisClient:
    def __init__(self):
        self.redis = None
        self.ttl = settings.REDIS_CHAT_TTL
        self.review_ttl = 60 * 60 * 24 * 7  # 7 days TTL for reviewed MRs
        self.max_reviews = settings.MAX_MR_REVIEWS

    async def initialize(self):
        """Initialize Redis connection asynchronously"""
        if self.redis is None:
            self.redis = await aioredis.from_url(settings.REDIS_URL)
        return self

    async def set_chat_history(self, session_id: str, messages: List[Dict[str, str]]):
        """存储聊天历史"""
        if self.redis is None:
            await self.initialize()
        key = f"chat:history:{session_id}"
        await self.redis.set(key, json.dumps(messages), ex=self.ttl)

    async def get_chat_history(self, session_id: str) -> Optional[List[Dict[str, str]]]:
        """获取聊天历史"""
        if self.redis is None:
            await self.initialize()
        key = f"chat:history:{session_id}"
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def delete_chat_history(self, session_id: str):
        """删除聊天历史"""
        if self.redis is None:
            await self.initialize()
        key = f"chat:history:{session_id}"
        await self.redis.delete(key)

    async def increment_mr_review_count(self, owner: str, repo: str, mr_id: str) -> int:
        """增加 MR 审查次数并返回当前次数"""
        if self.redis is None:
            await self.initialize()
        key = f"mr:review_count:{owner}:{repo}:{mr_id}"
        count = await self.redis.incr(key)
        if count == 1:  # 首次设置时添加过期时间
            await self.redis.expire(key, self.review_ttl)
        return count

    async def get_mr_review_count(self, owner: str, repo: str, mr_id: str) -> int:
        """获取 MR 已被审查的次数"""
        if self.redis is None:
            await self.initialize()
        key = f"mr:review_count:{owner}:{repo}:{mr_id}"
        count = await self.redis.get(key)
        return int(count) if count else 0
