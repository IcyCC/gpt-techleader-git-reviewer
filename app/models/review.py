from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class SeverityLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class CheckItem(BaseModel):
    message: str
    file_path: Optional[str]
    line_number: Optional[int]
    severity: SeverityLevel
    suggestion: Optional[str]


class ReviewResult(BaseModel):
    mr_id: str
    summary: str
    overall_status: str  # "approved", "changes_requested", "commented"
    review_date: datetime

    @classmethod
    def create_from_ai_response(
        cls, mr_id: str, summary: str, reviews: List[str]
    ) -> "ReviewResult":
        """从 AI 响应创建审查结果"""
        # TODO: 实现 AI 响应解析逻辑，提取具体问题和建议

        return cls(
            mr_id=mr_id,
            summary=summary,
            overall_status="commented",
            review_date=datetime.utcnow(),
        )
