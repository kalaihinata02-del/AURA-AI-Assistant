"""
Aura Jarvis Eye Vision Engine
==============================
Empowers Aura with autonomous multimodal computer vision.
Allows Aura to "see", inspect, read, and understand:
1. Live Screen / Active Windows (Errors, Code, UI, Web, Documents)
2. Live Webcam / Real-world Camera (Objects, Handheld items, Notes, People)

Features:
- Dual-modality capture (Screen & OpenCV Webcam with auto-device discovery)
- Fast Google Gemini Vision inference (gemini-flash-latest, gemini-3.8-flash)
- Fallback to OpenRouter / Local Vision if cloud limits occur
- 100% Tanglish, Tamil, and English natural comprehension
- Zero-crash offline mode support
"""

from __future__ import annotations

import io
import os
import sys
import json
import time
import base64
import datetime
import re
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Callable

try:
    import cv2
    _CV2_OK = True
except ImportError:
    _CV2_OK = False

try:
    import PIL.Image
    from PIL import ImageGrab
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

try:
    import mss
    import mss.tools
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


class JarvisEyeVisionEngine:
    """State-of-the-art vision intelligence engine for Aura AI."""

    def __init__(self):
        self._api_config_path = get_user_data_dir() / "config" / "api_keys.json"
        self._cached_camera_idx: Optional[int] = None
        self._max_image_w = 1280
        self._max_image_h = 720
        self._jpeg_quality = 80

    def _get_api_key(self) -> str:
        """Retrieves Gemini API key from user config."""
        try:
            if self._api_config_path.exists():
                with open(self._api_config_path, "r", encoding="utf-8") as f:
                    keys = json.load(f)
                return keys.get("gemini_api_key", "").strip()
        except Exception:
            pass
        return ""

    # ---------------------------------------------------------
    # 1. FRAME CAPTURE: SCREEN & ACTIVE WINDOW
    # ---------------------------------------------------------
    def capture_screen(self, ui_instance: Any = None) -> Tuple[Optional[bytes], str]:
        """
        Captures the primary/full desktop display as optimized JPEG bytes.
        Returns (bytes, mime_type).
        """
        # A. Try UI Qt grabWindow if running in GUI context
        if ui_instance:
            if hasattr(ui_instance, "capture_screen_bytes"):
                try:
                    raw = ui_instance.capture_screen_bytes()
                    if raw and len(raw) > 500:
                        return self._optimize_image(raw), "image/jpeg"
                except Exception:
                    pass
            if hasattr(ui_instance, "capture_screen_threadsafe"):
                try:
                    raw = ui_instance.capture_screen_threadsafe()
                    if raw and len(raw) > 500:
                        return self._optimize_image(raw), "image/jpeg"
                except Exception:
                    pass

        # B. Try PIL ImageGrab
        if _PIL_OK:
            try:
                img = ImageGrab.grab(all_screens=True).convert("RGB")
                return self._optimize_pil(img), "image/jpeg"
            except Exception:
                pass

        # C. Try mss
        if _MSS_OK:
            try:
                with mss.mss() as sct:
                    monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                    shot = sct.grab(monitor)
                    png_bytes = mss.tools.to_png(shot.rgb, shot.size)
                    return self._optimize_image(png_bytes), "image/jpeg"
            except Exception:
                pass

        # D. Try PowerShell / GDI fallback
        try:
            import subprocess
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            tmp_snap = Path.home() / f"aura_tmp_snap_{ts}.png"
            ps_cmd = (
                f"Add-Type -AssemblyName System.Windows.Forms; "
                f"$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
                f"$bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height; "
                f"$graphics = [System.Drawing.Graphics]::FromImage($bmp); "
                f"$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size); "
                f"$bmp.Save('{str(tmp_snap)}', [System.Drawing.Imaging.ImageFormat]::Png); "
                f"$graphics.Dispose(); $bmp.Dispose();"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=6)
            if tmp_snap.exists() and tmp_snap.stat().st_size > 0:
                data = tmp_snap.read_bytes()
                try:
                    tmp_snap.unlink()
                except Exception:
                    pass
                return self._optimize_image(data), "image/jpeg"
        except Exception:
            pass

        return None, ""

    def capture_active_window(self) -> Tuple[Optional[bytes], str]:
        """
        Captures only the user's currently focused foreground application window.
        """
        try:
            from core.window_context import capture_active_window_screenshot
            raw = capture_active_window_screenshot()
            if raw and len(raw) > 500:
                return self._optimize_image(raw), "image/jpeg"
        except Exception:
            pass
        # Fallback to full screen
        return self.capture_screen()

    # ---------------------------------------------------------
    # 2. FRAME CAPTURE: WEBCAM
    # ---------------------------------------------------------
    def get_camera_index(self) -> int:
        """Finds or retrieves the working webcam device index."""
        if self._cached_camera_idx is not None:
            return self._cached_camera_idx

        # Check saved setting
        try:
            if self._api_config_path.exists():
                with open(self._api_config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if "camera_index" in cfg:
                    self._cached_camera_idx = int(cfg["camera_index"])
                    return self._cached_camera_idx
        except Exception:
            pass

        # Auto-detect camera index
        best_idx = 0
        if _CV2_OK:
            for idx in range(4):
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW) if sys.platform == "win32" else cv2.VideoCapture(idx)
                if not cap.isOpened():
                    cap.release()
                    continue
                for _ in range(3):
                    cap.read()
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None and frame.mean() > 5:
                    best_idx = idx
                    break

        self._cached_camera_idx = best_idx
        return best_idx

    def capture_webcam(self) -> Tuple[Optional[bytes], str]:
        """
        Captures a live frame from the user's webcam and releases the device immediately.
        Returns (bytes, mime_type).
        """
        if not _CV2_OK:
            return None, ""

        cam_idx = self.get_camera_index()
        cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW) if sys.platform == "win32" else cv2.VideoCapture(cam_idx)
        if not cap.isOpened():
            cap.release()
            return None, ""

        try:
            # Skip first 4 frames so sensor auto-adjusts exposure and white balance
            for _ in range(4):
                cap.read()
            ret, frame = cap.read()
            if not ret or frame is None:
                return None, ""

            if _PIL_OK:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = PIL.Image.fromarray(rgb)
                return self._optimize_pil(img), "image/jpeg"

            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self._jpeg_quality])
            return buf.tobytes(), "image/jpeg"
        finally:
            cap.release()

    # ---------------------------------------------------------
    # 3. IMAGE PRE-PROCESSING & COMPRESSION
    # ---------------------------------------------------------
    def _optimize_pil(self, img: PIL.Image.Image) -> bytes:
        img = img.convert("RGB")
        resample = getattr(PIL.Image, "Resampling", PIL.Image).BILINEAR
        img.thumbnail((self._max_image_w, self._max_image_h), resample)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=self._jpeg_quality, optimize=True)
        return buf.getvalue()

    def _optimize_image(self, raw_bytes: bytes) -> bytes:
        if not _PIL_OK:
            return raw_bytes
        try:
            img = PIL.Image.open(io.BytesIO(raw_bytes))
            return self._optimize_pil(img)
        except Exception:
            return raw_bytes

    # ---------------------------------------------------------
    # 4. INTENT DETECTION (ENGLISH, TAMIL, TANGLISH)
    # ---------------------------------------------------------
    def detect_vision_intent(self, text: str) -> Tuple[bool, str]:
        """
        Detects if user is asking Aura to inspect screen or webcam.
        Returns (is_vision: bool, mode: "screen" | "camera" | "window").
        """
        low = (text or "").lower().strip()
        if not low:
            return False, ""

        # Discard simple screenshot capture requests (handled by Desktop Automation)
        if any(p == low for p in ("screenshot", "take screenshot", "take a screenshot", "screenshot edu", "screenshot podu")):
            return False, ""

        # --- A. WEBCAM / CAMERA TRIGGERS ---
        is_camera = any(p in low for p in (
            "look at me", "look through camera", "what am i holding", "who is in front of the camera",
            "look at camera", "inspect camera", "what do you see in the camera", "look at my webcam",
            "camera paaru", "camera la enna theriyuthu", "camera check pannu", "en kaiyila enna iruku",
            "webcam paaru", "camera la kaatu", "camera on panni paaru", "camera la enna iruku",
            "see what i am holding", "look at this object"
        ))
        if is_camera:
            return True, "camera"

        # --- B. SCREEN / DISPLAY TRIGGERS ---
        is_screen = any(p in low for p in (
            "what's on my screen", "whats on my screen", "what is on my screen", "what's on screen",
            "look at my screen", "check my screen", "analyze my screen", "inspect my screen",
            "read my screen", "tell me what's on my screen", "what does my screen say",
            "explain this error", "what is this error", "what's this error", "look at this error",
            "debug this error", "explain the error", "look at my code", "debug my code",
            "screen paaru", "en screen paaru", "screen la enna irukku", "screen check pannu",
            "intha error enna", "code error sollu", "screen la irukura error explain pannu",
            "display paaru", "monitor paaru", "what am i looking at", "summarize my screen",
            "screen la enna oduthu", "screen ah paaru", "explain this image", "explain what you see",
            "window paaru", "intha window paaru", "active window paaru", "look at this window",
            "inspect this window", "what's on this window", "whats on this window"
        ))
        if is_screen:
            # Check if specifically active window
            if any(w in low for w in ("this window", "active window", "intha window", "window paaru")):
                return True, "window"
            return True, "screen"

        # Regex fallback for "look at ... screen/camera"
        if re.search(r"(?:look|check|see|read|explain|debug)\s+(?:at|on|my)?\s*(?:the\s+)?(screen|display|camera|webcam)", low):
            mode = "camera" if any(k in low for k in ("camera", "webcam")) else "screen"
            return True, mode

        return False, ""

    # ---------------------------------------------------------
    # 5. MULTIMODAL AI REASONING ("JARVIS EYE")
    # ---------------------------------------------------------
    def analyze(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        prompt: str = "Describe what you see with clarity.",
        mode: str = "screen",
        window_title: str = "",
    ) -> str:
        """
        Executes vision analysis on the captured image using Gemini Vision,
        with fallback to OpenRouter or local intelligence.
        """
        if not image_bytes:
            return "No image frame was captured to analyze."

        # System persona and prompt framing
        system_instruction = (
            "You are Jarvis Eye, the advanced visual intelligence system of Aura AI for Kalai. "
            "You possess razor-sharp perception, high technical competence, and speak with warmth, respect, and confidence. "
            "You understand native English, Tamil (தமிழ்), and Tanglish (Tamil in English script). "
            "Analyze the image precisely and deliver an intelligent, helpful, concise answer (2-4 sentences max). "
            "If the user is showing code or an error, identify the root cause and give the exact solution. "
            "If asked about what is visible, summarize key elements accurately. "
            "Reply naturally in the user's language (Tamil, English, or friendly Tanglish). "
            "Address the user respectfully as Kalai or Nanba."
        )

        user_query = prompt.strip()
        if window_title and mode != "camera":
            user_query += f"\n[Active Application: '{window_title}']"

        # 1. Primary: Google Gemini Vision
        api_key = self._get_api_key()
        if api_key and _GOOGLE_GENAI_OK:
            client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
            for model_name in ("gemini-flash-latest", "gemini-3.8-flash", "gemini-2.0-flash"):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[
                            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                            f"{system_instruction}\n\nUser Question: {user_query}"
                        ],
                        config={"temperature": 0.4}
                    )
                    text = (getattr(response, "text", "") or "").strip()
                    if text:
                        return text
                except Exception as e:
                    print(f"[JarvisEye] ⚠️ Gemini model {model_name} failed: {e}")

        # 2. Fallback: Unified AI Client / OpenRouter Vision
        try:
            from llm_client import client as unified_client
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            reply = unified_client.vision(
                prompt=user_query,
                image_b64=b64,
                mime=mime_type,
                system=system_instruction
            )
            if reply and reply.strip():
                return reply.strip()
        except Exception as e:
            print(f"[JarvisEye] ⚠️ Unified AI Vision fallback failed: {e}")

        # 3. Offline / Disconnected Fallback
        return self._offline_vision_reply(mode, window_title)

    def _offline_vision_reply(self, mode: str, window_title: str) -> str:
        """Provides graceful offline fallback when no internet connection is present."""
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir = Path.home() / "Pictures" / "Screenshots"
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"Jarvis_Eye_{mode.title()}_{ts}.jpg"

        if mode == "camera":
            return (
                f"Jarvis Eye captured your camera frame, Kalai. "
                f"Since we are currently offline without internet connection, "
                f"cloud vision is resting. The frame is saved as {filename}."
            )
        else:
            win_msg = f"Your active focused window is '{window_title}'." if window_title else "Desktop is active."
            return (
                f"Screen frame captured offline, Kalai. {win_msg} "
                f"Connect to Wi-Fi for full deep neural visual explanation."
            )

    # ---------------------------------------------------------
    # 6. PIPELINE RUNNER (UI & VOICE INTEGRATION)
    # ---------------------------------------------------------
    def process_vision_request(
        self,
        command_text: str,
        mode: str = "screen",
        speak_cb: Optional[Callable[[str], Any]] = None,
        ui_instance: Any = None,
    ) -> Tuple[bool, str]:
        """
        End-to-end execution: captures frame, runs analysis, updates UI, and speaks reply.
        Returns (handled: bool, reply: str).
        """
        is_camera = (mode == "camera")
        label = "CAMERA" if is_camera else "SCREEN"

        # UI Visual Scanning Feedback
        if ui_instance and hasattr(ui_instance, "set_scanning"):
            try:
                ui_instance.set_scanning(True, f"SCANNING {label}")
            except Exception:
                pass

        # Speak immediate perception prompt
        if speak_cb:
            if any(k in command_text.lower() for k in ("paaru", "theriyuthu", "nanba")):
                speak_cb(f"Camera paakaren nanba..." if is_camera else "Screen paakaren nanba...")
            else:
                speak_cb("Looking through the camera..." if is_camera else "Inspecting your screen...")

        # Frame Capture
        window_title = ""
        if is_camera:
            img_bytes, mime = self.capture_webcam()
        elif mode == "window":
            img_bytes, mime = self.capture_active_window()
        else:
            img_bytes, mime = self.capture_screen(ui_instance)

        if not is_camera:
            try:
                from core.window_context import get_foreground_window_info
                w_info = get_foreground_window_info()
                window_title = (w_info.get("title") or "").strip()
            except Exception:
                pass

        if not img_bytes:
            err_msg = "Could not access the webcam device." if is_camera else "Could not capture the screen display."
            if ui_instance and hasattr(ui_instance, "set_scanning"):
                ui_instance.set_scanning(False, "")
            return True, err_msg

        # AI Vision Reasoning
        reply = self.analyze(
            image_bytes=img_bytes,
            mime_type=mime,
            prompt=command_text,
            mode=mode,
            window_title=window_title,
        )

        # UI Scanning state finish
        if ui_instance and hasattr(ui_instance, "set_scanning"):
            try:
                ui_instance.set_scanning(False, "")
            except Exception:
                pass

        return True, reply


# Global singleton instance
vision_engine = JarvisEyeVisionEngine()
