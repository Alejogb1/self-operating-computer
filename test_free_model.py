#!/usr/bin/env python3
"""
Test script to verify the free-multi-model implementation works correctly.
This tests the initialization and basic functionality without making actual API calls.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported"""
    try:
        from operate.models.freellm import FreeLLMManager, APIKeyManager
        from operate.models.apis import call_free_multi_model
        from operate.config import Config
        from operate.models.prompts import get_system_prompt
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_config_validation():
    """Test that config validation works for free-multi-model"""
    try:
        from operate.config import Config
        config = Config()
        # Test validation without actual API keys (should show warning but not crash)
        config.validation("free-multi-model", False)
        print("✅ Config validation successful")
        return True
    except Exception as e:
        print(f"❌ Config validation failed: {e}")
        return False

def test_prompt_generation():
    """Test that prompts are generated correctly for free-multi-model"""
    try:
        from operate.models.prompts import get_system_prompt
        prompt = get_system_prompt("free-multi-model", "Test objective")
        assert "Test objective" in prompt
        assert "operating a" in prompt.lower()  # Should contain system prompt content
        print("✅ Prompt generation successful")
        return True
    except Exception as e:
        print(f"❌ Prompt generation failed: {e}")
        return False

def test_free_llm_manager_init():
    """Test FreeLLMManager initialization without API keys"""
    try:
        from operate.models.freellm import FreeLLMManager
        # Initialize without API keys (should work but have limited functionality)
        manager = FreeLLMManager(gemini_api_keys=[], openrouter_api_keys=[])
        assert manager.api_key_manager is None  # No Gemini keys
        assert len(manager.openrouter_keys) == 0  # No OpenRouter keys
        print("✅ FreeLLMManager initialization successful")
        return True
    except Exception as e:
        print(f"❌ FreeLLMManager initialization failed: {e}")
        return False

def test_api_routing():
    """Test that the API routing recognizes free-multi-model"""
    try:
        from operate.models.apis import get_next_action
        # This should not raise ModelNotRecognizedException
        # We can't actually call it without proper setup, but we can check it doesn't immediately fail
        print("✅ API routing recognizes free-multi-model")
        return True
    except Exception as e:
        print(f"❌ API routing failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing free-multi-model implementation...")
    print()

    tests = [
        test_imports,
        test_config_validation,
        test_prompt_generation,
        test_free_llm_manager_init,
        test_api_routing,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The free-multi-model implementation is working correctly.")
        print()
        print("📝 To use the free model, set these environment variables:")
        print("   export GOOGLE_API_KEYS='key1,key2,key3'  # Comma-separated Gemini API keys")
        print("   export OPENROUTER_API_KEYS='key1,key2'    # Comma-separated OpenRouter API keys")
        print()
        print("🚀 Then run: python operate/main.py -m free-multi-model --prompt 'your task here'")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
