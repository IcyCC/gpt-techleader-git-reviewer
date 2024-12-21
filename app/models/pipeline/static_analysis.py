from datetime import datetime
from app.models.git import MergeRequest
from app.models.comment import Comment, CommentType
from app.infra.ai.client import AIClient, Message
from app.infra.config.settings import get_settings
from .base import ReviewPipeline, PipelineResult, AIReviewResponse
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

class StaticAnalysisPipeline(ReviewPipeline):
    """静态分析流水线"""
    def __init__(self):
        super().__init__(
            name="Static Analysis",
            description="Analyze code style, formatting, and potential issues"
        )

    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        templates = self.get_prompt_template(settings.GPT_LANGUAGE)
        
        if settings.GPT_LANGUAGE == "中文":
            return (
                f"{templates['system_role']}\n"
                f"{templates['json_format']}\n"
                "重点关注以下方面：\n"
                "1. 代码风格和格式\n"
                "2. 命名规范\n"
                "3. 基本代码异味\n"
                "4. 潜在的语法问题"
            )
        else:
            return (
                f"{templates['system_role']}\n"
                f"{templates['json_format']}\n"
                "Focus on:\n"
                "1. Code style and formatting\n"
                "2. Naming conventions\n"
                "3. Basic code smells\n"
                "4. Potential syntax issues"
            )

    async def review(self, mr: MergeRequest) -> PipelineResult:
        try:
            logger.info(f"开始静态分析: {mr.mr_id}")
            ai_client = AIClient()
            session_id = ai_client.generate_session_id()
            templates = self.get_prompt_template(settings.GPT_LANGUAGE)
            
            # 构建包含所有文件变更的提示
            files_content = []
            for file_diff in mr.file_diffs:
                files_content.append(
                    f"File: {file_diff.file_name}\n"
                    f"```\n{file_diff.diff_content}\n```"
                )
            
            all_diffs = "\n\n".join(files_content)
            
            system_prompt = Message("system", self._get_system_prompt())
            prompt = Message("user",
                f"{templates['review_request']}\n"
                f"Pull Request Title: {mr.title}\n"
                f"Description: {mr.description}\n\n"
                f"Changes:\n{all_diffs}"
            )
            
            response = await ai_client.chat([system_prompt, prompt], session_id=session_id)
            ai_review = AIReviewResponse.parse_raw_response(response)
            
            # 创建评论
            comments = []
            for ai_comment in ai_review.comments:
                if ai_comment.type == "praise":
                    continue
                comment = self._from_ai_comment(self.name, ai_comment, mr.mr_id)
                comments.append(comment)
            
            logger.info(f"静态分析完成: {mr.mr_id}, 生成评论数: {len(comments)}")
            return PipelineResult(
                comments=comments,
                summary=ai_review.summary
            )
            
        except Exception:
            logger.exception(f"静态分析失败: {mr.mr_id}")