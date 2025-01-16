import logging
from typing import Any, Optional, Tuple

from fastapi import HTTPException, Request

from app.infra.config.settings import get_settings
from app.infra.git.base_webhook_handler import BaseWebhookHandler
from app.models.const import BOT_PREFIX
from .client import GitLabClient

logger = logging.getLogger(__name__)
settings = get_settings()

class GitLabWebhookHandler(BaseWebhookHandler):
    """GitLab Webhook Handler"""

    def __init__(self):
        self.client = GitLabClient()

    async def handle_webhook(self, request: Request) -> Tuple[str, Optional[Any]]:
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

        owner = project.get("namespace")
        repo = project.get("name")
        logger.info(f"Received webhook event: {event_type}, {owner}/{repo}")

        if not owner or not repo:
            logger.error("Cannot get repository information")
            raise HTTPException(status_code=400, detail="Missing repository information")

        # Check if repository is allowed
        if not settings.is_repo_allowed(owner, repo):
            logger.warning(f"Repository not in allowlist: {owner}/{repo}")
            return event_type, None

        # Handle different event types
        if event_type == "System Hook":
            if payload.get("event_type") == "project_create":
                logger.info(f"Handling ping event: {owner}/{repo}")
                return "ping", {
                    "project_id": project.get("id"),
                    "repository": {"owner": owner, "name": repo},
                }

        elif event_type == "Merge Request Hook":
            action = payload.get("object_attributes", {}).get("action")
            if action != "open":
                logger.info(f"Ignoring MR event: {action}")
                return event_type, None

            mr_id = str(payload["object_attributes"]["iid"])
            logger.info(f"Handling MR open event: {owner}/{repo}!{mr_id}")
            return "merge_request", (owner, repo, mr_id)

        elif event_type == "Note Hook":
            if payload.get("object_attributes", {}).get("noteable_type") != "MergeRequest":
                return event_type, None

            # Only handle comment replies
            note_type = payload.get("object_attributes", {}).get("type")
            if note_type != "DiscussionNote":
                logger.info("Ignoring non-reply comment")
                return event_type, None

            mr_id = str(payload["merge_request"]["iid"])
            comment_id = str(payload["object_attributes"]["id"])
            comment_body = payload["object_attributes"]["note"]

            # Ignore bot comments
            if BOT_PREFIX in comment_body:
                logger.info("Ignoring bot comment")
                return event_type, None

            logger.info(f"Handling comment reply event: {owner}/{repo}!{mr_id} - {comment_id}")
            return "merge_request_comment", (owner, repo, mr_id, comment_id, comment_body)

        logger.info(f"Ignoring unknown event type: {event_type}")
        return event_type, None 