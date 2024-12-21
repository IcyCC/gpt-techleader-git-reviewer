from datetime import datetime
from typing import Dict, List

from app.infra.git.github.client import GitHubClient
from app.models.comment import Comment, CommentType, Discussion


class DiscussionService:
    """讨论服务，负责管理代码审查相关的讨论"""

    def __init__(self):
        self.git_client = GitHubClient()

    def _build_reply_tree(
        self, comment: Comment, reply_map: Dict[str, List[Comment]]
    ) -> List[Comment]:
        """递归构建回复树"""
        replies = []
        direct_replies = reply_map.get(comment.comment_id, [])
        
        for reply in direct_replies:
            # 递归获取这条回复的所有子回复
            sub_replies = self._build_reply_tree(reply, reply_map)
            replies.append(reply)
            replies.extend(sub_replies)
        
        return replies

    async def build_discussions(
        self, owner: str, repo: str, mr_id: str
    ) -> List[Discussion]:
        """构建 MR 的所有讨论"""
        # 获取 MR 信息
        mr = await self.git_client.get_merge_request(owner, repo, mr_id)

        # 获取所有评论
        comments = await self.git_client.list_comments(owner, repo, mr)

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
            # 递归获取所有回复
            all_replies = self._build_reply_tree(root_comment, reply_map)
            # 按时间排序回复
            all_replies.sort(key=lambda x: x.created_at)
            discussion = Discussion.from_comments(root_comment, all_replies)
            discussions.append(discussion)

        # 按创建时间排序讨论
        discussions.sort(key=lambda x: x.created_at)

        return discussions

    async def resolve_discussion(
        self, owner: str, repo: str, mr_id: str, comment_id: str
    ):
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
