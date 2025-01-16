import asyncio
import sys
from pathlib import Path
from app.services.discussion_service import DiscussionService

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

from app.infra.config.settings import get_settings
from app.infra.git.gitlab.client import GitLabClient

settings = get_settings()


async def test_get_merge_request():
    """Test fetching Merge Request information"""
    client = GitLabClient()
    try:
        # Replace with actual GitLab project ID and MR IID
        mr = await client.get_merge_request("axq","axq-public", "679")
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
    """Test fetching MR comments"""
    client = GitLabClient()
    try:
        mr = await client.get_merge_request("axq","axq-public", "679")
        comments = await client.list_comments("axq",mr.repo, mr)
        discussions = await DiscussionService().build_discussions(
            "axq",
            "axq-public",
            mr.mr_id
        )
        import ipdb;ipdb.set_trace()
        print("\nSuccessfully fetched comments:")
        for comment in comments:
            print(f"- Comment by {comment.author}: {comment.content[:50]}...")
        return True
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return False


async def run_tests():
    """Run all tests"""
    tests = [
        ("Test Get Merge Request", test_get_merge_request),
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