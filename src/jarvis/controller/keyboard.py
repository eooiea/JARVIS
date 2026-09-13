"""Keyboard automation controller supporting safe Korean/multilingual typing."""

import time
from typing import Optional
import pyautogui
import pyperclip
from jarvis.controller.base import ActionControllerBase
from jarvis.utils.logger import get_logger

logger = get_logger("controller.keyboard")


class KeyboardController(ActionControllerBase):
    """Controls keyboard typing and hotkeys with clipboard paste for Korean compatibility."""

    def type_text(self, text: str):
        """Type text using clipboard paste (Ctrl+V) to avoid IME Korean character corruption."""
        logger.info(f"Keyboard typing -> '{text[:20]}...' (len: {len(text)})")
        pyperclip.copy(str(text))
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        self.sleep_delay()

    def press_key(self, key: str, presses: int = 1):
        """Press a special or navigation key (e.g. 'enter', 'tab', 'esc', 'backspace')."""
        logger.info(f"Keyboard press -> '{key}' (x{presses})")
        if presses > 1:
            pyautogui.press(key, presses=presses)
        else:
            pyautogui.press(key)
        self.sleep_delay()

    def hotkey(self, *keys: str):
        """Send key combination shortcut (e.g. ('ctrl', 'c'), ('alt', 'tab'))."""
        logger.info(f"Keyboard hotkey -> {keys}")
        pyautogui.hotkey(*keys)
        self.sleep_delay()
