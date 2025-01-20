from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel


class CommentType(str, Enum):
    GENERAL = "general"  # 普通评论
    FILE = "file"  # 文件级别评论
    REPLY = "reply"  # 回复评论


class CommentPosition(BaseModel):
    new_file_path: str
    old_file_path: Optional[str] = None
    new_line_number: int
    old_line_number: Optional[int] = None
    diff_range: Optional[str] = None


class Comment(BaseModel):
    comment_id: str
    author: str
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    comment_type: CommentType
    reply_to: Optional[str] = None
    mr_id: str
    position: Optional[CommentPosition] = None
    parent_comment_id: Optional[str] = None
    reactions: Dict[str, int] = {} 


class Discussion(BaseModel):
    """讨论主题"""

    discussion_id: str
    mr_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    status: str = "active"  # active, resolved
    comments: List[Comment] = []  # 评论列表
    root_comment: Comment  # 讨论的根评论
    resolved: bool = False

    @classmethod
    def from_comments(
        cls, root_comment: Comment, replies: List[Comment]
    ) -> "Discussion":
        """从根评论和回复列表创建讨论"""
        all_comments = [root_comment] + replies

        # 检查是否有包含 [RESOLVED] 标记的回复
        resolved = any("[RESOLVED]" in comment.content for comment in replies)

        return cls(
            discussion_id=f"discussion_{root_comment.comment_id}",
            mr_id=root_comment.mr_id,
            title=(
                root_comment.content[:50] + "..."
                if len(root_comment.content) > 50
                else root_comment.content
            ),
            created_at=root_comment.created_at,
            updated_at=max(c.created_at for c in all_comments),
            comments=all_comments,
            root_comment=root_comment,
            status="resolved" if resolved else "active",
            resolved=resolved,
        )
