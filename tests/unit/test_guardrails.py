"""Unit tests for JARVIS Safety & Guardrails (TDD Red-Green)."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from jarvis.guardrails.killswitch import KillSwitch, EmergencyStopException
from jarvis.guardrails.permissions import PermissionManager, PermissionDeniedError
from jarvis.guardrails.connectivity import ConnectivityGuard
from jarvis.utils.config import JarvisConfig


# ==========================================
# 1. KillSwitch Tests
# ==========================================
def test_killswitch_trigger_and_check():
    """KillSwitch should raise EmergencyStopException once triggered."""
    ks = KillSwitch()
    assert not ks.is_triggered()

    # Normal execution passes
    ks.check_emergency_stop()

    # Trigger emergency stop
    ks.trigger()
    assert ks.is_triggered()

    with pytest.raises(EmergencyStopException) as exc_info:
        ks.check_emergency_stop()
    assert "긴급 중단(Kill-Switch)" in str(exc_info.value)

    # Reset
    ks.reset()
    assert not ks.is_triggered()
    ks.check_emergency_stop()


# ==========================================
# 2. PermissionManager Tests
# ==========================================
def test_permission_manager_safe_operations(tmp_path: Path):
    """PermissionManager should automatically allow safe operations inside output directory."""
    pm = PermissionManager(allowed_output_dir=tmp_path)
    safe_file = tmp_path / "new_report.xlsx"

    # Creating new file inside allowed output dir is SAFE
    allowed = pm.check_permission(action="create_file", target_path=safe_file)
    assert allowed is True


def test_permission_manager_dangerous_operation_rejected(tmp_path: Path):
    """PermissionManager should reject dangerous delete action when callback returns False."""
    pm = PermissionManager(allowed_output_dir=tmp_path, confirm_callback=lambda msg: False)
    target_file = tmp_path / "important_data.xlsx"

    # Deleting a file requires explicit approval
    with pytest.raises(PermissionDeniedError) as exc_info:
        pm.check_permission(action="delete_file", target_path=target_file)
    assert "작업 권한이 거부되었습니다" in str(exc_info.value)


def test_permission_manager_system_directory_blocked():
    """PermissionManager should immediately block system critical directory accesses."""
    pm = PermissionManager(confirm_callback=lambda msg: True)
    system_path = Path("C:/Windows/System32/config.sys")

    with pytest.raises(PermissionDeniedError) as exc_info:
        pm.check_permission(action="modify_file", target_path=system_path)
    assert "시스템 보호 디렉터리" in str(exc_info.value)


# ==========================================
# 3. ConnectivityGuard Tests
# ==========================================
def test_connectivity_guard_gemini_diagnose():
    """ConnectivityGuard should diagnose missing Gemini API key with friendly Korean guide."""
    config_no_key = JarvisConfig(gemini_api_key=None)
    guard = ConnectivityGuard(config=config_no_key)

    is_ready, message = guard.diagnose_provider("gemini")
    assert is_ready is False
    assert "GEMINI_API_KEY" in message
    assert "Google AI Studio" in message


def test_connectivity_guard_valid_gemini():
    """ConnectivityGuard should approve valid Gemini key configuration."""
    config_valid = JarvisConfig(gemini_api_key="AIzaSyValidTestKey123")
    guard = ConnectivityGuard(config=config_valid)

    is_ready, message = guard.diagnose_provider("gemini")
    assert is_ready is True
    assert "정상" in message
