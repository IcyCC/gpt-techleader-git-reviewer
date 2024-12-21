import asyncio
import os
import sys
from pathlib import Path
from app.services.discussion_service import DiscussionService
# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

from app.infra.config.settings import get_settings
from app.infra.git.github.client import GitHubClient

settings = get_settings()


async def test_get_merge_request():
    """测试获取 Pull Request 信息"""
    client = GitHubClient()
    try:
        mr = await client.get_merge_request("IcyCC", "gpt-techleader-git-reviewer", "20")
        print("\nSuccessfully fetched MR:")
        print(f"Title: {mr.title}")
        print(f"Author: {mr.author}")
        print(f"State: {mr.state}")
        print(f"Source Branch: {mr.source_branch}")
        print(f"Target Branch: {mr.target_branch}")
        print("\nFile Diffs:")
        for diff in mr.file_diffs:
            print(f"- {diff.file_name} ({diff.change_type})")
        return True
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return False

async def test_list_comments():
    client = GitHubClient()
    mr = await client.get_merge_request("IcyCC", "gpt-techleader-git-reviewer", "20")
    comments = await client.list_comments("IcyCC", "gpt-techleader-git-reviewer", mr)
    discussions = await DiscussionService().build_discussions(mr_id=mr.mr_id, owner=mr.owner, repo=mr.repo)
    

async def run_tests():
    """运行所有测试"""
    tests = [
        # ("Test Get Pull Request", test_get_merge_request),
        ("Test List Comments", test_list_comments),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\nRunning {test_name}...")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"Test error: {str(e)}")
            results.append((test_name, False))

    print("\nTest Results:")
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")


if __name__ == "__main__":
    asyncio.run(run_tests())
