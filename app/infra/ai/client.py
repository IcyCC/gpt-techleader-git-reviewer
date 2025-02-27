import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
import httpx
from openai import OpenAI

from app.infra.cache.redis_client import RedisClient
from app.infra.config.settings import get_settings
from app.infra.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)
settings = get_settings()


class Message:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, str]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }


class AIClient:
    def __init__(self):
        self.http_client = httpx.Client(verify=False)
        self.client = OpenAI(
            api_key=settings.GPT_API_KEY, base_url=settings.GPT_API_URL, http_client=self.http_client
        )
        self.model = settings.GPT_MODEL
        self.redis_client = RedisClient()
        self.use_debug_cache = settings.USE_AI_DEBUG_CACHE
        self.cache_dir = Path(settings.AI_CACHE_DIR)
        self.timeout = settings.GPT_TIMEOUT
        self.rate_limiter = RateLimiter()
        self.max_tokens = settings.MAX_TOKENS
        
    def _count_tokens(self, text: str) -> int:
        """计算文本的 token 数量"""
        return len(text) // 4

    def _check_max_tokens(
        self, messages: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """截断消息以确保不超过最大 token 限制"""
        total_tokens = 0
        # 从最新的消息开始计算
        for msg in reversed(messages):
            msg_tokens = self._count_tokens(msg["content"])
            total_tokens = total_tokens + msg_tokens
        logger.debug(f"消息总 token: {total_tokens}")
        if total_tokens > self.max_tokens:
            raise RuntimeError(f"消息总 token 超过最大限制: {total_tokens}, 最大限制: {self.max_tokens}")
        return messages

    

    @staticmethod
    def generate_session_id() -> str:
        """生成会话ID"""
        return str(uuid.uuid4())

    async def get_chat_history(self, session_id: str) -> List[Message]:
        """获取聊天历史"""
        history = await self.redis_client.get_chat_history(session_id)
        if history:
            return [
                Message(role=msg["role"], content=msg["content"]) for msg in history
            ]
        return []

    def _get_cached_response(self, messages: List[Message]) -> Optional[str]:
        """从缓存获取响应"""
        if not self.use_debug_cache:
            return None

        try:
            # 使用最后一条用户消息作为缓存键
            user_messages = [msg for msg in messages if msg.role == "user"]
            if not user_messages:
                return None

            last_user_msg = user_messages[-1].content
            cache_key = last_user_msg.lower().replace(" ", "_")[:50] + ".json"
            cache_file = self.cache_dir / cache_key

            # 如果缓存文件不存在，使用默认响应
            if not cache_file.exists():
                return None

            with open(cache_file, "r", encoding="utf-8") as f:
                response = f.read()
                logger.debug(f"使用缓存响应: {cache_key}")
                return response
        except Exception as e:
            logger.exception("读取缓存响应失败")
            return None

    def _save_to_cache(self, messages: List[Message], response: str):
        """保存响应到缓存"""
        if not self.use_debug_cache:
            return

        try:
            user_messages = [msg for msg in messages if msg.role == "user"]
            if not user_messages:
                return

            last_user_msg = user_messages[-1].content
            cache_key = last_user_msg.lower().replace(" ", "_")[:50] + ".json"
            cache_file = self.cache_dir / cache_key

            os.makedirs(self.cache_dir, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(response)
            logger.debug(f"保存响应到缓存: {cache_key}")
        except Exception as e:
            logger.exception("保存响应到缓存失败")

    async def chat(
        self,
        messages: List[Message],
        session_id: Optional[str] = None,
        temperature: float = settings.GPT_TEMPERATURE,
        stream: bool = False,
    ) -> str:
        """发送消息到 AI 并获取回复"""
        # 检查是否使用缓存
        if self.use_debug_cache:
            cached_response = self._get_cached_response(messages)
            if cached_response:
                logger.info("使用缓存的响应")
                return cached_response

        # 检查速率限制
        key = self.rate_limiter.get_ai_requests_key()
        if not await self.rate_limiter.check_and_increment(
            key, settings.MAX_AI_REQUESTS_PER_HOUR
        ):
            raise RuntimeError(
                f"已达到每小时 AI 请求限制 ({settings.MAX_AI_REQUESTS_PER_HOUR})"
            )

        logger.info("开始 AI 对话")
        # 如果提供了session_id，获取历史记录
        chat_messages = []
        if session_id:
            history = await self.get_chat_history(session_id)
            chat_messages.extend([msg.to_dict() for msg in history])

        # 添加新消息
        chat_messages.extend([msg.to_dict() for msg in messages])

        # 截断消息以符合 token 限制
        self._check_max_tokens(chat_messages)

        # 调用 API
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": msg["role"], "content": msg["content"]}
                for msg in chat_messages
            ],
            timeout=self.timeout,
            temperature=temperature,
            stream=stream,
        )

        # 获取响应
        if stream:
            full_response = []
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    full_response.append(chunk.choices[0].delta.content)
            response_text = "".join(full_response)
        else:
            response_text = completion.choices[0].message.content

        # 保存到缓存
        if self.use_debug_cache:
            self._save_to_cache(messages, response_text)

        # 如果有session_id，保存对话历史
        if session_id:
            chat_messages.append(
                {
                    "role": "assistant",
                    "content": response_text,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            await self.redis_client.set_chat_history(session_id, chat_messages)

        return response_text

    async def clear_chat_history(self, session_id: str):
        """清除聊天历史"""
        await self.redis_client.delete_chat_history(session_id)
        logger.info(f"清除聊天历史: {session_id}")