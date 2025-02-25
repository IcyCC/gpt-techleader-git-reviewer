import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel

from app.models.comment import Comment, CommentPosition, CommentType
from app.models.git import MergeRequest

logger = logging.getLogger(__name__)


class AIReviewComment(BaseModel):
    """AI 返回的评论结构"""

    new_file_path: str
    old_file_path: Optional[str] = None
    new_line_number: Optional[int] = 1
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
            json_str = extract_json(response.strip())

            assert json_str is not None, "无法解析JSON"
            data = json.loads(json_str)
            return cls(**data)
        except Exception as e:
            logger.exception(f"解析AI响应失败: {response[:200]}...")
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
                "system_role": "你是代码审查助手。提供简短精确的建议。只关注需要修改的关键问题。",
                "json_format": (
                    "使用以下JSON格式返回结果:\n"
                    "{\n"
                    '  "summary": "简短总结",\n'
                    '  "comments": [\n'
                    "    {\n"
                    '      "old_file_path": "文件路径",\n'
                    '      "new_file_path": "文件路径",\n'
                    '      "new_line_number": 行号,\n'
                    '      "content": "评论内容",\n'
                    '      "type": "suggestion|issue|praise"\n'
                    "    }\n"
                    "  ]\n"
                    "}\n"
                ),
                "review_request": "审查代码变更：",
                "file_review_request": "审查此文件：",
            },
            "english": {
                "system_role": "You are a code review assistant. Provide brief, precise suggestions. Focus only on the critical issues that need to be clearly modified.",
                "json_format": (
                    "Use this JSON format:\n"
                    "{\n"
                    '  "summary": "brief summary",\n'
                    '  "comments": [\n'
                    "    {\n"
                    '      "old_file_path": "file path",\n'
                    '      "new_file_path": "file path",\n'
                    '      "new_line_number": line number,\n'
                    '      "content": "comment",\n'
                    '      "type": "suggestion|issue|praise"\n'
                    "    }\n"
                    "  ]\n"
                    "}\n"
                ),
                "review_request": "Review changes:",
                "file_review_request": "Review file:",
            },
        }
        return templates.get(lang, templates["english"])

    @staticmethod
    def _from_ai_comment(
        pipeline_name: str, ai_comment: AIReviewComment, mr_id: str
    ) -> Comment:
        """从 AI 评论创建 Comment 实体"""
        position = CommentPosition(
            new_file_path=ai_comment.new_file_path,
            old_file_path=ai_comment.old_file_path,
            new_line_number=ai_comment.new_line_number or 1,
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
