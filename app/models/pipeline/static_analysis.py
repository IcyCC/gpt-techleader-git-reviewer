import logging
from datetime import datetime

from app.infra.ai.client import AIClient, Message
from app.infra.config.settings import get_settings
from app.models.comment import Comment, CommentType
from app.models.git import MergeRequest

from .base import AIReviewResponse, PipelineResult, ReviewPipeline

logger = logging.getLogger(__name__)
settings = get_settings()


class StaticAnalysisPipeline(ReviewPipeline):
    """静态分析流水线"""

    def __init__(self):
        super().__init__(
            name="Static Analysis",
            description="Analyze code style, formatting, and potential issues",
        )

    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        templates = self.get_prompt_template(settings.GPT_LANGUAGE)

        if settings.GPT_LANGUAGE == "中文":
            return (
                f"{templates['system_role']}\n"
                f"{templates['json_format']}\n"
                "关注：\n"
                "1. 代码风格\n"
                "2. 命名规范\n"
                "3. typo"
            )
        else:
            return (
                f"{templates['system_role']}\n"
                f"{templates['json_format']}\n"
                "Focus on:\n"
                "1. Code style\n"
                "2. Naming\n"
                "3. typo"
            )

    async def review(self, mr: MergeRequest) -> PipelineResult:
        ai_client = AIClient()
        session_id = ai_client.generate_session_id()
        templates = self.get_prompt_template(settings.GPT_LANGUAGE)

        # 构建包含所有文件变更的提示
        files_content = []
        for file_diff in mr.file_diffs:
            # 只包含变更的部分，不包含完整文件内容
            files_content.append(
                f"file_old_path: {file_diff.old_file_path}\n"
                f"file_new_path: {file_diff.new_file_path}\n"
                f"```diff\n{file_diff.diff_content}\n```"
            )

        all_diffs = "\n\n".join(files_content)

        system_prompt = Message("system", self._get_system_prompt())
        prompt = Message(
            "user",
            f"{templates['review_request']}\n"
            f"Title: {mr.title}\n"
            f"Changes:\n{all_diffs}",
        )

        response = await ai_client.chat([system_prompt, prompt], session_id=session_id)
        try:
            ai_review = AIReviewResponse.parse_raw_response(response)
        except Exception:
            logger.exception(f"解析AI响应失败: {response[:200]}...")
            ai_review = AIReviewResponse(
                summary="解析审查响应失败", comments=[]
            )

        # 创建评论，每个文件最多保留2条最重要的评论
        comments = []
        for ai_comment in ai_review.comments:
            if ai_comment.type == "praise":
                continue
            comments.append(self._from_ai_comment(self.name, ai_comment, mr.mr_id)) 

        return PipelineResult(comments=comments, summary=ai_review.summary)
