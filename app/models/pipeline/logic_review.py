import logging
from datetime import datetime

from app.infra.ai.client import AIClient, Message
from app.infra.config.settings import get_settings
from app.models.comment import Comment, CommentType
from app.models.git import MergeRequest

from .base import AIReviewResponse, PipelineResult, ReviewPipeline

logger = logging.getLogger(__name__)
settings = get_settings()


class LogicReviewPipeline(ReviewPipeline):
    """业务逻辑审查流水线"""

    def __init__(self):
        super().__init__(
            name="Logic Review", description="Review business logic and implementation"
        )

    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        templates = self.get_prompt_template(settings.GPT_LANGUAGE)

        if settings.GPT_LANGUAGE == "中文":
            return (
                f"{templates['system_role']}\n"
                f"{templates['json_format']}\n"
                "业务分析：\n"
                "1. PR目的\n"
                "2. 实现完整性\n"
                "3. 方案合理性\n"
                "4. 潜在问题\n\n"
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
                "4. Potential issues\n\n"
                "Summary includes:\n"
                "1. Business goal\n"
                "2. Implementation review\n"
                "3. Key suggestions"
            )

    async def review(self, mr: MergeRequest) -> PipelineResult:
        ai_client = AIClient()
        session_id = ai_client.generate_session_id()
        templates = self.get_prompt_template(settings.GPT_LANGUAGE)

        # 构建包含所有文件变更的提示
        files_content = []
        for file_diff in mr.file_diffs:
            # 只包含变更的部分
            files_content.append(
                f"File: {file_diff.file_name}\n"
                f"```diff\n{file_diff.diff_content}\n```"
            )

        all_diffs = "\n\n".join(files_content)

        # 构建业务上下文
        business_context = (
            f"PR信息:\n"
            f"标题: {mr.title}\n"
            f"描述: {mr.description}\n"
            f"变更:\n{all_diffs}"
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
            logger.exception(f"解析AI响应失败: {response[:200]}...")
            ai_review = AIReviewResponse(
                summary="解析审查响应失败", comments=[]
            )

        # 创建评论，每个文件最多保留2条最重要的评论
        comments = []
        file_comment_count = {}
        for ai_comment in ai_review.comments:
            if ai_comment.type == "praise":
                continue
            
            file_path = ai_comment.file_path
            if file_path not in file_comment_count:
                file_comment_count[file_path] = 0
            
            if file_comment_count[file_path] < 2:  # 限制每个文件最多2条评论
                comment = self._from_ai_comment(self.name, ai_comment, mr.mr_id)
                comments.append(comment)
                file_comment_count[file_path] += 1

        return PipelineResult(comments=comments, summary=ai_review.summary)
