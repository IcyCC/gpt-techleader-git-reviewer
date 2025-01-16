from enum import Enum
from typing import Optional

from app.infra.config.settings import get_settings
from app.infra.git.base import GitClientBase
from app.infra.git.github.client import GitHubClient
from app.infra.git.gitlab.client import GitLabClient

settings = get_settings()

class GitServiceType(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"

class GitClientFactory:
    """Git 客户端工厂类"""
    
    _instance: Optional[GitClientBase] = None
    
    @classmethod
    def create_client(cls) -> GitClientBase:
        """创建 Git 客户端实例"""
        if cls._instance is None:
            service_type = GitServiceType(settings.GIT_SERVICE.lower())
            
            if service_type == GitServiceType.GITHUB:
                cls._instance = GitHubClient()
            elif service_type == GitServiceType.GITLAB:
                cls._instance = GitLabClient()
            else:
                raise ValueError(f"Unsupported Git service type: {settings.GIT_SERVICE}")
                
        return cls._instance

    @classmethod
    def get_client(cls) -> GitClientBase:
        """获取 Git 客户端实例（单例模式）"""
        return cls.create_client() 