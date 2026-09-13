"""Mouse automation controller wrapping PyAutoGUI with safety delays."""

from typing import Optional
import pyautogui
from jarvis.controller.base import ActionControllerBase
from jarvis.utils.logger import get_logger

logger = get_logger("controller.mouse")


class MouseController(ActionControllerBase):
    """Controls mouse movement, single/double clicks, drag, and scrolling."""

    def move_to(self, x: int, y: int, duration: float = 0.0):
        """Move cursor to specified screen coordinates."""
        logger.info(f"Mouse move -> ({x}, {y})")
        pyautogui.moveTo(x, y, duration=duration)
        self.sleep_delay()

    def click(self, x: Optional[int] = None, y: Optional[int] = None, clicks: int = 1, button: str = "left"):
        """Click mouse at target coordinates or current cursor location."""
        logger.info(f"Mouse click -> ({x}, {y}), button={button}, clicks={clicks}")
        if x is not None and y is not None:
            pyautogui.click(x=x, y=y, clicks=clicks, button=button)
        else:
            pyautogui.click(clicks=clicks, button=button)
        self.sleep_delay()

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None):
        """Double click mouse at target coordinates or current cursor location."""
        logger.info(f"Mouse double click -> ({x}, {y})")
        if x is not None and y is not None:
            pyautogui.doubleClick(x=x, y=y)
        else:
            pyautogui.doubleClick()
        self.sleep_delay()

    def drag_to(self, x: int, y: int, button: str = "left", duration: float = 0.2):
        """Drag mouse from current position to (x, y)."""
        logger.info(f"Mouse drag -> ({x}, {y})")
        pyautogui.dragTo(x, y, duration=duration, button=button)
        self.sleep_delay()

    def scroll(self, clicks: int):
        """Scroll mouse wheel vertically (positive: up, negative: down)."""
        logger.info(f"Mouse scroll -> {clicks}")
        pyautogui.scroll(clicks)
        self.sleep_delay()
