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

    # GitHub配置
    GITHUB_TOKEN: str
    GITHUB_WEBHOOK_SECRET: Optional[str] = None
    GITHUB_API_URL: str = "https://api.github.com"

    # 允许的仓库列表，格式：owner1/repo1,owner2/repo2
    GITHUB_REPOS: str = ""

    # AI 审查限制
    MAX_FILES_PER_MR: int = 20  # MR 最大文件数
    MAX_LINES_PER_FILE: int = 1000  # 单个文件最大行数

    # 系统限制
    MAX_AI_REQUESTS_PER_HOUR: int = 30  # 每小时最大 AI 请求次数
    MAX_COMMENT_REPLIES: int = 2  # 每个评论最大回复次数
    MAX_MR_REVIEWS_PER_HOUR: int = 5  # 每小时最大处理 MR 数
    RATE_LIMIT_EXPIRE: int = 3600  # 限制过期时间（秒）

    # GPT配置
    GPT_API_KEY: str
    GPT_API_URL: str = "https://vip.apiyi.com/v1"
    GPT_MODEL: str = "claude-3-opus-20240229"
    GPT_TEMPERATURE: float = 0.7
    GPT_LANGUAGE: str = "中文"
    GPT_TIMEOUT: int = 1200
    MAX_TOKENS: int = 30000  # 每次请求的最大 token 数

    # 应用配置
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Redis配置
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_CHAT_TTL: int = 3600

    # AI响应缓存配置
    USE_AI_CACHE: bool = False
    AI_CACHE_DIR: str = "app/infra/cache/mock_responses"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    @property
    def github_repos(self) -> List[Dict[str, Any]]:
        """解析仓库配置字符串"""
        try:
            repos = []
            for repo_str in self.GITHUB_REPOS.split(","):
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
        try:
            return any(
                r["owner"] == owner and r["name"] == repo and r.get("enabled", True)
                for r in self.github_repos
            )
        except Exception as e:
            logger.error(f"检查仓库权限失败: {e}")
            return False


@lru_cache()
def get_settings() -> Settings:
    """
    获取应用配置，使用缓存避免重复加载
    """
    try:
        # 获取项目根目录
        root_dir = Path(__file__).parent.parent.parent.parent
        env_file = root_dir / ".env"
        # 打印调试信息
        print(f"Looking for .env file at: {env_file}")
        print(f"File exists: {env_file.exists()}")

        settings = Settings()
        return settings
    except Exception as e:
        print(f"Error loading settings: {str(e)}")
        raise
