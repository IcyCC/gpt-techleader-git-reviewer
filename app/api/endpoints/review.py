from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List
from app.models.review import ReviewResult
from app.models.comment import Comment, Discussion
from app.services.reviewer_service import ReviewerService
from app.services.discussion_service import DiscussionService
from pydantic import BaseModel

router = APIRouter()

@router.post("/pulls/{owner}/{repo}/{mr_id}/review", response_model=ReviewResult)
async def create_review(
    owner: str,
    repo: str,
    mr_id: str,
    reviewer_service: ReviewerService = Depends()
):
    """
    对指定的 PR 进行代码审查
    """
    try:
        result = await reviewer_service.review_mr(owner, repo, mr_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pulls/{owner}/{repo}/{mr_id}/comments/{comment_id}/reply", response_model=Comment)
async def reply_to_comment(
    owner: str,
    repo: str,
    mr_id: str,
    comment_id: str,
    reviewer_service: ReviewerService = Depends()
):
    """
    回复 PR 中的评论
    """
    try:
        response = await reviewer_service.handle_comment(
            owner,
            repo,
            mr_id,
            comment_id
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pulls/{owner}/{repo}/{mr_id}/discussions", response_model=List[Discussion])
async def list_discussions(
    owner: str,
    repo: str,
    mr_id: str,
    discussion_service: DiscussionService = Depends()
):
    """
    获取 PR 的所有讨论
    """
    try:
        discussions = await discussion_service.build_discussions(owner, repo, mr_id)
        return discussions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 