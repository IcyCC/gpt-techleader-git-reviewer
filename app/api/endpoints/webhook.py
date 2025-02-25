import asyncio
import re
from typing import Any, Dict, Union
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from app.infra.git.base_webhook_handler import WebHookEvent, WebHookEventType
from app.infra.git.github.webhook_handler import GitHubWebhookHandler
from app.infra.git.gitlab.webhook_handler import GitLabWebhookHandler
from app.models.const import BOT_PREFIX
from app.models.git import MergeRequest
from app.models.review import ReviewResult
from app.services.reviewer_service import ReviewerService
from app.infra.config.settings import get_settings
logger = logging.getLogger(__name__)


router = APIRouter()
settings = get_settings()
github_handler = GitHubWebhookHandler()
gitlab_handler = GitLabWebhookHandler()


@router.get("/webhook/github")
async def verify_webhook():
    return {"status": "Webhook verified", "message": "GET request received"}


async def process_pr(
    owner: str, repo: str, mr_id: str, reviewer_service: ReviewerService
):
    """异步处理 PR"""
    try:
        await reviewer_service.review_mr(owner, repo, mr_id)
    except Exception as e:
        print(f"Error processing PR: {e}")

async def process_comment_with_instruction(
    owner: str,
    repo: str,
    mr_id: str,
    reviewer_service: ReviewerService,
    comment_body: str,
):
    """异步处理带有指令的评论"""
    match = re.search(r'#ai:\s*(\w+)', comment_body)
    if match:
        instruction = match.group(1)
        if instruction == "review":
            await reviewer_service.review_mr(
                owner=owner, repo=repo, mr_id=mr_id, check_limit=False
            )
        else:
            logger.warning(f"Unknown instruction: {instruction}")
    else:
        logger.warning("No instruction found")

async def process_comment(
    owner: str,
    repo: str,
    mr_id: str,
    comment_id: str,
    reviewer_service: ReviewerService,
):
    """异步处理评论"""
    try:
        await reviewer_service.handle_comment(
            owner=owner, repo=repo, mr_id=mr_id, comment_id=comment_id
        )
    except Exception as e:
        print(f"Error processing comment: {e}")


@router.post("/webhook/{service}", response_model=Union[ReviewResult, Dict[str, Any]])
async def handle_git_webhook(
    service: str,
    request: Request,
    background_tasks: BackgroundTasks,
    reviewer_service: ReviewerService = Depends(),
):
    """Handle webhooks from Git services
    
    Supports:
    1. ping: webhook configuration verification
    2. MR/PR creation triggers code review
    3. MR/PR comments trigger replies if not from bot
    """
    try:
        # Select appropriate handler
        if service.lower() == "github":
            handler = github_handler
        elif service.lower() == "gitlab":
            handler = gitlab_handler
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported git service: {service}")

        # Verify and parse webhook
        event_info = await handler.handle_webhook(request)
        print(f"Received  event:", event_info)

        if not event_info:
            return {"message": "Event ignored"}

        # Handle ping event
        if event_info.event_type == WebHookEventType.PING:
            return {
                "message": "Webhook configured successfully",
                "event": "ping",
                "data": {},
            }

        # Handle MR/PR event
        if event_info.event_type == WebHookEventType.MERGE_REQUEST:
            event_data = event_info.event_data
            background_tasks.add_task(process_pr, event_data.owner, event_data.repo, event_data.mr_id, reviewer_service)
            return {"message": f"MR review task for {event_data.owner}/{event_data.repo}#{event_data.mr_id} scheduled"}

        # Handle comment event
        elif event_info.event_type == WebHookEventType.MERGE_REQUEST_COMMENT:
            event_data = event_info.event_data
            if '#ai:' in event_data.comment_body:
                background_tasks.add_task(
                    process_comment_with_instruction, event_data.owner, event_data.repo, event_data.mr_id, reviewer_service, event_data.comment_body
                )
            else:
                background_tasks.add_task(
                    process_comment, event_data.owner, event_data.repo, event_data.mr_id, event_data.comment_id, reviewer_service
                )
            return {
                "message": f"Comment processing task for {event_data.owner}/{event_data.repo}#{event_data.mr_id} scheduled"
            }
        else:
            return {"message": f"Event {event_info.event_type} ignored"}

    except Exception as e:
        logger.exception(f"Error handling webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
