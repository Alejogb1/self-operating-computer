import pyautogui
import platform
import time
import math
import subprocess
import sys

from operate.utils.misc import convert_percent_to_decimal


class OperatingSystem:
    def __init__(self):
        self._check_permissions()

    def _check_permissions(self):
        """Check if PyAutoGUI has necessary permissions on macOS"""
        if platform.system() == "Darwin":  # macOS
            try:
                # Try to get screen size - this will fail if no accessibility permissions
                pyautogui.size()
                print("[OperatingSystem] PyAutoGUI permissions appear to be granted")
            except Exception as e:
                print(f"[OperatingSystem] WARNING: PyAutoGUI permissions check failed: {e}")
                print("[OperatingSystem] On macOS, you need to grant accessibility permissions:")
                print("  1. Go to System Preferences > Security & Privacy > Privacy > Accessibility")
                print("  2. Add and enable Terminal, Python, and any IDE you're using")
                print("  3. Also check Screen Recording permissions for screenshots")
                return False
        return True

    def write(self, content):
        try:
            content = content.replace("\\n", "\n")
            for char in content:
                pyautogui.write(char)
            print(f"[OperatingSystem][write] Successfully wrote: '{content}'")
            return True
        except pyautogui.FailSafeException as e:
            print(f"[OperatingSystem][write] FailSafe triggered (mouse moved to corner): {e}")
            return False
        except Exception as e:
            print(f"[OperatingSystem][write] Error: {e}")
            return False

    def press(self, keys):
        try:
            for key in keys:
                pyautogui.keyDown(key)
            time.sleep(0.1)
            for key in keys:
                pyautogui.keyUp(key)
            print(f"[OperatingSystem][press] Successfully pressed keys: {keys}")
            return True
        except pyautogui.FailSafeException as e:
            print(f"[OperatingSystem][press] FailSafe triggered (mouse moved to corner): {e}")
            return False
        except Exception as e:
            print(f"[OperatingSystem][press] Error: {e}")
            return False

    def mouse(self, click_detail):
        try:
            x = convert_percent_to_decimal(click_detail.get("x"))
            y = convert_percent_to_decimal(click_detail.get("y"))

            if click_detail and isinstance(x, float) and isinstance(y, float):
                success = self.click_at_percentage(x, y)
                return success
            else:
                print(f"[OperatingSystem][mouse] Invalid click coordinates: {click_detail}")
                return False
        except Exception as e:
            print(f"[OperatingSystem][mouse] Error: {e}")
            return False

    def click_at_percentage(
        self,
        x_percentage,
        y_percentage,
        duration=0.2,
        circle_radius=50,
        circle_duration=0.5,
    ):
        try:
            screen_width, screen_height = pyautogui.size()
            x_pixel = int(screen_width * float(x_percentage))
            y_pixel = int(screen_height * float(y_percentage))

            print(f"[OperatingSystem][click_at_percentage] Moving to screen coordinates: ({x_pixel}, {y_pixel}) from percentages ({x_percentage*100:.1f}%, {y_percentage*100:.1f}%)")

            pyautogui.moveTo(x_pixel, y_pixel, duration=duration)

            start_time = time.time()
            while time.time() - start_time < circle_duration:
                angle = ((time.time() - start_time) / circle_duration) * 2 * math.pi
                x = x_pixel + math.cos(angle) * circle_radius
                y = y_pixel + math.sin(angle) * circle_radius
                pyautogui.moveTo(x, y, duration=0.1)

            pyautogui.click(x_pixel, y_pixel)
            print(f"[OperatingSystem][click_at_percentage] Successfully clicked at ({x_pixel}, {y_pixel})")
            return True
        except pyautogui.FailSafeException as e:
            print(f"[OperatingSystem][click_at_percentage] FailSafe triggered (mouse moved to corner): {e}")
            return False
        except Exception as e:
            print(f"[OperatingSystem][click_at_percentage] Error: {e}")
            return False
