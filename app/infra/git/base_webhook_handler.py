from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple, NamedTuple
from fastapi import Request
from pydantic import BaseModel
from enum import Enum

class MergeRequestEvent(NamedTuple):
    owner: str
    repo: str
    mr_id: str

class MergeRequestCommentEvent(NamedTuple):
    owner: str
    repo: str
    mr_id: str
    comment_id: str
    comment_body: str

class WebHookEventType(Enum):
    PING = "ping"
    MERGE_REQUEST = "merge_request"
    MERGE_REQUEST_COMMENT = "merge_request_comment"

class WebHookEvent(BaseModel):
    event_type: WebHookEventType
    event_data: Any

class BaseWebhookHandler(ABC):
    """Base webhook handler for Git services"""
    
    @abstractmethod
    async def handle_webhook(self, request: Request) -> Optional[WebHookEvent]:
        """Handle webhook request
        
        Returns:
            Tuple[str, Optional[Any]]: (event_type, event_data)
            Event types:
            - "ping": Initial webhook setup test event
            - "merge_request": MR/PR related events (only handles first open)
            - "merge_request_comment": MR/PR comment events (only handles replies)
        """
        pass 