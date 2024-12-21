import asyncio
import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
from fastapi import HTTPException, Request

from app.infra.config.settings import get_settings
from app.infra.git.base import GitClientBase
from app.models.comment import Comment, CommentPosition, CommentType
from app.models.git import ChangeType, FileDiff, MergeRequest, MergeRequestState

logger = logging.getLogger(__name__)
settings = get_settings()


class GitHubClient(GitClientBase):
    """GitHub API 客户端实现"""

    def __init__(self):
        self.base_url = "https://api.github.com"
        self.token = settings.GITHUB_TOKEN
        self.github_api_url = settings.GITHUB_API_URL
        self.webhook_secret = settings.GITHUB_WEBHOOK_SECRET
        self.timeout = aiohttp.ClientTimeout(total=5)  # 5秒超时

    async def _request(self, method: str, url: str, **kwargs) -> Any:
        """发送 HTTP 请求到 GitHub API"""
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }
        logger.info(f"请求: {method} {url}")
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.request(
                method, f"{self.github_api_url}{url}", headers=headers, **kwargs
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def get_merge_request(
        self, owner: str, repo: str, mr_id: str
    ) -> MergeRequest:
        """获取合并请求信息"""
        try:
            logger.info(f"获取 PR 信息: {owner}/{repo}#{mr_id}")
            pr_data = await self._request("GET", f"/repos/{owner}/{repo}/pulls/{mr_id}")

            # 获取文件变更
            files_data = await self._request(
                "GET", f"/repos/{owner}/{repo}/pulls/{mr_id}/files"
            )

            file_diffs = []
            for file in files_data:
                change_type = ChangeType.MODIFY
                if file["status"] == "added":
                    change_type = ChangeType.ADD
                elif file["status"] == "removed":
                    change_type = ChangeType.DELETE

                file_diff = FileDiff(
                    file_name=file["filename"],
                    change_type=change_type,
                    diff_content=file.get("patch", ""),
                    line_changes={},
                )
                file_diffs.append(file_diff)

            state_map = {
                "open": MergeRequestState.OPEN,
                "closed": MergeRequestState.CLOSED,
                "merged": MergeRequestState.MERGED,
            }

            return MergeRequest(
                mr_id=str(pr_data["number"]),
                owner=owner,
                repo=repo,
                title=pr_data["title"],
                author=pr_data["user"]["login"],
                state=state_map.get(pr_data["state"], MergeRequestState.OPEN),
                description=pr_data["body"] or "",
                source_branch=pr_data["head"]["ref"],
                target_branch=pr_data["base"]["ref"],
                created_at=datetime.fromisoformat(
                    pr_data["created_at"].replace("Z", "+00:00")
                ),
                updated_at=datetime.fromisoformat(
                    pr_data["updated_at"].replace("Z", "+00:00")
                ),
                file_diffs=file_diffs,
                labels=[label["name"] for label in pr_data["labels"]],
                reviewers=[
                    reviewer["login"] for reviewer in pr_data["requested_reviewers"]
                ],
                comments_count=pr_data["comments"],
            )
        except Exception as e:
            logger.exception(f"获取 PR 信息失败: {owner}/{repo}#{mr_id}")
            raise

    async def get_file_content(
        self, owner: str, repo: str, mr: MergeRequest, file_path: str
    ) -> Optional[str]:
        """获取指定文件的内容"""
        try:
            content_data = await self._request(
                "GET",
                f"/repos/{owner}/{repo}/contents/{file_path}",
                params={"ref": mr.source_branch},
            )
            import base64

            return base64.b64decode(content_data["content"]).decode("utf-8")
        except Exception:
            return None

    async def create_comment(self, owner: str, repo: str, comment: Comment):
        """创建评论"""
        try:
            logger.info(f"创建评论: {owner}/{repo}#{comment.mr_id}")
            if comment.comment_type == CommentType.FILE:
                # 获取最新的 commit SHA
                pr_data = await self._request(
                    "GET", f"/repos/{owner}/{repo}/pulls/{comment.mr_id}"
                )
                commit_id = pr_data["head"]["sha"]

                # 创建文件评论
                assert comment.position is not None, "File comment requires position"
                url = f"/repos/{owner}/{repo}/pulls/{comment.mr_id}/comments"
                await self._request(
                    "POST",
                    url,
                    json={
                        "body": comment.content,
                        "commit_id": commit_id,
                        "path": comment.position.file_path,
                        "line": comment.position.new_line_number,
                        "side": "RIGHT",
                    },
                )
            elif comment.comment_type == CommentType.REPLY:
                # 回复评论
                assert comment.reply_to is not None, "Reply comment requires reply_to"

                # 创建回复
                url = f"/repos/{owner}/{repo}/pulls/{comment.mr_id}/comments/{comment.reply_to}/replies"
                await self._request("POST", url, json={"body": comment.content})

            else:
                # 普通评论 - 使用 issue comments API
                url = f"/repos/{owner}/{repo}/issues/{comment.mr_id}/comments"
                await self._request("POST", url, json={"body": comment.content})
        except Exception as e:
            logger.exception(f"创建评论失败: {owner}/{repo}#{comment.mr_id}")
            raise

    async def resolve_review_thread(
        self, owner: str, repo: str, mr_id: str, thread_id: str
    ):
        pass

    async def _convert_github_comment_to_model(
        self, owner: str, repo: str, mr: MergeRequest, comment_data: dict
    ) -> Comment:
        """将 GitHub API 返回的评论数据转换为 Comment 模型"""
        # 创建评论位置（如果有）
        position = None
        if "path" in comment_data and ("line" in comment_data or "original_line" in comment_data):
            line_no = comment_data["line"] if comment_data["line"] else comment_data["original_line"]
            position = CommentPosition(
                file_path=comment_data["path"], new_line_number=line_no
            )

        # 确定评论类型
        comment_type = CommentType.GENERAL
        if position:
            comment_type = CommentType.FILE
        elif comment_data.get("in_reply_to_id"):
            comment_type = CommentType.REPLY

        return Comment(
            comment_id=str(comment_data["id"]),
            author=comment_data["user"]["login"],
            content=comment_data["body"],
            created_at=datetime.fromisoformat(
                comment_data["created_at"].replace("Z", "+00:00")
            ),
            updated_at=(
                datetime.fromisoformat(
                    comment_data["updated_at"].replace("Z", "+00:00")
                )
                if comment_data.get("updated_at")
                else None
            ),
            comment_type=comment_type,
            mr_id=str(mr.mr_id),
            position=position,
            reply_to=(
                str(comment_data["in_reply_to_id"])
                if comment_data.get("in_reply_to_id")
                else None
            ),
        )

    async def list_comments(
        self, owner: str, repo: str, mr: MergeRequest
    ) -> List[Comment]:
        """获取评论列表"""
        url = f"/repos/{owner}/{repo}/pulls/{mr.mr_id}/comments"
        comments_data = await self._request("GET", url)

        comments = []
        for comment_data in comments_data:
            comment = await self._convert_github_comment_to_model(
                owner, repo, mr, comment_data
            )
            comments.append(comment)
        return comments

    async def get_comment(
        self, owner: str, repo: str, mr: MergeRequest, comment_id: str
    ) -> Comment:
        """获取评论详情"""
        # 获取评论数据
        comment_data = await self._request(
            "GET", f"/repos/{owner}/{repo}/pulls/comments/{comment_id}"
        )

        return await self._convert_github_comment_to_model(
            owner, repo, mr, comment_data
        )

    async def verify_webhook(self, request: Request) -> bool:
        """验证 webhook 请求的合法性"""
        try:
            if not self.webhook_secret:
                logger.warning("未配置 webhook secret，跳过验证")
                return True

            signature = request.headers.get("X-Hub-Signature-256")
            if not signature:
                logger.error("请求中缺少签名")
                return False

            payload_body = await request.body()

            # 计算签名
            hmac_gen = hmac.new(
                self.webhook_secret.encode(), payload_body, hashlib.sha256
            )
            expected_signature = f"sha256={hmac_gen.hexdigest()}"

            is_valid = hmac.compare_digest(signature, expected_signature)
            if not is_valid:
                logger.error("webhook 签名验证失败")
            return is_valid
        except Exception as e:
            logger.exception("webhook 验证过程中发生错误")
            return False

    async def parse_webhook_event(
        self, request: Request
    ) -> Optional[tuple[str, str, str]]:
        """解析 webhook 事件，返回 (owner, repo, pr_number)"""
        event_type = request.headers.get("X-GitHub-Event")
        if event_type != "pull_request":
            return None

        payload = await request.json()
        action = payload["action"]
        if action not in ["opened", "reopened", "synchronize"]:
            return None

        owner = payload["repository"]["owner"]["login"]
        repo = payload["repository"]["name"]
        pr_number = str(payload["pull_request"]["number"])

        return owner, repo, pr_number
