from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from app.models.git import MergeRequest
from app.models.review import ReviewResult
from app.services.reviewer_service import ReviewerService
from app.infra.git.github.webhook_handler import GitHubWebhookHandler
from app.models.const import BOT_PREFIX
from typing import Dict, Any, Union
import asyncio

router = APIRouter()
github_handler = GitHubWebhookHandler()

@router.get("/api/v1/webhook/github")
async def verify_webhook():
    return {"status": "Webhook verified", "message": "GET request received"}

async def process_pr(owner: str, repo: str, mr_id: str, reviewer_service: ReviewerService):
    """异步处理 PR"""
    try:
        await reviewer_service.review_mr(owner, repo, mr_id)
    except Exception as e:
        print(f"Error processing PR: {e}")

async def process_comment(owner: str, repo: str, mr_id: str, comment_id: str, reviewer_service: ReviewerService):
    """异步处理评论"""
    try:
        await reviewer_service.handle_comment(owner=owner, repo=repo, mr_id=mr_id, comment_id=comment_id)
    except Exception as e:
        print(f"Error processing comment: {e}")

@router.post("/github", response_model=Union[ReviewResult, Dict[str, Any]])
async def handle_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    reviewer_service: ReviewerService = Depends()
):
    """处理来自 GitHub 的 webhook
    
    支持以下事件：
    1. ping: webhook 配置验证
    2. PR 创建或更新时，触发代码审查
    3. PR 评论时，如果不是机器人的评论则触发回复
    """
    try:
        # 验证并解析 webhook
        event_type, event_info = await github_handler.handle_webhook(request)
        print(f"Received {event_type} event:", event_info)
        
        if not event_info:
            return {"message": "Event ignored"}
            
        # 处理 ping 事件
        if event_type == "ping":
            return {
                "message": "Webhook configured successfully",
                "event": "ping",
                "data": event_info
            }
            
        # 处理 PR 事件
        if event_type == "pull_request":
            owner, repo, mr_id = event_info
            # 异步处理 PRa
            background_tasks.add_task(process_pr, owner, repo, mr_id, reviewer_service)
            return {"message": f"PR review task for {owner}/{repo}#{mr_id} scheduled"}
        # 处理评论事件
        elif event_type == "pull_request_review_comment":
            owner, repo, mr_id, comment_id, _ = event_info
            # 异步处理评论
            background_tasks.add_task(process_comment, owner, repo, mr_id, comment_id, reviewer_service)
            return {"message": f"Comment processing task for {owner}/{repo}#{mr_id} scheduled"}
        else:
            return {"message": f"Event {event_type} ignored"}
            
        return {"message": f"Event {event_type} processed"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 