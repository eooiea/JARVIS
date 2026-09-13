"""Unit tests for Desktop Controller and Hybrid Form Filler (TDD Red-Green)."""

import pytest
from unittest.mock import MagicMock, patch, call
from jarvis.controller.mouse import MouseController
from jarvis.controller.keyboard import KeyboardController
from jarvis.controller.form_filler import HybridFormFiller


# ==========================================
# 1. MouseController Tests
# ==========================================
@patch("jarvis.controller.mouse.pyautogui")
def test_mouse_controller_actions(mock_pag):
    """MouseController should properly wrap and delegate mouse movements and clicks."""
    mouse = MouseController(action_delay=0.01)

    mouse.move_to(100, 200)
    mock_pag.moveTo.assert_called_with(100, 200, duration=0.0)

    mouse.click(100, 200, button="left")
    mock_pag.click.assert_called_with(x=100, y=200, clicks=1, button="left")

    mouse.double_click(100, 200)
    mock_pag.doubleClick.assert_called_with(x=100, y=200)

    mouse.scroll(-500)
    mock_pag.scroll.assert_called_with(-500)


# ==========================================
# 2. KeyboardController Tests
# ==========================================
@patch("jarvis.controller.keyboard.pyautogui")
@patch("jarvis.controller.keyboard.pyperclip")
def test_keyboard_controller_type_and_hotkeys(mock_clip, mock_pag):
    """KeyboardController should support text typing and hotkey sending."""
    keyboard = KeyboardController(action_delay=0.01)

    keyboard.type_text("홍길동")
    mock_clip.copy.assert_called_with("홍길동")
    mock_pag.hotkey.assert_called_with("ctrl", "v")

    keyboard.press_key("tab")
    mock_pag.press.assert_called_with("tab")

    keyboard.hotkey("ctrl", "a")
    mock_pag.hotkey.assert_called_with("ctrl", "a")


# ==========================================
# 3. HybridFormFiller Tests
# ==========================================
def test_hybrid_form_filler_with_anchor():
    """HybridFormFiller should click detected anchor coordinate and sequential type with Tab."""
    mock_mouse = MagicMock()
    mock_keyboard = MagicMock()
    mock_anchor_finder = MagicMock()
    mock_capture = MagicMock()

    # Anchor found at (350, 420)
    mock_anchor_finder.find_anchor.return_value = (350, 420)
    mock_capture.capture_full_screen.return_value = b"mock_img_bytes"

    filler = HybridFormFiller(
        mouse=mock_mouse,
        keyboard=mock_keyboard,
        anchor_finder=mock_anchor_finder,
        screen_capture=mock_capture,
    )

    form_data = ["홍길동", "010-1234-5678", "서울시 강남구", "50000"]
    filled_count = filler.fill_form(
        fields=form_data,
        anchor_label="이름 입력창",
        delimiter_key="tab",
    )

    assert filled_count == 4
    # 1. Vision anchor click
    mock_mouse.click.assert_called_with(350, 420)
    # 2. Sequential typing & Tab press
    expected_type_calls = [call("홍길동"), call("010-1234-5678"), call("서울시 강남구"), call("50000")]
    mock_keyboard.type_text.assert_has_calls(expected_type_calls)
    assert mock_keyboard.press_key.call_count == 3  # Tab between 4 fields


def test_hybrid_form_filler_without_anchor():
    """HybridFormFiller without anchor should type directly at current focus."""
    mock_mouse = MagicMock()
    mock_keyboard = MagicMock()

    filler = HybridFormFiller(
        mouse=mock_mouse,
        keyboard=mock_keyboard,
        anchor_finder=None,
        screen_capture=None,
    )

    form_dict = {"품목": "모니터", "단가": "250000"}
    filled_count = filler.fill_form(fields=form_dict)

    assert filled_count == 2
    mock_mouse.click.assert_not_called()
    mock_keyboard.type_text.assert_has_calls([call("모니터"), call("250000")])
