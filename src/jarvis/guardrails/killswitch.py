"""Emergency Stop Kill-Switch for halting automated GUI and agent actions."""

import threading
from typing import Optional
from jarvis.utils.logger import get_logger

logger = get_logger("guardrails.killswitch")


class EmergencyStopException(Exception):
    """Raised when emergency stop (Kill-Switch) is triggered by the user."""
    pass


class KillSwitch:
    """Monitors emergency stop triggers (hotkeys, mouse corners, programmatic flags)."""

    def __init__(self):
        self._stop_event = threading.Event()
        self._listener_active = False

    def trigger(self):
        """Trigger emergency stop immediately."""
        logger.critical("🚨 [긴급 중단] 킬스위치(Kill-Switch)가 트리거되었습니다! 모든 자동화 작업을 즉시 중단합니다.")
        self._stop_event.set()

    def is_triggered(self) -> bool:
        """Check if kill switch is currently in triggered state."""
        return self._stop_event.is_set()

    def reset(self):
        """Reset emergency stop state back to normal."""
        self._stop_event.clear()
        logger.info("Kill-Switch state has been reset to normal.")

    def check_emergency_stop(self):
        """Raise EmergencyStopException if kill switch is triggered."""
        if self._stop_event.is_set():
            raise EmergencyStopException(
                "🚨 [긴급 중단(Kill-Switch) 발동] 사용자의 요청에 의해 모든 GUI 및 작업이 즉시 중지되었습니다."
            )

    def start_hotkey_listener(self, hotkey: str = "ctrl+alt+s"):
        """Attach global keyboard hotkey listener for emergency stops."""
        try:
            import keyboard
            keyboard.add_hotkey(hotkey, self.trigger)
            self._listener_active = True
            logger.info(f"Attached emergency stop global hotkey: '{hotkey}'")
        except Exception as e:
            logger.warning(f"Could not bind global hotkey '{hotkey}' ({e}). Mouse failsafe remains active.")
