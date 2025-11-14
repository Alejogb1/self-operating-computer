#!/usr/bin/env python3
"""
Test script to verify PyAutoGUI functionality and permissions.
This helps debug why PyAutoGUI appears to succeed but doesn't control the system.
"""

import pyautogui
import platform
import time
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_functionality():
    """Test basic PyAutoGUI functionality"""
    print("🧪 Testing PyAutoGUI basic functionality...")
    try:
        # Test screen size
        screen_size = pyautogui.size()
        print(f"✅ Screen size: {screen_size}")

        # Test mouse position
        current_pos = pyautogui.position()
        print(f"✅ Current mouse position: {current_pos}")

        return True
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def test_permissions():
    """Test if PyAutoGUI has necessary permissions"""
    print("\n🔐 Testing permissions...")
    if platform.system() == "Darwin":  # macOS
        try:
            # Try a simple alert - this requires accessibility permissions
            # Note: This may fail if tkinter is not available, which is different from accessibility permissions
            pyautogui.alert("Testing PyAutoGUI permissions", "Permission Test")
            print("✅ Alert displayed successfully - permissions appear granted")
            return True
        except ImportError as e:
            if "tkinter" in str(e).lower():
                print("⚠️  Tkinter not available for GUI alerts, but this doesn't affect core functionality")
                print("🔍 Testing accessibility permissions with mouse movement instead...")
                return test_accessibility_via_mouse()
            else:
                print(f"❌ Import error: {e}")
                return False
        except Exception as e:
            print(f"❌ Permission test failed: {e}")
            print("\n📋 To fix permissions on macOS:")
            print("  1. Go to System Preferences > Security & Privacy > Privacy > Accessibility")
            print("  2. Add and enable:")
            print("    - Terminal.app")
            print("    - Python (if running from command line)")
            print("    - Your IDE (VS Code, PyCharm, etc.)")
            print("  3. Also check Screen Recording permissions")
            print("  4. Restart your terminal/IDE after granting permissions")
            return False
    else:
        print("ℹ️  Permission test skipped (not macOS)")
        return True

def test_accessibility_via_mouse():
    """Test accessibility permissions by trying to move mouse programmatically"""
    try:
        # Get current position
        start_pos = pyautogui.position()

        # Try to move mouse a small amount
        pyautogui.moveTo(start_pos[0] + 10, start_pos[1] + 10, duration=0.1)
        time.sleep(0.2)

        # Check if position changed
        new_pos = pyautogui.position()

        # Move back
        pyautogui.moveTo(start_pos[0], start_pos[1], duration=0.1)

        if new_pos[0] != start_pos[0] or new_pos[1] != start_pos[1]:
            print("✅ Mouse movement successful - accessibility permissions appear granted")
            return True
        else:
            print("❌ Mouse didn't move - accessibility permissions may be missing")
            return False
    except Exception as e:
        print(f"❌ Accessibility test via mouse failed: {e}")
        return False

def test_mouse_control():
    """Test mouse control functionality"""
    print("\n🖱️  Testing mouse control...")
    try:
        # Get current position
        start_pos = pyautogui.position()
        print(f"📍 Starting mouse position: {start_pos}")

        # Try to move mouse slightly
        pyautogui.moveTo(start_pos[0] + 50, start_pos[1] + 50, duration=0.5)
        time.sleep(0.5)

        # Check if position changed
        new_pos = pyautogui.position()
        print(f"📍 New mouse position: {new_pos}")

        if new_pos != start_pos:
            print("✅ Mouse movement successful")
            return True
        else:
            print("❌ Mouse position didn't change - control may be blocked")
            return False

    except pyautogui.FailSafeException as e:
        print(f"❌ FailSafe triggered (mouse moved to corner): {e}")
        return False
    except Exception as e:
        print(f"❌ Mouse control test failed: {e}")
        return False

def test_keyboard_control():
    """Test keyboard control functionality"""
    print("\n⌨️  Testing keyboard control...")
    try:
        # Try to type in current window
        pyautogui.write("PyAutoGUI test", interval=0.1)
        print("✅ Keyboard input attempted")
        return True
    except pyautogui.FailSafeException as e:
        print(f"❌ FailSafe triggered: {e}")
        return False
    except Exception as e:
        print(f"❌ Keyboard control test failed: {e}")
        return False

def test_operating_system_class():
    """Test the OperatingSystem class from the project"""
    print("\n🏗️  Testing OperatingSystem class...")
    try:
        from operate.utils.operating_system import OperatingSystem
        os_instance = OperatingSystem()

        # Test write function
        print("Testing write function...")
        success = os_instance.write("test")
        if success:
            print("✅ OperatingSystem.write() succeeded")
        else:
            print("❌ OperatingSystem.write() failed")

        # Test press function
        print("Testing press function...")
        success = os_instance.press(["a"])
        if success:
            print("✅ OperatingSystem.press() succeeded")
        else:
            print("❌ OperatingSystem.press() failed")

        return True
    except Exception as e:
        print(f"❌ OperatingSystem class test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🔧 PyAutoGUI Diagnostic Tool")
    print("=" * 40)

    tests = [
        test_basic_functionality,
        test_permissions,
        test_mouse_control,
        test_keyboard_control,
        test_operating_system_class,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 40)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! PyAutoGUI should be working correctly.")
    else:
        print("❌ Some tests failed. Check the output above for specific issues.")
        print("\n💡 Common solutions:")
        print("  - Grant accessibility permissions (macOS)")
        print("  - Make sure target application is focused")
        print("  - Check if PyAutoGUI failsafe is triggered")
        print("  - Try running with sudo (not recommended for security)")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
