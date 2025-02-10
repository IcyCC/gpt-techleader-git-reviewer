import logging
from datetime import datetime

from app.infra.ai.client import AIClient, Message
from app.infra.config.settings import get_settings
from app.models.comment import Comment, CommentType
from app.models.git import MergeRequest

from .base import AIReviewResponse, PipelineResult, ReviewPipeline

logger = logging.getLogger(__name__)
settings = get_settings()


class CodeReviewPipeline(ReviewPipeline):
    """Comprehensive code review pipeline that handles both logic and static analysis"""

    def __init__(self):
        super().__init__(
            name="Code Review",
            description="Review business logic, implementation, code style and potential issues",
        )

    def _get_system_prompt(self) -> str:
        """Get system prompt for the AI reviewer"""
        templates = self.get_prompt_template(settings.GPT_LANGUAGE)

        if settings.GPT_LANGUAGE == "中文":
            return (
                f"{templates['system_role']}\n"
                f"{templates['json_format']}\n"
                "业务分析：\n"
                "1. PR目的\n"
                "2. 实现完整性\n"
                "3. 方案合理性\n"
                "\n"
                "代码分析：\n"
                "1. 代码风格\n"
                "2. 命名规范\n"
                "3. 潜在问题\n"
                "4. 性能考虑\n"
                "5. 代码和mr标题内容的拼写错误\n"
                "6. mr标题和描述是否能反应变更内容\n"
                "\n"
                "总结包含：\n"
                "1. 业务目的\n"
                "2. 实现评估\n"
                "3. 主要建议"
            )
        else:
            return (
                f"{templates['system_role']}\n"
                f"{templates['json_format']}\n"
                "Business Analysis:\n"
                "1. PR purpose\n"
                "2. Implementation completeness\n"
                "3. Solution design\n"
                "\n"
                "Code Analysis:\n"
                "1. Code style\n"
                "2. Naming conventions\n"
                "3. Potential issues\n"
                "4. Performance considerations\n"
                "5. Spelling errors and typo in code and mr title\n"
                "6. Whether the mr title and description can reflect the changes\n"
                "Summary includes:\n"
                "1. Business goal\n"
                "2. Implementation review\n"
                "3. Key suggestions"
            )

    async def review(self, mr: MergeRequest) -> PipelineResult:
        ai_client = AIClient()
        session_id = ai_client.generate_session_id()
        templates = self.get_prompt_template(settings.GPT_LANGUAGE)

        # Build prompt with all file changes
        files_content = []
        for file_diff in mr.file_diffs:
            files_content.append(
                f"file_old_path: {file_diff.old_file_path}\n"
                f"file_new_path: {file_diff.new_file_path}\n"
                f"```diff\n{file_diff.diff_content}\n```"
            )

        all_diffs = "\n\n".join(files_content)

        # Build business context
        if settings.GPT_LANGUAGE == "中文":
            business_context = (
                f"PR信息:\n"
                f"标题: {mr.title}\n"
                f"描述: {mr.description}\n"
                f"变更:\n{all_diffs}"
            )
        else:
            business_context = (
                f"PR information:\n"
                f"Title: {mr.title}\n"
                f"Description: {mr.description}\n"
                f"Changes:\n{all_diffs}"
            )

        system_prompt = Message("system", self._get_system_prompt())
        prompt = Message(
            "user",
            f"{templates['review_request']}\n{business_context}",
        )

        response = await ai_client.chat([system_prompt, prompt], session_id=session_id)
        try:
            ai_review = AIReviewResponse.parse_raw_response(response)
        except Exception:
            logger.exception(f"Failed to parse AI response: {response[:200]}...")
            ai_review = AIReviewResponse(
                summary="Failed to parse review response", comments=[]
            )

        comments = []
        for ai_comment in ai_review.comments:
            if ai_comment.type == "praise":
                continue
            comment = self._from_ai_comment(self.name, ai_comment, mr.mr_id)
            comments.append(comment)

        return PipelineResult(comments=comments, summary=ai_review.summary) 