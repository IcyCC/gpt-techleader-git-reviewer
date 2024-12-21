import json
from typing import Dict, List, Optional

import aioredis

from app.infra.config.settings import get_settings

settings = get_settings()


class RedisClient:
    def __init__(self):
        self.redis = aioredis.from_url(settings.REDIS_URL)
        self.ttl = settings.REDIS_CHAT_TTL

    async def set_chat_history(self, session_id: str, messages: List[Dict[str, str]]):
        """存储聊天历史"""
        key = f"chat:history:{session_id}"
        await self.redis.set(key, json.dumps(messages), ex=self.ttl)

    async def get_chat_history(self, session_id: str) -> Optional[List[Dict[str, str]]]:
        """获取聊天历史"""
        key = f"chat:history:{session_id}"
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def delete_chat_history(self, session_id: str):
        """删除聊天历史"""
        key = f"chat:history:{session_id}"
        await self.redis.delete(key)
