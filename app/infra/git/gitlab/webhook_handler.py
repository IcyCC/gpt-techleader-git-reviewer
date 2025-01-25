import logging
from typing import Any, Optional, Tuple

from fastapi import HTTPException, Request

from app.infra.config.settings import get_settings
from app.models.const import BOT_PREFIX
from .client import GitLabClient
from app.infra.git.base_webhook_handler import BaseWebhookHandler, MergeRequestEvent, MergeRequestCommentEvent, WebHookEvent, WebHookEventType

logger = logging.getLogger(__name__)
settings = get_settings()

class GitLabWebhookHandler(BaseWebhookHandler):
    """GitLab Webhook Handler"""

    def __init__(self):
        self.client = GitLabClient()

    async def handle_webhook(self, request: Request) -> Optional[WebHookEvent]:
        """Handle GitLab webhook request"""
        # Verify webhook token
        token = request.headers.get("X-Gitlab-Token")
        if not token or token != settings.GITLAB_WEBHOOK_SECRET:
            raise HTTPException(status_code=401, detail="Invalid webhook token")

        # Get event type
        event_type = request.headers.get("X-Gitlab-Event")
        if not event_type:
            raise HTTPException(status_code=400, detail="Missing event type")

        # Get request data
        payload = await request.json()

        # Get repository info
        project = payload.get("project", {})
        if not project:
            raise HTTPException(status_code=400, detail="Missing project information")

        owner, repo = project["path_with_namespace"].split("/")
        logger.info(f"Received webhook event: {event_type}, {owner}/{repo}")

        if not owner or not repo:
            logger.error("Cannot get repository information")
            raise HTTPException(status_code=400, detail="Missing repository information")

        # Check if repository is allowed
        if not settings.is_repo_allowed(owner, repo):
            logger.warning(f"Repository not in allowlist: {owner}/{repo}")
            raise HTTPException(status_code=400, detail="Repository not in allowlist")

        # Handle different event types
        if event_type == "System Hook":
            if payload.get("event_type") == "project_create":
                logger.info(f"Handling ping event: {owner}/{repo}")
                return WebHookEvent(event_type=WebHookEventType.PING, event_data={})

        elif event_type == "Merge Request Hook":
            mr_state = payload.get("object_attributes", {}).get("state")
            mr_draft = payload.get("object_attributes", {}).get("draft")
            if mr_state == 'opened' and not mr_draft:
                mr_id = str(payload["object_attributes"]["iid"])
                logger.info(f"Handling MR open event: {owner}/{repo}!{mr_id}")
                return WebHookEvent(event_type=WebHookEventType.MERGE_REQUEST, event_data=MergeRequestEvent(owner=owner, repo=repo, mr_id=mr_id))
            return None

        elif event_type == "Note Hook":
            if payload.get("object_attributes", {}).get("noteable_type") != "MergeRequest":
                return None

            # Only handle comment replies
            note_type = payload.get("object_attributes", {}).get("type")
            if note_type != "DiscussionNote":
                logger.info("Ignoring non-reply comment")
                return None

            mr_id = str(payload["merge_request"]["iid"])
            comment_id = str(payload["object_attributes"]["id"])
            comment_body = payload["object_attributes"]["note"]

            # Ignore bot comments
            if BOT_PREFIX in comment_body:
                logger.info("Ignoring bot comment")
                return None

            logger.info(f"Handling comment reply event: {owner}/{repo}!{mr_id} - {comment_id}")
            return None
            return WebHookEvent(event_type=WebHookEventType.MERGE_REQUEST_COMMENT, event_data=MergeRequestCommentEvent(owner=owner, repo=repo, mr_id=mr_id, comment_id=comment_id, comment_body=comment_body))

        logger.info(f"Ignoring unknown event type: {event_type}")
        return None