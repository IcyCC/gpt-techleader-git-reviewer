import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel

from app.infra.ai.client import AIClient, Message
from app.infra.config.settings import get_settings

from .comment import Comment, CommentPosition, CommentType
from .git import FileDiff, MergeRequest

settings = get_settings()

logger = logging.getLogger(__name__)


class AIReviewComment(BaseModel):
    """AI 返回的评论结构"""

    file_path: str
    line_number: Optional[int] = 1
    content: str
    type: str = "suggestion"  # suggestion, issue, praise


def extract_json(text):
    start = -1
    stack = []
    for i, char in enumerate(text):
        if char == "{":
            if not stack:
                start = i  # 记录最外层 JSON 的起始位置
            stack.append(char)
        elif char == "}":
            if stack:
                stack.pop()
                if not stack:
                    # 如果栈为空，说明找到了完整的最外层 JSON
                    return text[start : i + 1]
    return None


class AIReviewResponse(BaseModel):
    """AI 返回的审查结果结构"""

    summary: str = ""
    comments: List[AIReviewComment] = []

    @classmethod
    def parse_raw_response(cls, response: str) -> "AIReviewResponse":
        """解析 AI 返回的 JSON 字符串，支持多种格式"""
        try:
            # 匹配各种格式的JSON

            # 首先尝试直接解析为JSON
            json_str = extract_json(response.strip())

            assert json_str is not None, "无法解析JSON"
            data = json.loads(json_str)
            # 如果所有模式都没匹配到，返回基本响应

            return cls(**data)
        except Exception as e:
            print(f"解析AI响应失败: {str(e)}\n响应内容: {response[:200]}...")
            return cls(summary="解析审查响应失败", comments=[])


class PipelineResult(BaseModel):
    """Pipeline 执行结果"""

    comments: List[Comment]
    summary: str


class ReviewPipeline(BaseModel):
    """代码审查流水线基类"""

    name: str
    description: str
    enabled: bool = True

    class Config:
        arbitrary_types_allowed = True

    def get_prompt_template(self, lang: str = "中文") -> Dict[str, str]:
        """获取不同语言的提示模板"""
        templates = {
            "中文": {
                "system_role": "你是一位专业的代码审查助手，专注于提供有建设性的代码改进建议。",
                "json_format": (
                    "请使用以下JSON格式返回审查结果,注意line_number是新文件的行号：\n"
                    "{\n"
                    '  "summary": "整体总结",\n'
                    '  "comments": [\n'
                    "    {\n"
                    '      "file_path": "文件路径",\n'
                    '      "line_number": 123,\n'
                    '      "content": "具体的评论内容",\n'
                    '      "type": "suggestion|issue|praise"\n'
                    "    }\n"
                    "  ]\n"
                    "}\n"
                ),
                "review_request": "请审查以下代码变更并提供反馈：",
                "file_review_request": "请审查此文件的实现逻辑：",
            },
            "english": {
                "system_role": "You are a professional code review assistant, focused on providing constructive code improvement suggestions.",
                "json_format": (
                    "Please provide your review in the following JSON format, note that the line_number refers to the line numbers in the new file.:\n"
                    "{\n"
                    '  "summary": "Overall summary",\n'
                    '  "comments": [\n'
                    "    {\n"
                    '      "file_path": "file path",\n'
                    '      "line_number": 123,\n'
                    '      "content": "specific comment",\n'
                    '      "type": "suggestion|issue|praise"\n'
                    "    }\n"
                    "  ]\n"
                    "}\n"
                ),
                "review_request": "Please review the following code changes and provide feedback:",
                "file_review_request": "Please review the implementation logic in this file:",
            },
        }
        return templates.get(lang, templates["english"])

    @staticmethod
    def _from_ai_comment(
        pipeline_name: str, ai_comment: AIReviewComment, mr_id: str
    ) -> Comment:
        """从 AI 评论创建 Comment 实体"""
        position = CommentPosition(
            file_path=ai_comment.file_path, new_line_number=ai_comment.line_number or 1
        )

        return Comment(
            comment_id=f"{pipeline_name.lower()}_{datetime.utcnow().timestamp()}",
            author=pipeline_name,
            content=ai_comment.content,
            created_at=datetime.utcnow(),
            comment_type=CommentType.FILE,
            mr_id=mr_id,
            position=position,
        )

    async def review(self, mr: MergeRequest) -> PipelineResult:
        """执行审查流程"""
        raise NotImplementedError()


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
        ai_client = AIClient()
        session_id = ai_client.generate_session_id()
        templates = self.get_prompt_template(settings.GPT_LANGUAGE)

        # 构建包含所有文件变更的提示
        files_content = []
        for file_diff in mr.file_diffs:
            files_content.append(
                f"File: {file_diff.file_name}\n" f"```\n{file_diff.diff_content}\n```"
            )

        all_diffs = "\n\n".join(files_content)

        system_prompt = Message("system", self._get_system_prompt())
        prompt = Message(
            "user",
            f"{templates['review_request']}\n"
            f"Pull Request Title: {mr.title}\n"
            f"Description: {mr.description}\n\n"
            f"Changes:\n{all_diffs}",
        )

        response = await ai_client.chat([system_prompt, prompt], session_id=session_id)
        try:
            ai_review = AIReviewResponse.parse_raw_response(response)
        except Exception:
            logger.exception(f"解析AI响应失败: {response[:200]}...")
            ai_review = AIReviewResponse(
                summary=f"解析AI响应失败, {response}...", comments=[]
            )
        # 创建评论
        comments = []
        for ai_comment in ai_review.comments:
            if ai_comment.type == "praise":
                continue
            comment = self._from_ai_comment(self.name, ai_comment, mr.mr_id)
            comments.append(comment)

        return PipelineResult(
            comments=comments, summary=ai_review.summary or "Code review completed."
        )
