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
                "作为代码审查者，请从业务角度分析这个PR：\n"
                "1. 分析PR的业务目的和要解决的问题\n"
                "2. 评估代码变更是否完整地实现了业务目的\n"
                "3. 检查实现方案是否合理，是否有更好的方案\n"
                "4. 关注可能影响业务目标实现的潜在问题\n"
                "5. 评估性能、扩展性等对业务的影响\n\n"
                "在summary中请包含：\n"
                "1. PR的业务目的概述\n"
                "2. 代码变更如何实现这个业务目的\n"
                "3. 整体评估和建议\n\n"
                "在具体评论中关注：\n"
                "1. 可能无法完全实现业务目的的代码\n"
                "2. 可能影响业务目标的潜在问题\n"
                "3. 更好的实现方案建议\n"
                "4. 性能或扩展性问题\n"
            )
        else:
            return (
                f"{templates['system_role']}\n"
                f"{templates['json_format']}\n"
                "As a code reviewer, please analyze this PR from a business perspective:\n"
                "1. Analyze the business purpose and problems to be solved\n"
                "2. Evaluate if the code changes fully implement the business purpose\n"
                "3. Check if the implementation is reasonable and if there are better approaches\n"
                "4. Focus on potential issues that may affect business goals\n"
                "In the summary, please include:\n"
                "1. Overview of PR's business purpose\n"
                "2. How code changes implement this business purpose\n"
                "In specific comments, focus on:\n"
                "1. Code that may not fully achieve business goals\n"
                "2. Potential issues affecting business objectives\n"
            )

    async def review(self, mr: MergeRequest) -> PipelineResult:
        logger.info(f"开始业务逻辑审查: {mr.mr_id}")
        ai_client = AIClient()
        session_id = ai_client.generate_session_id()
        all_comments = []
        templates = self.get_prompt_template(settings.GPT_LANGUAGE)
        system_prompt = Message("system", self._get_system_prompt())
        # 构建包含所有文件变更的提示
        files_content = []
        for file_diff in mr.file_diffs:
            files_content.append(
                f"File: {file_diff.file_name}\n"
                f"```diff\n{file_diff.diff_content}\n```"
            )

        all_diffs = "\n\n".join(files_content)

        # 构建业务上下文
        business_context = (
            f"Pull Request 信息:\n"
            f"标题: {mr.title}\n"
            f"描述: {mr.description}\n"
            f"作者: {mr.author}\n"
            f"分支: {mr.source_branch} -> {mr.target_branch}\n\n"
            f"代码变更:\n{all_diffs}"
        )

        prompt = Message(
            "user",
            f"{templates['review_request']}\n"
            f"请从业务角度分析这个PR的目的和实现：\n\n"
            f"{business_context}",
        )

        overview_response = await ai_client.chat(
            [system_prompt, prompt], session_id=session_id
        )
        try:
            overview_result = AIReviewResponse.parse_raw_response(overview_response)
        except Exception:
            logger.exception(f"解析AI响应失败: {overview_response[:200]}...")
            overview_result = AIReviewResponse(
                summary=f"解析AI响应失败, {overview_response}...", comments=[]
            )

        # 添加评论，过滤掉纯赞扬性质的评论
        for ai_comment in overview_result.comments:
            if ai_comment.type == "praise":
                continue
            comment = self._from_ai_comment(self.name, ai_comment, mr.mr_id)
            all_comments.append(comment)

        logger.info(f"业务逻辑审查完成: {mr.mr_id}, 生成评论数: {len(all_comments)}")
        return PipelineResult(comments=all_comments, summary=overview_result.summary)
