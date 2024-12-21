import logging
from datetime import datetime
from typing import Optional, Tuple

from app.infra.ai.client import AIClient, Message
from app.infra.config.settings import get_settings
from app.infra.rate_limiter import RateLimiter
from app.services.discussion_service import DiscussionService

from .comment import Comment, CommentType, Discussion
from .git import FileDiff, MergeRequest

logger = logging.getLogger(__name__)


class CommentHandler:
    """处理评论回复的类"""

    def __init__(self, bot_name: str):
        self.bot_name = bot_name
        self.discussion_service = DiscussionService()
        self.settings = get_settings()

    async def handle_comment(
        self, mr: MergeRequest, comment: Comment
    ) -> Tuple[Comment, bool]:
        """处理评论回复"""
        rate_limiter = RateLimiter()
        logger.info(f"处理评论: {comment.comment_id}")
        ai_client = AIClient()

        # 检查回复次数限制
        key = rate_limiter.get_comment_replies_key(comment.comment_id)
        if not await rate_limiter.check_and_increment(
            key, self.settings.MAX_COMMENT_REPLIES
        ):
            raise Exception(
                f"此评论已达到最大回复次数限制 ({self.settings.MAX_COMMENT_REPLIES})"
            )

        # 获取讨论上下文
        current_discussion = await self._get_discussion_context(mr, comment)
        if not current_discussion:
            raise Exception(f"无法找到评论所属的讨论: {comment.comment_id}")

        # 构建 AI 提示
        system_prompt, user_prompt = self._build_prompts(mr, current_discussion)

        # 生成回复
        response = await ai_client.chat([system_prompt, user_prompt])
        logger.info(f"AI 生成的回复: {response[:100]}...")

        # 创建回复评论
        reply_comment = Comment(
            comment_id=f"bot_reply_{datetime.utcnow().timestamp()}",
            author=self.bot_name,
            content=response,
            created_at=datetime.utcnow(),
            comment_type=CommentType.REPLY,
            mr_id=comment.mr_id,
            reply_to=comment.comment_id,
        )

        return reply_comment, "[RESOLVED]" in response

    async def _get_discussion_context(
        self, mr: MergeRequest, comment: Comment
    ) -> Optional[Discussion]:
        """获取讨论上下文"""
        discussions = await self.discussion_service.build_discussions(
            mr.owner, mr.repo, mr.mr_id
        )

        for discussion in discussions:
            if any(c.comment_id == comment.comment_id for c in discussion.comments):
                return discussion
        logger.error(f"无法找到评论所属的讨论: {comment.comment_id}")
        return None

    def _build_prompts(self, mr: MergeRequest, discussion) -> tuple[Message, Message]:
        """构建 AI 提示"""
        system_prompt = Message(
            "system",
            "你是一位代码审查助手。请根据上下文提供有帮助的回复。\n"
            "如果你认为问题已经解决，请在回复的末尾添加 '[RESOLVED]'，并简要说明解决原因。\n"
            "如果问题尚未解决，请继续提供建设性的建议。\n"
            "请确保你的回复专业、清晰且有建设性。",
        )

        context = self._build_context(mr, discussion)
        return system_prompt, Message("user", context)

    def _build_context(self, mr: MergeRequest, discussion) -> str:
        """构建上下文信息"""
        context = "这是一个代码审查的讨论。\n\n"
        context += f"Pull Request 信息：\n"
        context += f"标题: {mr.title}\n"
        context += f"描述: {mr.description}\n"

        # 找到与当前讨论相关的文件
        discussion_file = self._get_discussion_file(mr, discussion)
        if discussion_file:
            context += "相关文件变更：\n"
            context += f"文件: {discussion_file.file_name}\n"
            if discussion_file.diff_content:
                context += f"```diff\n{discussion_file.diff_content}\n```\n"
        else:
            logger.warning(f"无法找到讨论相关的文件: {discussion.comments}")

        # 添加讨论历史
        context += "\n当前讨论历史：\n"
        for disc_comment in discussion.comments:
            context += f"{disc_comment.author}: {disc_comment.content}\n"

        context += "\n请根据上述上下文：\n"
        context += "1. 如果问题已经解决，请在回复末尾添加 [RESOLVED] 并说明原因\n"
        context += "2. 如果问题未解决，请继续提供建议\n"
        context += "3. 请直接给出回复内容，不要给出任何解释, 回复只针对当前讨论, 并且尽可能简短。\n"

        return context

    def _get_discussion_file(self, mr: MergeRequest, discussion) -> Optional[FileDiff]:
        """获取讨论相关的文件"""
        if discussion.comments:
            first_comment = discussion.comments[0]
            if first_comment.position and first_comment.position.file_path:
                return next(
                    (
                        diff
                        for diff in mr.file_diffs
                        if diff.file_name == first_comment.position.file_path
                    ),
                    None,
                )
        return None

    async def _try_resolve_discussion(self, mr: MergeRequest, comment: Comment):
        """尝试解决讨论"""
        try:
            await self.discussion_service.resolve_discussion(
                mr.owner, mr.repo, mr.mr_id, comment.comment_id
            )
        except Exception as e:
            logger.exception("解决讨论失败")
