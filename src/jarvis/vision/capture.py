"""High-speed screen and region capture module using mss and Pillow ImageGrab fallback."""

import io
from typing import Optional, Dict, Any
import mss
from PIL import Image, ImageGrab
from jarvis.utils.logger import get_logger

logger = get_logger("vision.capture")


class ScreenCapture:
    """High-speed screen capturing engine supporting mss and PIL.ImageGrab fallback."""

    def __init__(self):
        pass

    def _sct_to_png_bytes(self, sct_img: Any) -> bytes:
        """Convert mss ScreenShot object (RGB/BGRA) to PNG bytes via Pillow."""
        img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    def _pil_to_png_bytes(self, img: Image.Image) -> bytes:
        """Convert Pillow Image to PNG bytes."""
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    def capture_full_screen(self, monitor_index: int = 1) -> bytes:
        """Capture full screen. Uses mss with ImageGrab fallback."""
        try:
            import mss
            with mss.mss() as sct:
                if monitor_index >= len(sct.monitors):
                    monitor_index = 1
                monitor = sct.monitors[monitor_index]
                sct_img = sct.grab(monitor)
                logger.info(f"Captured screen via mss (monitor {monitor_index}): {sct_img.size}")
                return self._sct_to_png_bytes(sct_img)
        except Exception as e:
            logger.warning(f"mss capture failed ({e}), falling back to PIL.ImageGrab")
            img = ImageGrab.grab(all_screens=True)
            logger.info(f"Captured screen via ImageGrab: {img.size}")
            return self._pil_to_png_bytes(img)

    def capture_region(self, x: int, y: int, width: int, height: int) -> bytes:
        """Capture specific screen bounding box region."""
        bbox = (int(x), int(y), int(x + width), int(y + height))
        try:
            import mss
            region: Dict[str, int] = {
                "left": int(x),
                "top": int(y),
                "width": int(width),
                "height": int(height),
            }
            with mss.mss() as sct:
                sct_img = sct.grab(region)
                logger.info(f"Captured screen region via mss: {x, y, width, height}")
                return self._sct_to_png_bytes(sct_img)
        except Exception as e:
            logger.warning(f"mss region capture failed ({e}), falling back to PIL.ImageGrab")
            img = ImageGrab.grab(bbox=bbox)
            logger.info(f"Captured screen region via ImageGrab: {img.size}")
            return self._pil_to_png_bytes(img)
