from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel


class ChangeType(str, Enum):
    ADD = "add"
    DELETE = "delete"
    MODIFY = "modify"


class FileDiff(BaseModel):
    new_file_path: str
    change_type: ChangeType
    diff_content: str
    old_file_path: Optional[str] = None
    line_changes: Dict[int, str] = {}  # 行号到变更内容的映射



class MergeRequestState(str, Enum):
    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"
    REVIEWING = "reviewing"


class MergeRequest(BaseModel):
    mr_id: str
    owner: str
    repo: str
    title: str
    author: str
    state: MergeRequestState
    description: str
    source_branch: str
    target_branch: str
    created_at: datetime
    updated_at: datetime
    file_diffs: List[FileDiff] = []
    labels: List[str] = []
    reviewers: List[str] = []
    comments_count: int = 0
    project_id: Optional[int] = None
