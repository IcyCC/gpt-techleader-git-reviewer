from datetime import datetime
from typing import Dict, List

from app.infra.git.factory import GitClientFactory
from app.models.comment import Comment, CommentType, Discussion


class DiscussionService:
    """讨论服务，负责管理代码审查相关的讨论"""

    MAX_REPLY_DEPTH = 10  # 最大回复深度限制

    def __init__(self):
        self.git_client = GitClientFactory.get_client()

    def _build_reply_tree(
        self, comment: Comment, reply_map: Dict[str, List[Comment]], current_depth: int = 0
    ) -> List[Comment]:
        """递归构建回复树
        
        Args:
            comment: 当前评论
            reply_map: 回复映射表
            current_depth: 当前递归深度
        
        Returns:
            List[Comment]: 所有回复的列表
        """
        # 如果当前深度已经达到最大深度，返回空列表
        if current_depth >= self.MAX_REPLY_DEPTH:
            return []

        replies = []
        direct_replies = reply_map.get(comment.comment_id, [])
        
        for reply in direct_replies:
            # 如果添加这条回复会超过最大深度限制，则跳过
            if len(replies) >= self.MAX_REPLY_DEPTH - current_depth:
                break
                
            replies.append(reply)
            # 递归获取这条回复的子回复（深度+1）
            if current_depth + 1 < self.MAX_REPLY_DEPTH:
                sub_replies = self._build_reply_tree(reply, reply_map, current_depth + 1)
                # 确保不超过最大深度限制
                remaining_slots = self.MAX_REPLY_DEPTH - current_depth - len(replies)
                replies.extend(sub_replies[:remaining_slots])
        
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
            # 递归获取所有回复（从深度0开始）
            all_replies = self._build_reply_tree(root_comment, reply_map, 0)
            # 按时间排序回复
            all_replies.sort(key=lambda x: x.created_at)
            discussion = Discussion.from_comments(root_comment, all_replies)
            discussions.append(discussion)

        # 按创建时间排序讨论
        discussions.sort(key=lambda x: x.created_at)

        return discussions
