from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from fastapi import Request

from app.models.comment import Comment
from app.models.git import MergeRequest


class GitClientBase(ABC):
    """Git 客户端基础接口类"""

    @abstractmethod
    async def get_merge_request(
        self, owner: str, repo: str, mr_id: str
    ) -> MergeRequest:
        """获取合并请求信息"""
        pass


    @abstractmethod
    async def create_comment(self, owner: str, repo: str, comment: Comment):
        """创建评论"""
        pass

    @abstractmethod
    async def get_comment(
        self, owner: str, repo: str, mr: MergeRequest, comment_id: str
    ) -> Comment:
        """获取评论详情"""
        pass

    @abstractmethod
    async def verify_webhook(self, request: Request) -> bool:
        """验证 webhook 请求的合法性"""
        pass
