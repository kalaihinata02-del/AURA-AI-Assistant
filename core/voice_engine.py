"""
Aura Cinematic Voice Engine
===========================
Next-generation intelligent multilingual speech synthesis.
Automatically routes between:
- Cinematic British JARVIS Neural Voice (en-GB-RyanNeural) for English
- Rich Authoritative Tamil Neural Voice (ta-IN-ValluvarNeural) for Tamil
- Expressive Native Inflection (ta-IN-ValluvarNeural / en-IN-PrabhatNeural) for Tanglish

Features:
- Real-time automatic language & script detection
- Zero-latency Windows MCI audio playback
- Clean speech pre-processing (removes markdown fences, urls, emojis, technical hashes)
- Configurable voice personalities via config/voice_settings.json
"""

from __future__ import annotations

import os
import re
import sys
import json
import time
import uuid
import ctypes
import tempfile
import threading
from pathlib import Path
from typing import Optional, Callable

from core.user_paths import get_user_data_dir


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
VOICE_CONFIG_FILE = BASE_DIR / "config" / "voice_settings.json"

DEFAULT_VOICE_CONFIG = {
    "english_voice":  "en-IN-PrabhatNeural",   # Indian English — clear, natural accent
    "tamil_voice":    "ta-IN-ValluvarNeural",   # Pure Tamil Unicode script
    "tanglish_voice": "en-IN-PrabhatNeural",   # Indian English voice pronounces Tanglish + English smoothly without glitches
    "gemini_live_voice": "Charon",
    "speech_rate": "+0%",                       # Natural pace — no distortion
    "pitch": "+0Hz"
}


_TANGLISH_MARKERS = {
    "nanba", "vanakkam", "pannu", "pannidu", "panren", "pandren", "irukku", "iruken",
    "paaru", "koodu", "kudu", "podu", "sollu", "solra", "enna", "aachu",
    "kootu", "kora", "kammi", "mudinjathu", "seri", "kandippa", "thala",
    "romba", "nalla", "epudi", "eppadi", "thambi", "bro", "mapla", "machan",
    "pora", "varan", "theriyum", "puriyala", "kekkuthu", "kekutha", "illai",
    "aama", "venum", "venda", "panna", "edukku", "edu"
}


class CinematicVoiceEngine:
    """Intelligent Neural Speech Engine with real-time Tamil, Tanglish, and JARVIS English routing."""

    def __init__(self):
        self._lock = threading.Lock()
        self._current_player_alias: Optional[str] = None
        self._current_audio_path: Optional[str] = None
        self._config = dict(DEFAULT_VOICE_CONFIG)
        # Pre-synthesis cache: text → audio_path (synthesised ahead of playback)
        self._presynth_cache: dict[str, str] = {}
        self._presynth_lock = threading.Lock()
        self.load_config()

    def load_config(self):
        try:
            if VOICE_CONFIG_FILE.exists():
                # Try utf-8-sig first (handles BOM from PowerShell), then plain utf-8
                try:
                    text = VOICE_CONFIG_FILE.read_text(encoding="utf-8-sig")
                except Exception:
                    text = VOICE_CONFIG_FILE.read_text(encoding="utf-8")
                loaded = json.loads(text)
                self._config.update(loaded)
            else:
                self.save_config()
        except Exception as e:
            print(f"[VoiceEngine] Config load error: {e}")

    def save_config(self):
        try:
            VOICE_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(VOICE_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4)
        except Exception as e:
            print(f"[VoiceEngine] Config save error: {e}")

    @property
    def config(self) -> dict:
        return self._config

    def detect_voice(self, text: str) -> str:
        """
        Determines the optimal neural voice for the given text:
        - TAMIL (Tamil script) -> ta-IN-ValluvarNeural
        - TANGLISH (Tamil in English letters) -> en-IN-PrabhatNeural (speaks Indian phonetic words naturally)
        - ENGLISH (standard English) -> en-IN-PrabhatNeural
        """
        from core.language_detector import detect_language
        lang = detect_language(text)
        if lang == "TAMIL":
            return self._config.get("tamil_voice", "ta-IN-ValluvarNeural")
        elif lang == "TANGLISH":
            return self._config.get("tanglish_voice", "en-IN-PrabhatNeural")
        else:
            return self._config.get("english_voice", "en-IN-PrabhatNeural")

    def clean_text_for_speech(self, text: str) -> str:
        """Sanitizes text removing markdown, code fences, emojis, and enforces language purity."""
        if not text:
            return ""

        t = text.strip()
        # Remove URLs
        t = re.sub(r"https?://\S+", "link", t)
        # Remove code blocks
        t = re.sub(r"```[\s\S]*?```", "code block omitted", t)
        # Remove inline code
        t = re.sub(r"`([^`]+)`", r"\1", t)
        # Remove markdown bold/italics
        t = re.sub(r"[*_~]{1,3}", "", t)
        # Remove markdown headers (# Title)
        t = re.sub(r"^#+\s*", "", t, flags=re.MULTILINE)
        # Remove bullet points
        t = re.sub(r"^\s*[-*•]\s*", "", t, flags=re.MULTILINE)
        # Remove system logs prefix (e.g. "Aura:", "SYS:", "You:")
        t = re.sub(r"^(aura|sys|you|err):\s*", "", t, flags=re.IGNORECASE)

        # Enforce language purity
        from core.language_detector import detect_language, clean_and_enforce_output
        lang = detect_language(t)
        t = clean_and_enforce_output(t, lang)

        # Collapse excessive whitespace
        t = re.sub(r"\s+", " ", t).strip()
        return t


    def _cleanup_audio(self):
        with self._lock:
            if self._current_player_alias:
                try:
                    ctypes.windll.winmm.mciSendStringW(f"stop {self._current_player_alias}", None, 0, None)
                    ctypes.windll.winmm.mciSendStringW(f"close {self._current_player_alias}", None, 0, None)
                except Exception:
                    pass
                self._current_player_alias = None

            if self._current_audio_path:
                try:
                    if os.path.exists(self._current_audio_path):
                        os.remove(self._current_audio_path)
                except Exception:
                    pass
                self._current_audio_path = None

    def stop(self):
        """Immediately interrupts any playing voice."""
        self._cleanup_audio()

    def presynth(self, text: str):
        """
        Pre-synthesise audio in background while AI is thinking.
        Call this as soon as you have the reply text — by the time
        speak() is called, audio will already be ready (near-zero wait).
        """
        cleaned = self.clean_text_for_speech(text)
        if not cleaned:
            return

        def _do_presynth():
            try:
                import edge_tts, asyncio
                chosen_voice = self.detect_voice(cleaned)
                rate  = self._config.get("speech_rate", "+0%")
                pitch = self._config.get("pitch", "+0Hz")
                audio_path = os.path.join(tempfile.gettempdir(), f"aura_pre_{uuid.uuid4().hex}.mp3")

                async def _synth():
                    comm = edge_tts.Communicate(cleaned, voice=chosen_voice, rate=rate, pitch=pitch)
                    await comm.save(audio_path)

                try:
                    asyncio.run(_synth())
                except Exception:
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(_synth())
                    loop.close()

                with self._presynth_lock:
                    self._presynth_cache[cleaned] = audio_path
            except Exception as e:
                print(f"[VoiceEngine] Presynth failed: {e}")

        threading.Thread(target=_do_presynth, daemon=True, name="voice-presynth").start()

    def _speak_sapi5_offline(
        self,
        text: str,
        on_start: Optional[Callable[[], None]] = None,
        on_finish: Optional[Callable[[], None]] = None,
    ) -> bool:
        """100% Offline Windows SAPI5 voice fallback when internet is down."""
        try:
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Rate = 1
            if on_start:
                try:
                    on_start()
                except Exception:
                    pass
            speaker.Speak(text)
            return True
        except Exception as e:
            print(f"[VoiceEngine] SAPI5 offline speech failed: {e}")
            return False
        finally:
            if on_finish:
                try:
                    on_finish()
                except Exception:
                    pass

    def speak(
        self,
        text: str,
        on_start: Optional[Callable[[], None]] = None,
        on_finish: Optional[Callable[[], None]] = None,
    ) -> bool:
        """
        Synthesizes and plays audio with lowest possible latency.
        Uses edge-tts streaming → pygame playback for best quality & speed.
        Falls back to SAPI5 if offline.
        """
        cleaned = self.clean_text_for_speech(text)
        if not cleaned:
            return False

        try:
            import edge_tts
        except ImportError:
            print("[VoiceEngine] edge_tts not found — using offline SAPI5")
            return self._speak_sapi5_offline(cleaned, on_start, on_finish)

        self._cleanup_audio()

        chosen_voice = self.detect_voice(cleaned)
        rate  = self._config.get("speech_rate", "+0%")
        pitch = self._config.get("pitch", "+0Hz")

        # ── Step 1: Check pre-synthesis cache (instant if pre-buffered!) ──
        audio_path = None
        with self._presynth_lock:
            cached = self._presynth_cache.pop(cleaned, None)
            if cached and os.path.exists(cached):
                audio_path = cached
                print("[VoiceEngine] ⚡ Cache hit — instant playback!")

        # ── Step 2: Synthesise if not cached ──────────────────────────────
        if not audio_path:
            audio_path = os.path.join(tempfile.gettempdir(), f"aura_voice_{uuid.uuid4().hex}.mp3")
            try:
                import asyncio

                async def _synthesise():
                    comm = edge_tts.Communicate(cleaned, voice=chosen_voice, rate=rate, pitch=pitch)
                    await comm.save(audio_path)

                try:
                    asyncio.run(_synthesise())
                except Exception:
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(_synthesise())
                    loop.close()
            except Exception as exc:
                print(f"[VoiceEngine] Neural TTS failed ({exc}) — SAPI5 fallback")
                return self._speak_sapi5_offline(cleaned, on_start, on_finish)

        # ── Step 2: Play with pygame (best quality, no codec issues) ──────
        if on_start:
            try:
                on_start()
            except Exception:
                pass

        played = False
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=512)
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                time.sleep(0.02)
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            played = True
        except Exception as pg_exc:
            print(f"[VoiceEngine] pygame playback failed ({pg_exc}) — MCI fallback")

        # ── Step 3: MCI fallback if pygame fails ──────────────────────────
        if not played:
            player_alias = f"aura_mci_{uuid.uuid4().hex}"
            try:
                with self._lock:
                    self._current_player_alias = player_alias
                    self._current_audio_path   = audio_path

                ctypes.windll.winmm.mciSendStringW(
                    f'open "{audio_path}" type mpegvideo alias {player_alias}',
                    None, 0, None
                )
                ctypes.windll.winmm.mciSendStringW(
                    f"play {player_alias} wait",
                    None, 0, None
                )
                played = True
            except Exception as mci_exc:
                print(f"[VoiceEngine] MCI playback failed: {mci_exc}")
                played = self._speak_sapi5_offline(cleaned)
            finally:
                self._cleanup_audio()

        # ── Cleanup ───────────────────────────────────────────────────────
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass

        if on_finish:
            try:
                on_finish()
            except Exception:
                pass

        return played

    def speak_async(
        self,
        text: str,
        on_start: Optional[Callable[[], None]] = None,
        on_finish: Optional[Callable[[], None]] = None,
    ) -> threading.Thread:
        """Starts voice synthesis & playback in a non-blocking daemon thread."""
        thread = threading.Thread(
            target=self.speak,
            args=(text, on_start, on_finish),
            name="aura-voice-playback",
            daemon=True
        )
        thread.start()
        return thread


# Singleton global instance
voice_engine = CinematicVoiceEngine()
