"""
Aura 100% Offline AI Fallback Engine
====================================
Ensures Aura continues operating seamlessly even when the internet is completely disconnected.
Features:
- Fast network connectivity detection (cached with TTL)
- Local LLM bridge (Ollama HTTP API if local model is active)
- Built-in Natural Language Intent Parser & Reasoner (English, Tamil, Tanglish)
- Offline System Operations (Apps, Volume, Battery, RAM, CPU, Brightness, Time, Date, Math)
- Conversational Offline Brain with friendly Tanglish/English identity for Kalai
"""

from __future__ import annotations

import re
import os
import sys
import time
import socket
import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

try:
    import psutil
    _PSUTIL_OK = True
except ImportError:
    _PSUTIL_OK = False


class OfflineAIEngine:
    """Aura's local autonomous intelligence engine when disconnected from cloud APIs."""

    def __init__(self):
        self._last_conn_check = 0.0
        self._cached_conn_status = True
        self._conn_cache_ttl = 4.0  # Cache connectivity status for 4 seconds
        self._ollama_url = "http://localhost:11434"

    def is_connected(self) -> bool:
        """Fast check to verify if the internet is accessible."""
        now = time.time()
        if (now - self._last_conn_check) < self._conn_cache_ttl:
            return self._cached_conn_status

        self._last_conn_check = now
        try:
            # Fast socket connect to Cloudflare / Google public DNS (port 53)
            with socket.create_connection(("1.1.1.1", 53), timeout=0.8):
                self._cached_conn_status = True
                return True
        except Exception:
            try:
                with socket.create_connection(("8.8.8.8", 53), timeout=0.8):
                    self._cached_conn_status = True
                    return True
            except Exception:
                self._cached_conn_status = False
                return False

    def query_ollama(self, prompt: str, model: str = "qwen2.5:1.5b") -> Optional[str]:
        """Queries local Ollama instance if active."""
        try:
            import urllib.request
            import json

            url = f"{self._ollama_url}/api/generate"
            payload = json.dumps({
                "model": model,
                "prompt": f"You are Aura, personal AI assistant for Kalai. Answer briefly in friendly English or Tanglish.\nUser: {prompt}\nAura:",
                "stream": False
            }).encode("utf-8")

            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                reply = data.get("response", "").strip()
                if reply:
                    return reply
        except Exception:
            pass
        return None

    def process_offline_request(self, text: str) -> Tuple[bool, str]:
        """
        Processes a natural language request entirely offline.
        Returns (handled: bool, response_text: str).
        """
        raw = (text or "").strip()
        low = raw.lower()
        if not low:
            return True, "Solunga Kalai, I'm listening."

        # 1. Try Local Ollama if available
        ollama_reply = self.query_ollama(raw)
        if ollama_reply:
            return True, ollama_reply

        # 2. Time & Date Queries
        if any(w in low for w in ("what time", "time enna", "neram enna", "current time", "time now")) or low == "time":
            now = datetime.datetime.now()
            time_str = now.strftime("%I:%M %p")
            return True, f"The current time is {time_str}, Kalai."

        if any(w in low for w in ("what date", "date enna", "innaiku date", "today date", "which day", "innaiku enna naal")) or low == "date":
            now = datetime.datetime.now()
            date_str = now.strftime("%A, %B %d, %Y")
            return True, f"Today is {date_str}, Kalai."

        # 3. Hardware & Battery
        if any(w in low for w in ("battery", "charging", "battery percent", "charge status", "battery status")):
            if _PSUTIL_OK:
                b = psutil.sensors_battery()
                if b:
                    plugged = "plugged in and charging" if b.power_plugged else "on battery power"
                    return True, f"Battery is at {b.percent}%, currently {plugged}."
            return True, "Battery telemetry is currently unavailable on this device."

        # 4. RAM / CPU Usage
        if any(w in low for w in ("ram", "memory usage", "ram usage", "how much ram", "memory percent")):
            if _PSUTIL_OK:
                v = psutil.virtual_memory()
                return True, f"System RAM usage is at {v.percent}%. {round(v.used / (1024**3), 1)} GB of {round(v.total / (1024**3), 1)} GB in use."
            return True, "RAM telemetry unavailable."

        if any(w in low for w in ("cpu", "cpu usage", "processor", "cpu percent")):
            if _PSUTIL_OK:
                c = psutil.cpu_percent(interval=0.1)
                return True, f"CPU utilization is currently at {c}%."
            return True, "CPU telemetry unavailable."

        # 5. Offline Math Calculations (e.g. "what is 25 * 40", "calculate 1500 / 3", "50 + 20")
        math_match = re.search(r"(\bcalculate\b|\bwhat is\b|\bmath\b)?\s*([0-9\.\s\+\-\*\/\%\(\)\^]+)", low)
        if math_match:
            expr = math_match.group(2).strip()
            # Only evaluate if it contains operators and digits
            if any(op in expr for op in ("+", "-", "*", "/", "%")) and any(ch.isdigit() for ch in expr):
                try:
                    # Safe arithmetic evaluation
                    clean_expr = re.sub(r"[^0-9\+\-\*\/\%\.\(\)\s]", "", expr)
                    val = eval(clean_expr, {"__builtins__": None}, {})
                    return True, f"The answer to {clean_expr} is {val}."
                except Exception:
                    pass

        # 6. Offline Conversational & Identity (English & Tanglish)
        if any(w in low for w in ("who are you", "un name enna", "unoda per enna", "un per enna", "yaar nee")):
            return True, "I am Aura, your personal AI assistant created for Kalai. Operating seamlessly in 100% Offline Mode."

        if any(w in low for w in ("hi", "hello", "hey", "vanakkam", "mapla", "nanba")):
            return True, "Vanakkam Kalai! Offline mode active. All PC controls and tools are ready to execute."

        if any(w in low for w in ("how are you", "epudi iruka", "nalla irukiya", "how's it going")):
            return True, "I am doing great, Kalai! Systems are fully operational and ready even without an internet connection."

        if any(w in low for w in ("offline mode", "internet status", "wifi status", "internet iruka", "am i offline")):
            conn = self.is_connected()
            if conn:
                return True, "Internet is online and cloud neural models are fully active."
            return True, "Internet connection is offline. Aura Local Engine is active to manage your computer."

        if any(w in low for w in ("what can you do offline", "offline features", "offline la enna panna mudiyum", "help offline")):
            return True, (
                "In Offline Mode, I can autonomously automate your desktop (minimize windows, take screenshots, "
                "type notes, lock PC, control media, open folders), launch apps, adjust volume & brightness, "
                "check battery & RAM, calculate math, and tell time and dates."
            )

        # 7. Check if it's an app launcher or local PC command
        from actions.open_app import _normalize, _APP_ALIASES
        norm = _normalize(low)
        if norm in _APP_ALIASES or any(k in low for k in _APP_ALIASES):
            return False, ""  # Let local PC command router handle opening the app

        # 8. Autonomous Desktop Automation (100% works offline)
        try:
            from core.desktop_automation import desktop_automation
            handled_auto, auto_reply = desktop_automation.handle_command(raw)
            if handled_auto and auto_reply:
                return True, auto_reply
        except Exception:
            pass

        # 9. Jarvis Eye Vision (Screen & Webcam Offline Graceful Handling)
        try:
            from core.vision_engine import vision_engine
            is_v, v_mode = vision_engine.detect_vision_intent(raw)
            if is_v:
                ok_v, v_reply = vision_engine.process_vision_request(raw, mode=v_mode)
                if ok_v and v_reply:
                    return True, v_reply
        except Exception:
            pass

        # Default friendly offline fallback
        return True, "I am operating in Offline Mode, Kalai. All desktop automation, PC apps, volume, battery, and diagnostics are fully available."


# Global singleton instance
offline_engine = OfflineAIEngine()
