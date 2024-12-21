import asyncio
import sys
from pathlib import Path

project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

from app.infra.ai.client import AIClient, Message

async def test_chat_with_session():
    """测试带会话的对话功能"""
    client = AIClient()
    try:
        # 创建新会话
        session_id = client.generate_session_id()
        
        # 第一轮对话
        messages1 = [
            Message("system", "You are a helpful assistant."),
            Message("user", "Hello! What's your name?")
        ]
        response1 = await client.chat(messages1, session_id=session_id)
        print("\nFirst Response:", response1)
        
        # 第二轮对话，应该能记住上下文
        messages2 = [
            Message("user", "What did I just ask you?")
        ]
        response2 = await client.chat(messages2, session_id=session_id)
        print("\nSecond Response:", response2)
        
        # 获取历史记录
        history = await client.get_chat_history(session_id)
        print("\nChat History:", len(history), "messages")
        
        # 清除历史记录
        await client.clear_chat_history(session_id)
        return True
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return False

async def run_tests():
    """运行所有测试"""
    tests = [
        ("Test Chat with Session", test_chat_with_session),
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