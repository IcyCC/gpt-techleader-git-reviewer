from typing import Optional

from app.infra.git.github.client import GitHubClient
from app.models.bot import Bot
from app.models.comment import Comment
from app.models.git import MergeRequest
from app.models.review import ReviewResult


class ReviewerService:
    def __init__(self):
        self.bot = Bot(
            bot_id="1", name="AI Code Reviewer", status="active", current_reviews=[]
        )
        self.git_client = GitHubClient()

    async def review_mr(self, owner: str, repo: str, mr_id: str) -> ReviewResult:
        print("review_mr", owner, repo, mr_id)
        """处理 MR 审查请求"""
        # 获取 MR 信息
        mr = await self.git_client.get_merge_request(owner, repo, mr_id)
        # 执行审查
        return await self.bot.review_mr(mr)

    async def handle_comment(
        self, owner: str, repo: str, mr_id: str, comment_id: str
    ) -> Comment:
        """处理评论回复"""
        # 获取 MR 信息
        mr = await self.git_client.get_merge_request(owner, repo, mr_id)
        # 获取原始评论
        original_comment = await self.git_client.get_comment(
            owner, repo, mr, comment_id
        )
        # 处理回复
        return await self.bot.handle_comment(mr, original_comment)

    async def retry_review(self, owner: str, repo: str, mr_id: str) -> ReviewResult:
        """重新执行审查"""
        # 获取 MR 信息
        mr = await self.git_client.get_merge_request(owner, repo, mr_id)
        # 重新执行审查
        return await self.bot.review_mr(mr)
