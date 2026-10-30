"""
Aura Ghost Vision Auto-Click Engine
===================================
Autonomous Multimodal Visual Computer Use for Aura AI.
Features:
- State-of-the-art screen visual grounding using Google Gemini Vision
- Real-time UI element coordinate detection (x, y)
- Holographic Neon Sci-Fi Target Reticle animation over screen
- Smooth human-like cursor glide with ease-out physics
- Precision autonomous clicks (single, double, right)
- 100% Tanglish & English natural command comprehension
"""

from __future__ import annotations

import io
import os
import re
import sys
import json
import time
import math
import base64
import threading
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Callable

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    _PYAUTOGUI_OK = True
except ImportError:
    _PYAUTOGUI_OK = False

try:
    import PIL.Image
    from PIL import ImageGrab
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

try:
    import mss
    _MSS_OK = True
except ImportError:
    _MSS_OK = False

try:
    from google import genai
    from google.genai import types
    _GOOGLE_GENAI_OK = True
except ImportError:
    _GOOGLE_GENAI_OK = False

from core.user_paths import get_user_data_dir


# -----------------------------------------------------------------------------
# 1. HOLOGRAPHIC RETICLE OVERLAY (PYQT6)
# -----------------------------------------------------------------------------
def _spawn_reticle_overlay(x: int, y: int, label: str = "TARGET"):
    """Spawns an ephemeral holographic target reticle widget on screen at (x, y)."""
    try:
        from PyQt6.QtWidgets import QApplication, QWidget
        from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
        from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont

        app = QApplication.instance()
        if not app:
            return

        class _ReticleWidget(QWidget):
            def __init__(self, cx: int, cy: int, target_label: str):
                super().__init__(None)
                self.cx = cx
                self.cy = cy
                self.target_label = target_label[:24].upper()
                self.box_size = 140
                self.setFixedSize(self.box_size, self.box_size)
                self.move(int(cx - self.box_size // 2), int(cy - self.box_size // 2))

                self.setWindowFlags(
                    Qt.WindowType.FramelessWindowHint
                    | Qt.WindowType.WindowStaysOnTopHint
                    | Qt.WindowType.Tool
                    | Qt.WindowType.WindowTransparentForInput
                )
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

                self._angle = 0.0
                self._progress = 0.0  # 0.0 to 1.0 over lifetime
                self._clicked = False
                self._click_ripple = 0.0

                self._timer = QTimer(self)
                self._timer.timeout.connect(self._tick)
                self._timer.start(16)  # ~60 FPS

            def trigger_click_burst(self):
                self._clicked = True

            def _tick(self):
                self._progress += 0.028
                self._angle = (self._angle + 4.5) % 360
                if self._clicked:
                    self._click_ripple += 0.08

                if self._progress >= 1.0:
                    self._timer.stop()
                    self.close()
                    self.deleteLater()
                else:
                    self.update()

            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)

                w, h = self.width(), self.height()
                mid_x, mid_y = w / 2.0, h / 2.0
                max_r = 38.0

                alpha = int(255 * (1.0 - (self._progress ** 2)))

                # 1. Outer Tech Target Ring (Rotating Cyan)
                painter.save()
                painter.translate(mid_x, mid_y)
                painter.rotate(self._angle)
                pen_ring = QPen(QColor(0, 245, 255, min(240, alpha)), 1.8)
                painter.setPen(pen_ring)
                painter.setBrush(Qt.BrushStyle.NoBrush)

                ring_rect = QRectF(-max_r, -max_r, max_r * 2, max_r * 2)
                # 4 segmented arcs
                for i in range(4):
                    start_angle = i * 90 + 15
                    painter.drawArc(ring_rect, int(start_angle * 16), int(60 * 16))

                # Corner brackets
                br_len = 8.0
                for deg in (45, 135, 225, 315):
                    rad = math.radians(deg)
                    bx = (max_r + 4) * math.cos(rad)
                    by = (max_r + 4) * math.sin(rad)
                    painter.drawEllipse(QPointF(bx, by), 1.5, 1.5)
                painter.restore()

                # 2. Inner Pulse Reticle
                pulse = 0.5 + 0.5 * math.sin(self._progress * math.pi * 3)
                inner_r = 16.0 + 4.0 * pulse
                pen_inner = QPen(QColor(57, 255, 20, min(230, alpha)), 1.5)
                painter.setPen(pen_inner)
                painter.drawEllipse(QPointF(mid_x, mid_y), inner_r, inner_r)

                # Center Crosshair Dot
                painter.setBrush(QBrush(QColor(57, 255, 20, min(255, alpha))))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(mid_x, mid_y), 3.0, 3.0)

                # 3. Expanding Click Shockwave Burst
                if self._clicked:
                    burst_r = inner_r + self._click_ripple * 35.0
                    burst_alpha = max(0, int(220 * (1.0 - min(1.0, self._click_ripple))))
                    pen_burst = QPen(QColor(57, 255, 20, burst_alpha), 2.2)
                    painter.setPen(pen_burst)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawEllipse(QPointF(mid_x, mid_y), burst_r, burst_r)

                # 4. Sci-Fi HUD Label Tag
                painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
                painter.setPen(QPen(QColor(0, 245, 255, min(220, alpha))))
                lbl_text = f"◎ LOCKED: {self.target_label}"
                painter.drawText(QRectF(0, h - 22, w, 18), Qt.AlignmentFlag.AlignCenter, lbl_text)

        # Post to main GUI thread if needed
        def _show():
            try:
                overlay = _ReticleWidget(x, y, label)
                overlay.show()
                # Store reference on app to prevent garbage collection
                if not hasattr(app, "_ghost_reticles"):
                    app._ghost_reticles = []
                app._ghost_reticles.append(overlay)
                # Auto-remove reference on close
                overlay.destroyed.connect(lambda: app._ghost_reticles.remove(overlay) if overlay in getattr(app, "_ghost_reticles", []) else None)
            except Exception as e:
                print(f"[GhostVision] Overlay show error: {e}")

        from PyQt6.QtCore import QMetaObject, Q_ARG
        from PyQt6.QtCore import pyqtSlot
        if threading.current_thread() == threading.main_thread():
            _show()
        else:
            QTimer.singleShot(0, _show)

    except Exception as e:
        print(f"[GhostVision] Overlay init error: {e}")


# -----------------------------------------------------------------------------
# 2. GHOST VISION AUTO-CLICK ENGINE
# -----------------------------------------------------------------------------
class GhostVisionEngine:
    """Autonomous Visual Grounding and Auto-Click Engine."""

    def __init__(self):
        self._api_config_path = get_user_data_dir() / "config" / "api_keys.json"

    def _get_api_key(self) -> str:
        try:
            if self._api_config_path.exists():
                with open(self._api_config_path, "r", encoding="utf-8") as f:
                    keys = json.load(f)
                return keys.get("gemini_api_key", "").strip()
        except Exception:
            pass
        return ""

    def capture_screen_image(self) -> Tuple[Optional[bytes], int, int]:
        """Captures full screen and returns (jpeg_bytes, width, height)."""
        # A. Try MSS for zero-latency screen grab
        if _MSS_OK:
            try:
                with mss.mss() as sct:
                    monitor = sct.monitors[1]  # primary display
                    img = sct.grab(monitor)
                    w, h = monitor["width"], monitor["height"]
                    if _PIL_OK:
                        pil_img = PIL.Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
                        buf = io.BytesIO()
                        pil_img.save(buf, format="JPEG", quality=85)
                        return buf.getvalue(), w, h
            except Exception as e:
                print(f"[GhostVision] MSS grab fallback: {e}")

        # B. Fallback to PIL ImageGrab
        if _PIL_OK:
            try:
                pil_img = ImageGrab.grab()
                w, h = pil_img.size
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=85)
                return buf.getvalue(), w, h
            except Exception as e:
                print(f"[GhostVision] ImageGrab fallback: {e}")

        # C. Fallback to pyautogui screenshot
        if _PYAUTOGUI_OK:
            try:
                img = pyautogui.screenshot()
                w, h = img.size
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                return buf.getvalue(), w, h
            except Exception as e:
                print(f"[GhostVision] PyAutoGUI grab failed: {e}")

        return None, 0, 0

    def locate_element(self, description: str) -> Optional[Tuple[int, int, str]]:
        """
        Locates UI element on screen using Gemini Vision.
        Returns (x, y, label) if found, else None.
        """
        img_bytes, screen_w, screen_h = self.capture_screen_image()
        if not img_bytes or screen_w <= 0 or screen_h <= 0:
            print("[GhostVision] Screen capture failed")
            return None

        clean_desc = (description or "").strip()
        if not clean_desc:
            return None

        api_key = self._get_api_key()
        if not api_key:
            print("[GhostVision] Missing Gemini API key")
            return self._locate_fallback(clean_desc, img_bytes, screen_w, screen_h)

        prompt = (
            f"You are an expert autonomous GUI vision agent for desktop computer control.\n"
            f"Screen Resolution: {screen_w} pixels wide by {screen_h} pixels high.\n\n"
            f"TASK: Locate the user-requested UI element: '{clean_desc}'.\n"
            f"This could be a button, icon, link, video thumbnail, play button, input field, tab, or text.\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Identify the exact center pixel coordinates (x, y) where the user would click.\n"
            f"2. Ensure 0 <= x <= {screen_w} and 0 <= y <= {screen_h}.\n"
            f"3. Return ONLY a valid JSON object in this exact format:\n"
            f'{{"found": true, "x": <integer_x>, "y": <integer_y>, "label": "<short_name>"}}\n'
            f"4. If the element is genuinely NOT visible anywhere on screen, return:\n"
            f'{{"found": false, "reason": "not_visible"}}\n\n'
            f"Return JSON ONLY. No markdown fences. No extra text."
        )

        try:
            client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                    prompt,
                ],
                config={"temperature": 0.1},
            )

            text_resp = ""
            for candidate in getattr(response, "candidates", []) or []:
                for part in getattr(getattr(candidate, "content", None), "parts", []) or []:
                    part_text = getattr(part, "text", "")
                    if part_text:
                        text_resp += part_text

            text_resp = text_resp.strip()
            print(f"[GhostVision] Gemini Vision response: {text_resp}")

            # Parse JSON
            clean_json = re.sub(r"^```(json)?", "", text_resp, flags=re.IGNORECASE).rstrip("`").strip()
            data = json.loads(clean_json)

            if data.get("found") and "x" in data and "y" in data:
                x = int(data["x"])
                y = int(data["y"])
                lbl = data.get("label") or clean_desc
                # Bounds check
                x = max(5, min(screen_w - 5, x))
                y = max(5, min(screen_h - 5, y))
                return x, y, lbl

        except Exception as e:
            print(f"[GhostVision] Gemini locate error: {e}")

        # Fallback to OpenRouter vision if Gemini fails
        return self._locate_fallback(clean_desc, img_bytes, screen_w, screen_h)

    def _locate_fallback(self, description: str, img_bytes: bytes, w: int, h: int) -> Optional[Tuple[int, int, str]]:
        """Fallback to OpenRouter vision if cloud Gemini is throttled."""
        try:
            from llm_client import client as llm
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            prompt = (
                f"Screen size {w}x{h}. Find the UI element: '{description}'. "
                f"Reply ONLY with center coordinates as: x,y (example: 540,320) or NOT_FOUND"
            )
            res = llm.vision(prompt, image_b64=b64, mime="image/jpeg")
            if "NOT_FOUND" not in (res or "").upper():
                match = re.search(r"(\d+)\s*,\s*(\d+)", res)
                if match:
                    x = int(match.group(1))
                    y = int(match.group(2))
                    return x, y, description
        except Exception as e:
            print(f"[GhostVision] Fallback locate error: {e}")
        return None

    def execute_ghost_click(
        self,
        description: str,
        click_type: str = "single",
        speak_cb: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, str]:
        """
        Full Autonomous Ghost Click Routine:
        1. Analyzes screen & computes exact pixel coordinates
        2. Spawns holographic neon target reticle overlay at target
        3. Smoothly glides mouse cursor to target
        4. Triggers click burst & executes mouse click
        5. Reports success
        """
        if not _PYAUTOGUI_OK:
            return False, "PyAutoGUI is not available on this system."

        clean_desc = (description or "").strip()
        if not clean_desc:
            return False, "Enna click pannanum nu sollala nanba."

        coords = self.locate_element(clean_desc)
        if not coords:
            return False, f"'{clean_desc}' screen-la kandupidikka mudiyala nanba."

        target_x, target_y, target_label = coords
        print(f"[GhostVision] Target locked at ({target_x}, {target_y}): '{target_label}'")

        # 1. Play sci-fi lock sound effect
        try:
            from sound_manager import sound_mgr
            sound_mgr.play_sfx("telemetry_chirp")
        except Exception:
            pass

        # 2. Spawn Holographic Target Reticle
        _spawn_reticle_overlay(target_x, target_y, target_label)
        time.sleep(0.12)

        # 3. Smooth human-like cursor glide to target
        try:
            pyautogui.moveTo(
                target_x,
                target_y,
                duration=0.32,
                tween=pyautogui.easeOutQuad,
            )
        except Exception:
            pyautogui.moveTo(target_x, target_y)

        # 4. Small realistic hover pause before click
        time.sleep(0.08)

        # 5. Execute Mouse Click
        try:
            if click_type == "double":
                pyautogui.doubleClick(target_x, target_y)
                action_str = "Double click"
            elif click_type == "right":
                pyautogui.rightClick(target_x, target_y)
                action_str = "Right click"
            else:
                pyautogui.click(target_x, target_y)
                action_str = "Click"
        except Exception as e:
            return False, f"Click execution error: {e}"

        # 6. Success message
        reply = f"Target locked! '{target_label}' {action_str.lower()} panniyachu nanba."
        return True, reply


# Global singleton
ghost_vision = GhostVisionEngine()
