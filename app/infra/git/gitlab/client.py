import asyncio
import logging
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional

import aiohttp
from fastapi import HTTPException, Request

from app.infra.config.settings import get_settings
from app.infra.git.base import GitClientBase
from app.models.comment import Comment, CommentPosition, CommentType
from app.models.git import ChangeType, FileDiff, MergeRequest, MergeRequestState

logger = logging.getLogger(__name__)
settings = get_settings()


class GitLabClient(GitClientBase):
    """GitLab API 客户端实现"""

    def __init__(self):
        self.base_url = settings.GITLAB_API_URL
        self.token = settings.GITLAB_TOKEN
        self.webhook_secret = settings.GITLAB_WEBHOOK_SECRET
        self.timeout = aiohttp.ClientTimeout(total=5)  # 5秒超时

    async def _request(self, method: str, url: str, **kwargs) -> Any:
        """发送 HTTP 请求到 GitLab API"""
        headers = {
            "PRIVATE-TOKEN": self.token,
            "Content-Type": "application/json",
        }
        logger.info(f"请求: {method} {url}")
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.request(
                method, f"{self.base_url}{url}", headers=headers, **kwargs, ssl=False
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def get_merge_request(
        self, owner: str, repo: str, mr_id: str
    ) -> MergeRequest:
        """获取合并请求信息"""
        try:
            # GitLab API 使用项目路径: owner/repo
            project_path = f"{owner}/{repo}"
            encoded_project_path = project_path.replace("/", "%2F")
            
            logger.info(f"获取 MR 信息: {project_path}!{mr_id}")
            mr_data = await self._request(
                "GET", 
                f"/projects/{encoded_project_path}/merge_requests/{mr_id}"
            )

            # 获取文件变更
            changes_data = await self._request(
                "GET",
                f"/projects/{encoded_project_path}/merge_requests/{mr_id}/changes?access_raw_diffs=true"
            )

            file_diffs = []
            for change in changes_data.get("changes", []):
                change_type = ChangeType.MODIFY
                if change.get("new_file"):
                    change_type = ChangeType.ADD
                elif change.get("deleted_file"):
                    change_type = ChangeType.DELETE

                file_diff = FileDiff(
                    new_file_path=change["new_path"],
                    old_file_path=change.get("old_path"),
                    change_type=change_type,
                    diff_content=change.get("diff", ""),
                    line_changes={},
                )
                file_diffs.append(file_diff)

            state_map = {
                "opened": MergeRequestState.OPEN,
                "closed": MergeRequestState.CLOSED,
                "merged": MergeRequestState.MERGED,
            }

            return MergeRequest(
                mr_id=str(mr_data["iid"]),
                owner=owner,
                repo=repo,
                title=mr_data["title"],
                author=mr_data["author"]["username"],
                state=state_map.get(mr_data["state"], MergeRequestState.OPEN),
                description=mr_data["description"] or "",
                source_branch=mr_data["source_branch"],
                target_branch=mr_data["target_branch"],
                created_at=datetime.fromisoformat(mr_data["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(mr_data["updated_at"].replace("Z", "+00:00")),
                file_diffs=file_diffs,
                labels=mr_data["labels"],
                reviewers=[
                    reviewer["username"] 
                    for reviewer in mr_data.get("reviewers", [])
                ],
                comments_count=mr_data.get("user_notes_count", 0),
            )
        except Exception as e:
            logger.exception(f"获取 MR 信息失败: {owner}/{repo}!{mr_id}")
            raise
    
    @lru_cache(maxsize=100)
    async def _get_latest_mr_version(self, owner: str, repo: str, mr_id: str):
        mr_data = await self._request(
            "GET",
            f"/projects/{owner}/{repo}/merge_requests/{mr_id}/versions"
        )
        return mr_data[0]
        

    async def create_comment(self, owner: str, repo: str, comment: Comment):
        """创建评论"""
        try:
            project_path = f"{owner}/{repo}"
            encoded_project_path = project_path.replace("/", "%2F")
            
            logger.info(f"创建评论: {project_path}!{comment.mr_id}")
            
            if comment.comment_type == CommentType.FILE:
                # 创建文件评论
                assert comment.position is not None, "File comment requires position"
                url = f"/projects/{encoded_project_path}/merge_requests/{comment.mr_id}/discussions"
                mr_version = await self._get_latest_mr_version(owner, repo, comment.mr_id)
                comment_body = {
                        "body": comment.content,
                        "position": {
                            "position_type": "text",
                            "new_path": comment.position.new_file_path,
                            "new_line": comment.position.new_line_number,
                            "base_sha": mr_version["base_commit_sha"],
                            "start_sha": mr_version["start_commit_sha"],
                            "head_sha": mr_version["head_commit_sha"],
                        }
                    }
                if comment.position.old_file_path:
                    comment_body["position"]["old_path"] = comment.position.old_file_path
                await self._request(
                    "POST",
                    url,
                    json=comment_body,
                )
            elif comment.comment_type == CommentType.REPLY:
                # 回复评论
                assert comment.reply_to is not None, "Reply comment requires reply_to"
                url = f"/projects/{encoded_project_path}/merge_requests/{comment.mr_id}/discussions/{comment.reply_to}/notes"
                await self._request(
                    "POST",
                    url,
                    json={"body": comment.content},
                )
            else:
                # 普通评论
                url = f"/projects/{encoded_project_path}/merge_requests/{comment.mr_id}/notes"
                await self._request(
                    "POST",
                    url,
                    json={"body": comment.content},
                )
        except Exception as e:
            logger.exception(f"创建评论失败: {owner}/{repo}!{comment.mr_id}")
            raise

    async def _convert_gitlab_comment_to_model(
        self, owner: str, repo: str, mr: MergeRequest, note_data: dict
    ) -> Comment:
        """将 GitLab API 返回的评论数据转换为 Comment 模型"""
        position = None
        if "position" in note_data:
            position = CommentPosition(
                new_file_path=note_data["position"]["new_path"],
                new_line_number=note_data["position"]["new_line"],
                old_file_path=note_data["position"]["old_path"],
                old_line_number=note_data["position"]["old_line"],
            )

        comment_type = CommentType.GENERAL
        if position:
            comment_type = CommentType.FILE
        elif note_data.get("type") == "DiscussionNote":
            comment_type = CommentType.REPLY

        return Comment(
            comment_id=str(note_data["id"]),
            author=note_data["author"]["username"],
            content=note_data["body"],
            created_at=datetime.fromisoformat(note_data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(note_data["updated_at"].replace("Z", "+00:00")) if note_data.get("updated_at") else None,
            comment_type=comment_type,
            mr_id=str(mr.mr_id),
            position=position,
            reply_to=str(note_data.get("discussion_id")) if comment_type == CommentType.REPLY else None,
        )

    async def list_comments(
        self, owner: str, repo: str, mr: MergeRequest
    ) -> List[Comment]:
        """获取评论列表"""
        project_path = f"{owner}/{repo}"
        encoded_project_path = project_path.replace("/", "%2F")
        
        # GitLab 中需要同时获取评论和讨论
        notes_data = await self._request(
            "GET",
            f"/projects/{encoded_project_path}/merge_requests/{mr.mr_id}/notes"
        )

        comments = []
        for note_data in notes_data:
            comment = await self._convert_gitlab_comment_to_model(
                owner, repo, mr, note_data
            )
            comments.append(comment)
        return comments

    async def get_comment(
        self, owner: str, repo: str, mr: MergeRequest, comment_id: str
    ) -> Comment:
        """获取评论详情"""
        project_path = f"{owner}/{repo}"
        encoded_project_path = project_path.replace("/", "%2F")
        
        note_data = await self._request(
            "GET",
            f"/projects/{encoded_project_path}/merge_requests/{mr.mr_id}/notes/{comment_id}"
        )

        return await self._convert_gitlab_comment_to_model(
            owner, repo, mr, note_data
        )

    async def verify_webhook(self, request: Request) -> bool:
        """验证 webhook 请求的合法性"""
        try:
            if not self.webhook_secret:
                logger.warning("未配置 webhook secret，跳过验证")
                return True

            token = request.headers.get("X-Gitlab-Token")
            if not token:
                logger.error("请求中缺少 Token")
                return False

            is_valid = token == self.webhook_secret
            if not is_valid:
                logger.error("webhook Token 验证失败")
            return is_valid
        except Exception as e:
            logger.exception("webhook 验证过程中发生错误")
            return False