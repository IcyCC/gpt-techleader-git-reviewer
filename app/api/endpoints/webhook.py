import asyncio
from typing import Any, Dict, Union

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from app.infra.git.github.webhook_handler import GitHubWebhookHandler
from app.infra.git.gitlab.webhook_handler import GitLabWebhookHandler
from app.models.const import BOT_PREFIX
from app.models.git import MergeRequest
from app.models.review import ReviewResult
from app.services.reviewer_service import ReviewerService
from app.infra.config.settings import get_settings

router = APIRouter()
settings = get_settings()
github_handler = GitHubWebhookHandler()
gitlab_handler = GitLabWebhookHandler()


@router.get("/api/v1/webhook/github")
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
        event_type, event_info = await handler.handle_webhook(request)
        print(f"Received {event_type} event:", event_info)

        if not event_info:
            return {"message": "Event ignored"}

        # Handle ping event
        if event_type == "ping":
            return {
                "message": "Webhook configured successfully",
                "event": "ping",
                "data": event_info,
            }

        # Handle MR/PR event
        if event_type in ["pull_request", "merge_request"]:
            owner, repo, mr_id = event_info
            background_tasks.add_task(process_pr, owner, repo, mr_id, reviewer_service)
            return {"message": f"MR review task for {owner}/{repo}#{mr_id} scheduled"}

        # Handle comment event
        elif event_type in ["pull_request_review_comment", "merge_request_comment"]:
            owner, repo, mr_id, comment_id, _ = event_info
            background_tasks.add_task(
                process_comment, owner, repo, mr_id, comment_id, reviewer_service
            )
            return {
                "message": f"Comment processing task for {owner}/{repo}#{mr_id} scheduled"
            }
        else:
            return {"message": f"Event {event_type} ignored"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
