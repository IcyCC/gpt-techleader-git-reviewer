import logging
from datetime import datetime
from typing import List, Optional, Tuple

from pydantic import BaseModel

from app.infra.config.settings import get_settings
from app.infra.git.github.client import GitHubClient
from app.infra.rate_limiter import RateLimiter
from app.models.const import BOT_PREFIX

from .comment import Comment, CommentType
from .comment_handler import CommentHandler
from .git import MergeRequest
from .pipeline import LogicReviewPipeline, ReviewPipeline, StaticAnalysisPipeline
from .review import ReviewResult
from .size_checker import SizeChecker

logger = logging.getLogger(__name__)


class Bot(BaseModel):
    bot_id: str
    name: str
    status: str
    current_reviews: List[str] = []
    pipelines: List[ReviewPipeline] = []

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)
        self.pipelines = [StaticAnalysisPipeline(), LogicReviewPipeline()]

    async def _handle_review_mr(
        self, mr: MergeRequest
    ) -> Tuple[ReviewResult, List[Comment]]:
        settings = get_settings()
        rate_limiter = RateLimiter()
        # 检查 MR 处理次数限制
        if not await rate_limiter.check_and_increment(
            rate_limiter.get_mr_reviews_key(), settings.MAX_MR_REVIEWS_PER_HOUR
        ):
            return (
                ReviewResult(
                    mr_id=mr.mr_id,
                    summary=f"⚠️ 已达到每小时最大处理 MR 数限制 ({settings.MAX_MR_REVIEWS_PER_HOUR})，请稍后再试。",
                    overall_status="error",
                    review_date=datetime.utcnow(),
                ),
                [],
            )

        all_comments = []
        summaries = []
        failed_pipelines = []

        # 检查 MR 大小
        size_checker = SizeChecker(self.name)
        mr_size_result = size_checker.check_mr_size(mr)
        if mr_size_result:
            return mr_size_result

        # 检查文件大小
        large_files, normal_files = size_checker.check_files_size(mr)
        if large_files:
            for file_diff in large_files:
                comment = size_checker.create_large_file_comment(
                    mr, file_diff, file_diff.diff_content.count("\n") + 1
                )
                all_comments.append(comment)
            summaries.append(size_checker.create_large_files_summary(large_files))
        # 更新 MR 的文件列表，只包含正常大小的文件
        mr.file_diffs = normal_files

        # 执行每个 pipeline
        for pipeline in self.pipelines:
            if not pipeline.enabled:
                logger.info(f"pipeline {pipeline.name} 未启用")
                continue
            try:
                logger.info(f"执行 pipeline: {pipeline.name} for MR #{mr.mr_id}")
                result = await pipeline.review(mr)
                all_comments.extend(result.comments)
                if result.summary:
                    summaries.append(f"[{pipeline.name}] {result.summary}")
            except Exception as e:
                logger.exception(f"Pipeline {pipeline.name} 执行失败: {str(e)}")
                failed_pipelines.append((pipeline.name, str(e)))
                continue

        # 创建总结评论
        if failed_pipelines:
            summaries.append(
                f"\n⚠️ 以下 pipeline 执行失败: {', '.join([f'{name}: {error}' for name, error in failed_pipelines])}"
            )

        # 如果所有 pipeline 都失败了
        if len(failed_pipelines) == len([p for p in self.pipelines if p.enabled]):
            logger.error(f"所有 pipeline 都失败了: {failed_pipelines}")
            return (
                ReviewResult(
                    mr_id=mr.mr_id,
                    summary="\n".join(summaries),
                    overall_status="error",
                    review_date=datetime.utcnow(),
                ),
                [],
            )

        return (
            ReviewResult(
                mr_id=mr.mr_id,
                summary="\n".join(summaries),
                overall_status="commented",
                review_date=datetime.utcnow(),
            ),
            all_comments,
        )

    async def review_mr(self, mr: MergeRequest) -> ReviewResult:
        """执行 MR 审查"""
        git_client = GitHubClient()
        result, all_comments = await self._handle_review_mr(mr)
        if result.summary:
            summary_comment = Comment(
                comment_id=f"summary_{datetime.utcnow().timestamp()}",
                author=self.name,
                content=result.summary,
                created_at=datetime.utcnow(),
                comment_type=CommentType.GENERAL,
                mr_id=mr.mr_id,
            )
            all_comments.append(summary_comment)

        for comment in all_comments:
            try:
                await self._post_comment(git_client, mr, comment)
            except Exception as e:
                logger.exception(f"评论发布失败: {comment.model_dump_json()}")
        return result

    async def handle_comment(
        self, mr: MergeRequest, comment: Comment
    ) -> Optional[Comment]:
        """处理评论回复"""
        comment_handler = CommentHandler(self.name)
        comment, resolved = await comment_handler.handle_comment(mr, comment)
        git_client = GitHubClient()
        await self._post_comment(git_client, mr, comment)
        if resolved:
            await git_client.resolve_review_thread(
                mr.owner, mr.repo, mr.mr_id, comment.comment_id
            )
        return comment

    @staticmethod
    async def _post_comment(
        git_client: GitHubClient, mr: MergeRequest, comment: Comment
    ):
        """发布评论到 Git 平台"""
        try:
            comment.content = f"{BOT_PREFIX} {comment.content}"
            await git_client.create_comment(mr.owner, mr.repo, comment)
            logger.info(f"评论发布成功: {comment.comment_id}")
        except Exception as e:
            logger.exception(f"评论发布失败: {comment.model_dump_json()}")
            raise
