"""Base controller class managing Action Delay and safety settings."""

import time
from typing import Optional
import pyautogui
from jarvis.utils.config import JarvisConfig, load_config
from jarvis.utils.logger import get_logger

logger = get_logger("controller.base")


class ActionControllerBase:
    """Base class providing action delay pacing and safety configurations."""

    def __init__(self, action_delay: Optional[float] = None, config: Optional[JarvisConfig] = None):
        cfg = config or load_config()
        self.action_delay = action_delay if action_delay is not None else cfg.controller.action_delay
        
        # Enable PyAutoGUI screen corner failsafe
        pyautogui.FAILSAFE = cfg.controller.failsafe
        pyautogui.PAUSE = 0.05

    def sleep_delay(self):
        """Pause execution for specified action_delay to prevent command flooding."""
        if self.action_delay > 0:
            time.sleep(self.action_delay)
