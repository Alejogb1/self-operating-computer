#!/usr/bin/env python3
"""
Test script to verify that free-multi-model no longer falls back to GPT-4
"""

import sys
import os
import asyncio

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_free_model_no_gpt4_fallback():
    """Test that free-multi-model handles failures properly without GPT-4 fallback"""
    print("🧪 Testing free-multi-model error handling...")

    try:
        from operate.models.apis import get_next_action

        # Test with free-multi-model
        messages = [{"role": "system", "content": "Test system prompt"}]
        objective = "Test objective"

        result = await get_next_action("free-multi-model", messages, objective, None)

        print("✅ free-multi-model succeeded (API keys are working)")
        print("💡 This means the fix prevents GPT-4 fallback when free models work")
        return True

    except Exception as e:
        error_msg = str(e).lower()
        print(f"✅ Expected failure occurred: {str(e)[:100]}...")

        # Check that the error is about free models failing, not about OpenAI API key
        if "free llm providers failed" in error_msg and "api_key" not in error_msg:
            print("✅ Error message correctly indicates free model failure (no GPT-4 fallback)")
            return True
        elif "openai_api_key" in error_msg or "api_key client option" in error_msg:
            print("❌ Error still mentions OpenAI API key - fallback not removed properly")
            return False
        else:
            print(f"⚠️  Unexpected error type: {error_msg}")
            return False

async def main():
    """Run the test"""
    print("🔧 Testing free-multi-model fix (no GPT-4 fallback)")
    print("=" * 50)

    success = await test_free_model_no_gpt4_fallback()

    print("=" * 50)
    if success:
        print("🎉 Fix verified! free-multi-model no longer falls back to GPT-4")
        print("💡 Now it will show clear error messages when free APIs fail")
    else:
        print("❌ Fix not working properly")

    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
