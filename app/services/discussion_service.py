from typing import List, Dict
from datetime import datetime
from app.models.comment import Discussion, Comment, CommentType
from app.infra.git.github.client import GitHubClient

class DiscussionService:
    """讨论服务，负责管理代码审查相关的讨论"""
    
    def __init__(self):
        self.git_client = GitHubClient()

    async def build_discussions(self, owner: str, repo: str, mr_id: str) -> List[Discussion]:
        """构建 MR 的所有讨论"""
        # 获取 MR 信息
        mr = await self.git_client.get_merge_request(owner, repo, mr_id)
        
        # 获取所有评论
        comments = await self.git_client.list_comments(owner, repo, mr)
        
        # 构建评论树
        comment_map: Dict[str, Comment] = {c.comment_id: c for c in comments}
        root_comments: List[Comment] = []
        reply_map: Dict[str, List[Comment]] = {}
        
        # 分类评论
        for comment in comments:
            if comment.reply_to:
                # 这是一个回复
                if comment.reply_to not in reply_map:
                    reply_map[comment.reply_to] = []
                reply_map[comment.reply_to].append(comment)
            else:
                # 这是一个根评论
                root_comments.append(comment)
        
        # 构建讨论列表
        discussions = []
        for root_comment in root_comments:
            replies = reply_map.get(root_comment.comment_id, [])
            # 按时间排序回复
            replies.sort(key=lambda x: x.created_at)
            discussion = Discussion.from_comments(root_comment, replies)
            discussions.append(discussion)
        
        # 按创建时间排序讨论
        discussions.sort(key=lambda x: x.created_at)
        
        return discussions

    async def resolve_discussion(self, owner: str, repo: str, mr_id: str, comment_id: str):
        """将讨论标记为已解决
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            mr_id: PR ID
            comment_id: 要解决的评论 ID
        """
        # 获取 MR 信息
        mr = await self.git_client.get_merge_request(owner, repo, mr_id)
        
        # 调用 GitHub API 解决讨论
        await self.git_client.resolve_review_thread(owner, repo, mr.mr_id, comment_id)