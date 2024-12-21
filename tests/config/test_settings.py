import pytest
from app.infra.config.settings import get_settings

def test_settings():
    """测试配置加载"""
    settings = get_settings()
    
    # 验证必要的配置项
    assert settings.GPT_API_KEY, "GPT_API_KEY not found"
    assert settings.GITHUB_TOKEN, "GITHUB_TOKEN not found"
    assert settings.GITHUB_REPO_OWNER, "GITHUB_REPO_OWNER not found"
    assert settings.GITHUB_REPO_NAME, "GITHUB_REPO_NAME not found"
    
    # 打印配置信息
    print("\nLoaded Settings:")
    print(f"GPT_API_KEY: {settings.GPT_API_KEY[:10]}...")
    print(f"GITHUB_TOKEN: {settings.GITHUB_TOKEN[:10]}...")
    print(f"REPO: {settings.GITHUB_REPO_OWNER}/{settings.GITHUB_REPO_NAME}")

if __name__ == "__main__":
    test_settings() 