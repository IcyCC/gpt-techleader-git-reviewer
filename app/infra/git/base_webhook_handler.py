from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple
from fastapi import Request

class BaseWebhookHandler(ABC):
    """Base webhook handler for Git services"""
    
    @abstractmethod
    async def handle_webhook(self, request: Request) -> Tuple[str, Optional[Any]]:
        """Handle webhook request
        
        Returns:
            Tuple[str, Optional[Any]]: (event_type, event_data)
            Event types:
            - "ping": Initial webhook setup test event
            - "merge_request": MR/PR related events (only handles first open)
            - "merge_request_comment": MR/PR comment events (only handles replies)
        """
        pass 