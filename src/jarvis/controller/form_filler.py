"""Hybrid Form Filler combining Vision Anchor detection with high-speed Tab sequencing."""

from typing import Union, List, Dict, Optional, Any
from jarvis.controller.mouse import MouseController
from jarvis.controller.keyboard import KeyboardController
from jarvis.vision.anchor import VisionAnchorFinder
from jarvis.vision.capture import ScreenCapture
from jarvis.utils.logger import get_logger

logger = get_logger("controller.form_filler")


class HybridFormFiller:
    """Automates form entry: 1) Vision Anchor click -> 2) Tab/typing sequencing."""

    def __init__(
        self,
        mouse: Optional[MouseController] = None,
        keyboard: Optional[KeyboardController] = None,
        anchor_finder: Optional[VisionAnchorFinder] = None,
        screen_capture: Optional[ScreenCapture] = None,
    ):
        self.mouse = mouse or MouseController()
        self.keyboard = keyboard or KeyboardController()
        self.anchor_finder = anchor_finder
        self.screen_capture = screen_capture

    def _extract_field_values(self, fields: Union[List[Any], Dict[str, Any]]) -> List[str]:
        """Convert list or dictionary into flat list of string values."""
        if isinstance(fields, dict):
            return [str(v) for v in fields.values()]
        elif isinstance(fields, list):
            return [str(v) for v in fields]
        return [str(fields)]

    def fill_form(
        self,
        fields: Union[List[Any], Dict[str, Any]],
        anchor_label: Optional[str] = None,
        delimiter_key: str = "tab",
        submit_key: Optional[str] = None,
    ) -> int:
        """Fill repetitive form fields starting from vision anchor or current focus."""
        values = self._extract_field_values(fields)
        if not values:
            logger.warning("No form values provided to fill.")
            return 0

        # Step 1: Vision Anchor Click (if requested)
        if anchor_label and self.anchor_finder and self.screen_capture:
            logger.info(f"Finding anchor for starting field: '{anchor_label}'")
            screenshot_bytes = self.screen_capture.capture_full_screen()
            coords = self.anchor_finder.find_anchor(screenshot_bytes, target_label=anchor_label)
            if coords:
                x, y = coords
                logger.info(f"Clicking starting form anchor at ({x}, {y})")
                self.mouse.click(x, y)
            else:
                logger.warning(f"Anchor '{anchor_label}' not detected. Proceeding from current focus.")

        # Step 2: High-speed Sequential Typing + Tab Navigation
        logger.info(f"Starting sequential form entry for {len(values)} fields...")
        for idx, val in enumerate(values):
            self.keyboard.type_text(val)
            # Press delimiter (Tab/Enter) between fields, except after the last one
            if idx < len(values) - 1:
                self.keyboard.press_key(delimiter_key)

        # Optional Submit Key
        if submit_key:
            logger.info(f"Submitting form with '{submit_key}' key.")
            self.keyboard.press_key(submit_key)

        logger.info(f"Completed filling {len(values)} form fields.")
        return len(values)
