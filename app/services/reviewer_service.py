from typing import Optional

from app.infra.git.factory import GitClientFactory
from app.models.bot import Bot
from app.models.comment import Comment
from app.models.git import MergeRequest
from app.models.review import ReviewResult
from app.infra.cache.redis_client import RedisClient
from app.infra.config.settings import get_settings


class ReviewerService:
    def __init__(self):
        self.bot = Bot(
            bot_id="1", name="AI Code Reviewer", status="active", current_reviews=[]
        )
        self.git_client = GitClientFactory.get_client()
        self.redis_client = RedisClient()
        self.settings = get_settings()

    async def review_mr(self, owner: str, repo: str, mr_id: str, check_limit: bool = True) -> ReviewResult:
        # 检查审查次数
        if check_limit:
            review_count = await self.redis_client.get_mr_review_count(owner, repo, mr_id)
            if review_count >= self.settings.MAX_MR_REVIEWS:
                raise RuntimeError(f"MR {owner}/{repo}#{mr_id} has reached the maximum review limit of {self.settings.MAX_MR_REVIEWS}")

        # 获取 MR 信息并执行审查
        mr = await self.git_client.get_merge_request(owner, repo, mr_id)
        result = await self.bot.review_mr(mr)
        
        # 增加审查次数
        await self.redis_client.increment_mr_review_count(owner, repo, mr_id)
        
        return result

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
