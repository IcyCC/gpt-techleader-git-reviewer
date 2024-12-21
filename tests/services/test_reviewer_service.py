import asyncio
from datetime import datetime

import pytest

from app.models.comment import Comment, CommentType
from app.models.git import MergeRequest, MergeRequestState
from app.models.review import ReviewResult
from app.services.reviewer_service import ReviewerService


@pytest.fixture
def reviewer_service():
    return ReviewerService()


@pytest.fixture
def test_mr():
    return MergeRequest(
        mr_id="1",
        owner="IcyCC",
        repo="gpt-techleader-git-reviewer",
        title="Test PR",
        author="test-user",
        state=MergeRequestState.OPEN,
        description="Test description",
        source_branch="feature",
        target_branch="main",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_handle_comment_normal_reply(reviewer_service, test_mr):
    """测试普通评论回复"""
    try:

        # 处理评论
        reply = await reviewer_service.handle_comment(
            test_mr.owner, test_mr.repo, test_mr.mr_id, 1885553259
        )

        return True
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return False


# @pytest.mark.asyncio
# async def test_review_mr(reviewer_service):
#     """测试 MR 审查功能"""
#     # 测试数据
#     owner = "IcyCC"
#     repo = "gpt-techleader-git-reviewer"
#     mr_id = "1"
#     try:
#         result = await reviewer_service.review_mr(owner, repo, mr_id)

#         # 验证结果
#         assert isinstance(result, ReviewResult)
#         assert result.mr_id == mr_id
#         assert result.summary != ""

#         print("\nReview Result:")
#         print(f"Summary: {result.summary}")

#         return True
#     except Exception as e:
#         print(f"Test failed: {str(e)}")
#         return False
