from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from app.models.git import MergeRequest
from app.models.comment import Comment
from fastapi import Request

class GitClientBase(ABC):
    """Git 客户端基础接口类"""
    
    @abstractmethod
    async def get_merge_request(self, owner: str, repo: str, mr_id: str) -> MergeRequest:
        """获取合并请求信息"""
        pass

    @abstractmethod
    async def get_file_content(self, owner: str, repo: str, mr: MergeRequest, file_path: str) -> Optional[str]:
        """获取指定文件的内容"""
        pass

    @abstractmethod
    async def create_comment(self, owner: str, repo: str, comment: Comment):
        """创建评论"""
        pass

    @abstractmethod
    async def get_comment(self, owner: str, repo: str, mr: MergeRequest, comment_id: str) -> Comment:
        """获取评论详情"""
        pass

    @abstractmethod
    async def verify_webhook(self, request: Request) -> bool:
        """验证 webhook 请求的合法性"""
        pass

    @abstractmethod
    async def parse_webhook_event(self, request: Request) -> Optional[Tuple[str, str, str]]:
        """解析 webhook 事件，返回 (owner, repo, pr_number)"""
        pass 