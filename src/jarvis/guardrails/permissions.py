"""Permission and file safety guardrail preventing dangerous operations."""

from pathlib import Path
from typing import Optional, Callable
from jarvis.utils.logger import get_logger

logger = get_logger("guardrails.permissions")

BLOCKED_SYSTEM_PATHS = [
    Path("C:/Windows"),
    Path("C:/Program Files"),
    Path("C:/Program Files (x86)"),
    Path("/System"),
    Path("/usr"),
    Path("/etc"),
]


class PermissionDeniedError(Exception):
    """Raised when an unauthorized or unconfirmed dangerous operation is attempted."""
    pass


class PermissionManager:
    """Classifies actions into safe/dangerous and enforces confirmation policies."""

    def __init__(
        self,
        allowed_output_dir: Optional[Path | str] = None,
        confirm_callback: Optional[Callable[[str], bool]] = None,
    ):
        self.allowed_output_dir = Path(allowed_output_dir).resolve() if allowed_output_dir else None
        self.confirm_callback = confirm_callback

    def _is_system_path(self, target: Path) -> bool:
        """Check if target path is within protected OS system directories."""
        try:
            resolved = target.resolve()
            for sys_path in BLOCKED_SYSTEM_PATHS:
                try:
                    if resolved.is_relative_to(sys_path.resolve()):
                        return True
                except (ValueError, AttributeError):
                    if str(resolved).lower().startswith(str(sys_path).lower()):
                        return True
        except Exception:
            pass
        return False

    def check_permission(self, action: str, target_path: Optional[Path | str] = None) -> bool:
        """Evaluate if an action is safe or requires user approval."""
        path_obj = Path(target_path).resolve() if target_path else None

        # 1. Block system critical path modifications unconditionally
        if path_obj and self._is_system_path(path_obj):
            logger.critical(f"Blocked dangerous access to system path: {path_obj}")
            raise PermissionDeniedError(
                f"[접근 거부] 시스템 보호 디렉터리({path_obj})에 대한 수정/삭제는 보안상 절대 금지됩니다."
            )

        # 2. Check safe actions (Creating new files inside allowed output directory)
        if action in ("create_file", "capture_screen", "read_safe"):
            if path_obj and self.allowed_output_dir:
                try:
                    if path_obj.is_relative_to(self.allowed_output_dir):
                        return True
                except (ValueError, AttributeError):
                    if str(path_obj).startswith(str(self.allowed_output_dir)):
                        return True
            elif not path_obj:
                return True

        # 3. Dangerous actions (File deletion, overwriting existing non-output files)
        if action in ("delete_file", "overwrite_file", "execute_system_command", "modify_file"):
            prompt_msg = f"[위험 작업 승인 요청] '{action}' 작업을 대상({path_obj})에 수행하시겠습니까?"
            logger.warning(prompt_msg)

            if self.confirm_callback:
                approved = self.confirm_callback(prompt_msg)
                if approved:
                    logger.info(f"User approved dangerous action: '{action}'")
                    return True

            raise PermissionDeniedError(
                f"[작업 권한이 거부되었습니다] 위험 작업({action} on {path_obj})에 대한 사용자 승인이 없습니다."
            )

        return True
