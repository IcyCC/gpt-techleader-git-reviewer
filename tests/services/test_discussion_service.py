import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.comment import Comment, CommentType
from app.models.git import MergeRequest, MergeRequestState
from app.services.discussion_service import DiscussionService


@pytest.fixture
def discussion_service():
    return DiscussionService()


@pytest.fixture
def mock_mr():
    return MergeRequest(
        mr_id="1",
        owner="test-owner",
        repo="test-repo",
        title="Test PR",
        author="test-user",
        state=MergeRequestState.OPEN,
        description="Test description",
        source_branch="feature",
        target_branch="main",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_comments():
    base_time = datetime.utcnow()
    
    # 创建根评论
    root_comment = Comment(
        comment_id="root1",
        author="reviewer",
        content="This needs improvement",
        created_at=base_time,
        comment_type=CommentType.FILE,
        mr_id="1",
    )

    # 创建第一��回复
    reply1 = Comment(
        comment_id="reply1",
        author="developer",
        content="I'll fix it",
        created_at=base_time + timedelta(minutes=5),
        comment_type=CommentType.REPLY,
        mr_id="1",
        reply_to="root1",
    )

    # 创建第二层回复
    reply1_1 = Comment(
        comment_id="reply1_1",
        author="reviewer",
        content="Thanks, also check...",
        created_at=base_time + timedelta(minutes=10),
        comment_type=CommentType.REPLY,
        mr_id="1",
        reply_to="reply1",
    )

    # 创建第三层回复
    reply1_1_1 = Comment(
        comment_id="reply1_1_1",
        author="developer",
        content="Done",
        created_at=base_time + timedelta(minutes=15),
        comment_type=CommentType.REPLY,
        mr_id="1",
        reply_to="reply1_1",
    )

    return [root_comment, reply1, reply1_1, reply1_1_1]


@pytest.mark.asyncio
async def test_build_reply_tree(discussion_service, sample_comments):
    """测试回复树构建"""
    # 构建回复映射
    reply_map = {}
    for comment in sample_comments:
        if comment.reply_to:
            if comment.reply_to not in reply_map:
                reply_map[comment.reply_to] = []
            reply_map[comment.reply_to].append(comment)

    # 测试回复树构建
    root_comment = sample_comments[0]
    replies = discussion_service._build_reply_tree(root_comment, reply_map)

    # 验证回复数量和顺序
    assert len(replies) == 3
    assert [r.comment_id for r in replies] == ["reply1", "reply1_1", "reply1_1_1"]
    assert all(isinstance(r, Comment) for r in replies)


@pytest.mark.asyncio
async def test_build_discussions(discussion_service, mock_mr, sample_comments):
    """测试讨论构建"""
    # Mock GitHub 客户端方法
    discussion_service.git_client.get_merge_request = AsyncMock(return_value=mock_mr)
    discussion_service.git_client.list_comments = AsyncMock(return_value=sample_comments)

    # 获取讨论列表
    discussions = await discussion_service.build_discussions(
        mock_mr.owner, mock_mr.repo, mock_mr.mr_id
    )

    # 验证讨论
    assert len(discussions) == 1  # 应该只有一个根评论，所以只有一个讨论
    discussion = discussions[0]
    
    # 验证讨论的根评论
    assert discussion.root_comment.comment_id == "root1"
    
    # 验证所有回复都被包含
    assert len(discussion.comments) == 4  # 1个根评论 + 3个回复
    
    # 验证评论顺序（应该按时间排序）
    comment_ids = [c.comment_id for c in discussion.comments]
    assert comment_ids == ["root1", "reply1", "reply1_1", "reply1_1_1"]



@pytest.mark.asyncio
async def test_empty_discussion(discussion_service, mock_mr):
    """测试空讨论的情况"""
    # Mock 返回空评论列表
    discussion_service.git_client.get_merge_request = AsyncMock(return_value=mock_mr)
    discussion_service.git_client.list_comments = AsyncMock(return_value=[])

    # 获取讨论列表
    discussions = await discussion_service.build_discussions(
        mock_mr.owner, mock_mr.repo, mock_mr.mr_id
    )

    # 验证结果
    assert len(discussions) == 0


@pytest.mark.asyncio
async def test_multiple_root_comments(discussion_service, mock_mr, sample_comments):
    """测试多个根评论的情况"""
    # 创建第二个根评论及其回复
    base_time = datetime.utcnow()
    root2 = Comment(
        comment_id="root2",
        author="reviewer",
        content="Another issue",
        created_at=base_time + timedelta(minutes=20),
        comment_type=CommentType.FILE,
        mr_id="1",
    )
    reply2 = Comment(
        comment_id="reply2",
        author="developer",
        content="Will fix",
        created_at=base_time + timedelta(minutes=25),
        comment_type=CommentType.REPLY,
        mr_id="1",
        reply_to="root2",
    )

    all_comments = sample_comments + [root2, reply2]

    # Mock 返回所有评论
    discussion_service.git_client.get_merge_request = AsyncMock(return_value=mock_mr)
    discussion_service.git_client.list_comments = AsyncMock(return_value=all_comments)

    # 获取讨论列表
    discussions = await discussion_service.build_discussions(
        mock_mr.owner, mock_mr.repo, mock_mr.mr_id
    )

    # 验证结果
    assert len(discussions) == 2  # 应该有两个讨论
    assert {d.root_comment.comment_id for d in discussions} == {"root1", "root2"}
    
    # 验证每个讨论的回复数量
    discussions_by_root = {d.root_comment.comment_id: d for d in discussions}
    assert len(discussions_by_root["root1"].comments) == 4  # 根评论 + 3个回复
    assert len(discussions_by_root["root2"].comments) == 2  # 根评论 + 1个回复 


@pytest.mark.asyncio
async def test_max_reply_depth(discussion_service, mock_mr):
    """测试最大回复深度限制"""
    base_time = datetime.utcnow()
    
    # 创建一个超过最大深度的回复链
    comments = []
    prev_comment = None
    
    # 创建根评论
    root = Comment(
        comment_id="root",
        author="reviewer",
        content="Root comment",
        created_at=base_time,
        comment_type=CommentType.FILE,
        mr_id="1",
    )
    comments.append(root)
    prev_comment = root
    
    # 创建15层回复（超过最大深度10）
    for i in range(15):
        reply = Comment(
            comment_id=f"reply_{i}",
            author="user",
            content=f"Reply level {i+1}",
            created_at=base_time + timedelta(minutes=i+1),
            comment_type=CommentType.REPLY,
            mr_id="1",
            reply_to=prev_comment.comment_id,
        )
        comments.append(reply)
        prev_comment = reply

    # Mock GitHub 客户端方法
    discussion_service.git_client.get_merge_request = AsyncMock(return_value=mock_mr)
    discussion_service.git_client.list_comments = AsyncMock(return_value=comments)

    # 获取讨论列表
    discussions = await discussion_service.build_discussions(
        mock_mr.owner, mock_mr.repo, mock_mr.mr_id
    )

    # 验证结果
    assert len(discussions) == 1
    discussion = discussions[0]
    
    # 验证评论数量（应该是最大深度+1，因为包含根评论）
    assert len(discussion.comments) == discussion_service.MAX_REPLY_DEPTH + 1
    
    # 验证最后一条评论的ID应该是 reply_9（第10层回复）
    last_comment = discussion.comments[-1]
    assert last_comment.comment_id == f"reply_{discussion_service.MAX_REPLY_DEPTH-1}"


@pytest.mark.asyncio
async def test_mixed_depth_replies(discussion_service, mock_mr):
    """测试混合深度的回复"""
    base_time = datetime.utcnow()
    
    # 创建根评论
    root = Comment(
        comment_id="root",
        author="reviewer",
        content="Root comment",
        created_at=base_time,
        comment_type=CommentType.FILE,
        mr_id="1",
    )
    
    # 创建第一层回复
    reply1 = Comment(
        comment_id="reply1",
        author="user1",
        content="First level reply",
        created_at=base_time + timedelta(minutes=1),
        comment_type=CommentType.REPLY,
        mr_id="1",
        reply_to="root",
    )
    
    # 创建第二层回复
    reply2 = Comment(
        comment_id="reply2",
        author="user2",
        content="Second level reply",
        created_at=base_time + timedelta(minutes=2),
        comment_type=CommentType.REPLY,
        mr_id="1",
        reply_to="reply1",
    )
    
    # 创建一个新的回复链（12层，超过限制）
    deep_replies = []
    prev_comment = root
    for i in range(12):
        reply = Comment(
            comment_id=f"deep_reply_{i}",
            author="user",
            content=f"Deep reply level {i+1}",
            created_at=base_time + timedelta(minutes=i+10),
            comment_type=CommentType.REPLY,
            mr_id="1",
            reply_to=prev_comment.comment_id,
        )
        deep_replies.append(reply)
        prev_comment = reply

    # 合并所有评论
    all_comments = [root, reply1, reply2] + deep_replies

    # Mock GitHub 客户端方法
    discussion_service.git_client.get_merge_request = AsyncMock(return_value=mock_mr)
    discussion_service.git_client.list_comments = AsyncMock(return_value=all_comments)

    # 获取讨论列表
    discussions = await discussion_service.build_discussions(
        mock_mr.owner, mock_mr.repo, mock_mr.mr_id
    )

    # 验证结果
    assert len(discussions) == 1
    discussion = discussions[0]
    
    # 验证评论总数不超过最大深度限制
    total_comments = len(discussion.comments)
    assert total_comments <= discussion_service.MAX_REPLY_DEPTH + 1
    
    # 验证第一个回复链完整保留
    assert "reply1" in [c.comment_id for c in discussion.comments]
    assert "reply2" in [c.comment_id for c in discussion.comments]