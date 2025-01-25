import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Code Reviewer"
    API_V1_STR: str = "/api/v1"
    
    # Git 服务类型配置
    GIT_SERVICE: str = "gitlab"  # 'github' or 'gitlab'

    # GitHub配置 (当 GIT_SERVICE == 'github' 时使用)
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_WEBHOOK_SECRET: Optional[str] = None
    GITHUB_API_URL: str = "https://api.github.com"
    GITHUB_REPOS: str = ""  # 格式：owner1/repo1,owner2/repo2
    
    # GitLab配置 (当 GIT_SERVICE == 'gitlab' 时使用)
    GITLAB_API_URL: str = "https://gitlab.com/api/v4"
    GITLAB_TOKEN: Optional[str] = None
    GITLAB_WEBHOOK_SECRET: Optional[str] = None
    GITLAB_REPOS: str = ""  # 格式：owner1/repo1,owner2/repo2


    # AI 审查限制
    MAX_FILES_PER_MR: int = 20  # MR 最大文件数
    MAX_LINES_PER_FILE: int = 1000  # 单个文件最大行数
    MAX_BYTES_PER_FILE: int = 1024 * 102  # 单个文件最大字节数

    # 系统限制
    MAX_AI_REQUESTS_PER_HOUR: int = 30  # 每小时最大 AI 请求次数
    MAX_COMMENT_REPLIES: int = 2  # 每个评论最大回复次数
    MAX_MR_REVIEWS_PER_HOUR: int = 5  # 每小时最大处理 MR 数
    RATE_LIMIT_EXPIRE: int = 3600  # 限制过期时间（秒）
    MAX_MR_REVIEWS: int = 3  # 每个 MR 最多允许被检查的次数

    # GPT配置
    GPT_API_KEY: str
    GPT_API_URL: str = "https://vip.apiyi.com/v1"
    GPT_MODEL: str = "claude-3-opus-20240229"
    GPT_TEMPERATURE: float = 0.7
    GPT_LANGUAGE: str = "中文"
    GPT_TIMEOUT: int = 1200
    MAX_TOKENS: int = 10000000  # 每次请求的最大 token 数

    # 应用配置
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Redis配置
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_CHAT_TTL: int = 3600

    # AI响应缓存配置
    USE_AI_DEBUG_CACHE: bool = False
    AI_CACHE_DIR: str = "app/infra/cache/mock_responses"


    @property
    def github_repos(self) -> List[Dict[str, Any]]:
        """解析仓库配置字符串"""
        if self.GIT_SERVICE != "github":
            return []
            
        try:
            repos = []
            for repo_str in self.GITHUB_REPOS.split(","):
                if not repo_str:
                    continue
                if "/" not in repo_str:
                    logger.warning(f"无效的仓库格式: {repo_str}")
                    continue
                owner, name = repo_str.strip().split("/")
                repos.append({"owner": owner, "name": name, "enabled": True})
            return repos
        except Exception as e:
            logger.error(f"解析仓库配置失败: {e}")
            return []

    @property
    def gitlab_repos(self) -> List[Dict[str, Any]]:
        """解析 GitLab 仓库配置字符串"""
        if self.GIT_SERVICE != "gitlab":
            return []
            
        try:
            repos = []
            for repo_str in self.GITLAB_REPOS.split(","):
                if not repo_str:
                    continue
                if "/" not in repo_str:
                    logger.warning(f"无效的仓库格式: {repo_str}")
                    continue
                owner, name = repo_str.strip().split("/")
                repos.append({"owner": owner, "name": name, "enabled": True})
            return repos
        except Exception as e:
            logger.error(f"解析仓库配置失败: {e}")
            return []

    def is_repo_allowed(self, owner: str, repo: str) -> bool:
        """检查仓库是否在允许列表中"""
        repos = self.gitlab_repos if self.GIT_SERVICE == "gitlab" else self.github_repos
        return any(
            r["owner"] == owner and r["name"] == repo and r.get("enabled", True)
            for r in repos
        )

    def validate_git_config(self):
        """验证 Git 服务配置的完整性"""
        if self.GIT_SERVICE not in ["github", "gitlab"]:
            raise ValueError("GIT_SERVICE must be either 'github' or 'gitlab'")
            
        if self.GIT_SERVICE == "github":
            if not self.GITHUB_TOKEN:
                raise ValueError("GITHUB_TOKEN is required when using GitHub service")
        else:  # gitlab
            if not self.GITLAB_TOKEN:
                raise ValueError("GITLAB_TOKEN is required when using GitLab service")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取应用配置，使用缓存避免重复加载"""
    try:
        root_dir = Path(__file__).parent.parent.parent.parent
        env_file = root_dir / ".env"
        print(f"Looking for .env file at: {env_file}")
        print(f"File exists: {env_file.exists()}")

        settings = Settings()
        settings.validate_git_config()  # 验证配置的完整性
        return settings
    except Exception as e:
        print(f"Error loading settings: {str(e)}")
        raise