import logging
from typing import Any, Optional, Tuple

from fastapi import HTTPException, Request

from app.infra.config.settings import get_settings
from app.models.const import BOT_PREFIX
from app.models.git import MergeRequest

from .client import GitHubClient

logger = logging.getLogger(__name__)
settings = get_settings()


class GitHubWebhookHandler:
    """GitHub Webhook 处理器"""

    def __init__(self):
        self.client = GitHubClient()

    async def handle_webhook(self, request: Request) -> Tuple[str, Optional[Any]]:
        """处理 GitHub webhook 请求

        Returns:
            Tuple[str, Optional[Any]]: (事件类型, 事件数据)
            事件类型可以是：
            - "ping": 首次配置 webhook 时的测试事件
            - "pull_request": PR 相关事件（仅处理首次打开）
            - "pull_request_review_comment": PR 评论事件（仅处理回复）
        """
        # 验证 webhook 签名
        if not await self.client.verify_webhook(request):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

        # 获取事件类型
        event_type = request.headers.get("X-GitHub-Event")
        if not event_type:
            raise HTTPException(status_code=400, detail="Missing event type")

        # 获取请求数据
        payload = await request.json()

        # 获取仓库信息
        owner = payload.get("repository", {}).get("owner", {}).get("login")
        repo = payload.get("repository", {}).get("name")
        logger.info(f"收到 webhook 事件: {event_type}, {owner}/{repo}")

        if not owner or not repo:
            logger.error("无法获取仓库信息")
            raise HTTPException(
                status_code=400, detail="Missing repository information"
            )

        # 检查仓库是否在允许列表中
        if not settings.is_repo_allowed(owner, repo):
            logger.warning(f"仓库不在允许列表中: {owner}/{repo}")
            return event_type, None

        # 处理不同类型的事件
        if event_type == "ping":
            # ping 事件，返回基本信息
            logger.info(f"处理 ping 事件: {owner}/{repo}")
            return "ping", {
                "zen": payload.get("zen"),
                "hook_id": payload.get("hook_id"),
                "repository": {"owner": owner, "name": repo},
            }

        elif event_type == "pull_request":
            # 只处理 PR 首次打开的事件
            action = payload.get("action")
            if action != "opened":
                logger.info(f"忽略 PR 事件: {action}")
                return event_type, None

            pr_number = str(payload["pull_request"]["number"])
            logger.info(f"处理 PR 打开事件: {owner}/{repo}#{pr_number}")

            return event_type, (owner, repo, pr_number)

        elif event_type == "pull_request_review_comment":
            # 只处理评论回复
            action = payload.get("action")
            if action != "created":
                logger.info(f"忽略评论事件: {action}")
                return event_type, None

            # 检查是否是回复评论
            in_reply_to = payload.get("comment", {}).get("in_reply_to_id")
            if not in_reply_to:
                logger.info("忽略非回复类型的评论")
                return event_type, None

            pr_number = str(payload["pull_request"]["number"])
            comment_id = str(payload["comment"]["id"])
            comment_body = payload["comment"]["body"]

            # 检查是否是机器人的评论
            if BOT_PREFIX in comment_body:
                logger.info("忽略机器人的评论")
                return event_type, None

            logger.info(f"处理评论回复事件: {owner}/{repo}#{pr_number} - {comment_id}")
            return event_type, (owner, repo, pr_number, comment_id, comment_body)

        logger.info(f"忽略未知事件类型: {event_type}")
        return event_type, None
