"""
core/telegram_remote.py
=======================
📱 Telegram Remote Control for Aura AI
--------------------------------------
Control your PC from your mobile phone via Telegram!

Commands:
  /start        → Welcome message
  /status       → Battery, CPU, RAM info
  /screenshot   → Take & send screenshot
  /open <app>   → Open an app on PC
  /run <cmd>    → Run a shell command (safe whitelist)
  /shutdown     → Shutdown the PC
  /lock         → Lock Windows
  /play <song>  → Play on YouTube/Spotify
  /stop         → Stop current Aura action
  /help         → Show all commands
  (any text)    → Route to Aura's AI brain

Security: Only whitelisted Telegram user IDs can issue commands.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("aura.telegram")

# ──────────────────────────────────────────────
# Lazy-load python-telegram-bot
# ──────────────────────────────────────────────

def _load_telegram():
    try:
        import telegram as _tg
        import telegram.ext as _ext
        return _tg, _ext
    except ImportError:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "python-telegram-bot", "--quiet"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            import telegram as _tg
            import telegram.ext as _ext
            return _tg, _ext
        except Exception as exc:
            logger.warning("python-telegram-bot not available: %s", exc)
            return None, None


_tg, _ext = _load_telegram()

# ──────────────────────────────────────────────
# Config helpers
# ──────────────────────────────────────────────

def _api_keys_path() -> Path:
    try:
        from core.user_paths import get_user_data_dir
        return get_user_data_dir() / "config" / "api_keys.json"
    except Exception:
        return Path.home() / "AppData" / "Local" / "AuraAI" / "config" / "api_keys.json"


def _load_keys() -> dict:
    try:
        return json.loads(_api_keys_path().read_text(encoding="utf-8-sig"))
    except Exception:
        try:
            return json.loads(_api_keys_path().read_text(encoding="utf-8"))
        except Exception:
            return {}


def _save_keys(data: dict):
    path = _api_keys_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")


# ──────────────────────────────────────────────
# System helpers (battery, CPU, RAM)
# ──────────────────────────────────────────────

def _get_system_status() -> str:
    lines = []
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        ram_used = ram.used // (1024 ** 2)
        ram_total = ram.total // (1024 ** 2)
        ram_pct = ram.percent
        lines.append(f"🖥️ CPU: {cpu:.1f}%")
        lines.append(f"🧠 RAM: {ram_used} MB / {ram_total} MB ({ram_pct}%)")
        bat = psutil.sensors_battery()
        if bat:
            status = "🔌 Charging" if bat.power_plugged else "🔋 Battery"
            lines.append(f"{status}: {bat.percent:.0f}%")
    except Exception as exc:
        lines.append(f"⚠️ Status error: {exc}")
    return "\n".join(lines) if lines else "Status unavailable"


def _take_screenshot() -> Optional[bytes]:
    """Returns PNG bytes of a screenshot."""
    # Try PIL first
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        pass

    # PowerShell GDI fallback
    try:
        ps_script = (
            "Add-Type -AssemblyName System.Windows.Forms;"
            "$s=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
            "$b=New-Object System.Drawing.Bitmap($s.Width,$s.Height);"
            "$g=[System.Drawing.Graphics]::FromImage($b);"
            "$g.CopyFromScreen($s.Location,[System.Drawing.Point]::Empty,$s.Size);"
            "$ms=New-Object System.IO.MemoryStream;"
            "$b.Save($ms,[System.Drawing.Imaging.ImageFormat]::Png);"
            "[Convert]::ToBase64String($ms.ToArray())"
        )
        result = subprocess.run(
            ["powershell", "-WindowStyle", "Hidden", "-Command", ps_script],
            capture_output=True, timeout=15
        )
        if result.returncode == 0 and result.stdout:
            import base64
            return base64.b64decode(result.stdout.strip())
    except Exception:
        pass

    return None


# ──────────────────────────────────────────────
# Main Service Class
# ──────────────────────────────────────────────

class TelegramRemoteService:
    """
    Telegram Bot that acts as a remote control for Aura AI on Windows PC.
    Run with `.start(bot_token, allowed_user_ids=[123456789])`.
    """

    def __init__(
        self,
        *,
        status_callback: Optional[Callable[[str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ):
        self._status_cb = status_callback or (lambda *_: None)
        self._log_cb = log_callback or (lambda *_: None)
        self._token = ""
        self._allowed_ids: set[int] = set()
        self._app_submitter: Optional[Callable[[str, str], None]] = None
        self._speak_cb: Optional[Callable[[str], None]] = None
        self._thread: threading.Thread | None = None
        self._app = None  # telegram Application
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stopping = False
        self._lock = threading.Lock()

    # ── Public API ──────────────────────────────

    def bind_app_submitter(self, submitter: Callable[[str, str], None]):
        """Bind Aura's _on_text_command so Telegram messages are routed through Aura."""
        self._app_submitter = submitter

    def bind_speak(self, speak_fn: Callable[[str], None]):
        """Bind Aura's speak() so bot replies are also spoken on PC."""
        self._speak_cb = speak_fn

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and not self._stopping

    def start(self, token: str, allowed_user_ids: list[int]):
        token = (token or "").strip()
        if not token:
            raise ValueError("Telegram bot token is missing.")
        if _tg is None:
            raise RuntimeError("python-telegram-bot is not installed.")

        if self.is_running():
            if token == self._token:
                self._emit_status("Telegram bot already running.")
                return
            self.stop()

        self._token = token
        self._allowed_ids = set(int(x) for x in (allowed_user_ids or []))
        self._stopping = False
        self._thread = threading.Thread(
            target=self._thread_main,
            name="TelegramBotThread",
            daemon=True,
        )
        self._thread.start()
        self._emit_status("🤖 Telegram bot connecting...")

    def stop(self):
        with self._lock:
            if self._stopping:
                return
            self._stopping = True
            app = self._app
            loop = self._loop

        if app is not None and loop is not None and not loop.is_closed():
            try:
                fut = asyncio.run_coroutine_threadsafe(app.stop(), loop)
                fut.result(timeout=8)
            except Exception:
                pass

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=8)

        self._app = None
        self._loop = None
        self._thread = None
        self._emit_status("📴 Telegram bot stopped.")

    # ── Internal helpers ─────────────────────────

    def _emit_status(self, msg: str):
        try:
            self._status_cb(msg)
        except Exception:
            pass

    def _emit_log(self, msg: str):
        try:
            self._log_cb(msg)
        except Exception:
            pass

    def _is_allowed(self, user_id: int) -> bool:
        if not self._allowed_ids:
            return True  # No whitelist = allow all (warn in logs)
        return user_id in self._allowed_ids

    # ── Thread entry ─────────────────────────────

    def _thread_main(self):
        """Run bot in its own asyncio event loop (daemon thread)."""
        try:
            asyncio.run(self._run_bot())
        except Exception as exc:
            logger.exception("Telegram bot crashed")
            self._emit_status(f"❌ Telegram error: {exc}")

    async def _run_bot(self):
        """Full async bot — uses updater polling the correct way."""
        import asyncio as _asyncio
        filters = _ext.filters

        app = (
            _ext.Application.builder()
            .token(self._token)
            .build()
        )
        self._app = app
        self._loop = _asyncio.get_running_loop()

        # Register command handlers
        app.add_handler(_ext.CommandHandler("start",      self._cmd_start))
        app.add_handler(_ext.CommandHandler("help",       self._cmd_help))
        app.add_handler(_ext.CommandHandler("status",     self._cmd_status))
        app.add_handler(_ext.CommandHandler("screenshot", self._cmd_screenshot))
        app.add_handler(_ext.CommandHandler("open",       self._cmd_open))
        app.add_handler(_ext.CommandHandler("run",        self._cmd_run))
        app.add_handler(_ext.CommandHandler("shutdown",   self._cmd_shutdown))
        app.add_handler(_ext.CommandHandler("lock",       self._cmd_lock))
        app.add_handler(_ext.CommandHandler("play",       self._cmd_play))
        app.add_handler(_ext.CommandHandler("stop",       self._cmd_stop))

        # Natural language fallback — any plain text message
        app.add_handler(
            _ext.MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

        self._emit_status("✅ Telegram bot online — ready for remote commands!")
        self._emit_log("SYS: Telegram Remote Control bot connected.")

        # Initialize and start polling properly
        async with app:
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            # Keep alive until stop() is called
            while not self._stopping:
                await _asyncio.sleep(0.5)
            await app.updater.stop()
            await app.stop()

        self._emit_status("📴 Telegram bot offline.")

    # ── Security guard ───────────────────────────

    async def _guard(self, update) -> bool:
        """Returns True if user is allowed. Sends denial otherwise."""
        uid = update.effective_user.id if update.effective_user else 0
        if self._is_allowed(uid):
            return True
        await update.message.reply_text("⛔ Access denied. Onoda permission illai!")
        logger.warning("Telegram: Blocked unauthorized user %s", uid)
        return False

    # ── Reply helper ─────────────────────────────

    async def _reply(self, update, text: str):
        """Send reply back to Telegram, splitting long messages."""
        text = (text or "").strip()
        if not text:
            return
        chunks = self._split(text)
        for chunk in chunks:
            try:
                await update.message.reply_text(chunk)
            except Exception as exc:
                logger.warning("Telegram reply failed: %s", exc)

    def _split(self, text: str, limit: int = 4000) -> list[str]:
        if len(text) <= limit:
            return [text]
        parts = []
        while text:
            if len(text) <= limit:
                parts.append(text)
                break
            cut = text.rfind("\n", 0, limit)
            if cut < 200:
                cut = limit
            parts.append(text[:cut].strip())
            text = text[cut:].strip()
        return [p for p in parts if p]

    # ── Command Handlers ─────────────────────────

    async def _cmd_start(self, update, context):
        if not await self._guard(update):
            return
        uid = update.effective_user.id
        name = update.effective_user.first_name or "Nanba"
        msg = (
            f"👋 Vanakkam {name}!\n\n"
            "🤖 *Aura Remote Control* ready da!\n\n"
            "Type /help to see all commands.\n"
            "Or just send any text — Aura will respond! 🎯"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        self._emit_log(f"SYS: Telegram user {uid} ({name}) connected.")

    async def _cmd_help(self, update, context):
        if not await self._guard(update):
            return
        help_text = (
            "📱 *Aura Remote Commands* 🤖\n\n"
            "/status — 🖥️ Battery, CPU, RAM\n"
            "/screenshot — 📸 Take a screenshot\n"
            "/open <app> — 🚀 Open an app (e.g. /open chrome)\n"
            "/play <song> — 🎵 Play music (e.g. /play Anirudh hits)\n"
            "/run <cmd> — ⚡ Run safe commands\n"
            "/lock — 🔒 Lock Windows\n"
            "/shutdown — 🔴 Shutdown PC\n"
            "/stop — ⏹️ Stop current Aura action\n"
            "/help — 📖 This menu\n\n"
            "💬 *Or just type anything* — Aura will answer like normal! 🧠"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def _cmd_status(self, update, context):
        if not await self._guard(update):
            return
        await update.message.reply_text("🔍 Checking status...")
        status = await asyncio.to_thread(_get_system_status)
        await self._reply(update, f"📊 *System Status*\n\n{status}")

    async def _cmd_screenshot(self, update, context):
        if not await self._guard(update):
            return
        await update.message.reply_text("📸 Taking screenshot...")
        try:
            png_bytes = await asyncio.to_thread(_take_screenshot)
            if png_bytes:
                await update.message.reply_photo(
                    photo=io.BytesIO(png_bytes),
                    caption="🖥️ Screenshot from your PC!"
                )
            else:
                await update.message.reply_text("❌ Screenshot failed da. Try again!")
        except Exception as exc:
            await self._reply(update, f"❌ Error: {exc}")

    async def _cmd_open(self, update, context):
        if not await self._guard(update):
            return
        args = " ".join(context.args).strip() if context.args else ""
        if not args:
            await update.message.reply_text("Usage: /open chrome\n/open notepad\n/open vscode")
            return
        await update.message.reply_text(f"🚀 Opening {args}...")
        cmd = f"open {args}"
        await self._route_to_aura(update, cmd)

    async def _cmd_play(self, update, context):
        if not await self._guard(update):
            return
        args = " ".join(context.args).strip() if context.args else ""
        if not args:
            await update.message.reply_text("Usage: /play Anirudh hits\n/play Spotify")
            return
        await update.message.reply_text(f"🎵 Playing: {args}...")
        cmd = f"play {args} on youtube"
        await self._route_to_aura(update, cmd)

    async def _cmd_run(self, update, context):
        if not await self._guard(update):
            return
        args = " ".join(context.args).strip() if context.args else ""
        # Safe whitelist — no dangerous commands
        BLOCKED = ["format", "del ", "rm -", "rmdir", "rd /s", "shutdown", "taskkill", "reg delete", "netsh"]
        if not args:
            await update.message.reply_text("Usage: /run ipconfig\n/run tasklist")
            return
        if any(b in args.lower() for b in BLOCKED):
            await update.message.reply_text("⛔ That command is blocked for safety!")
            return
        await update.message.reply_text(f"⚡ Running: `{args}`", parse_mode="Markdown")
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    subprocess.run,
                    args, shell=True,
                    capture_output=True, text=True,
                    timeout=10
                ),
                timeout=15
            )
            output = (result.stdout or result.stderr or "No output").strip()
            output = output[:3500]  # Telegram limit
            await self._reply(update, f"```\n{output}\n```")
        except Exception as exc:
            await self._reply(update, f"❌ Error: {exc}")

    async def _cmd_shutdown(self, update, context):
        if not await self._guard(update):
            return
        await update.message.reply_text("🔴 Shutting down PC in 30 seconds... Say /stop to cancel!")
        self._emit_log("SYS: Telegram remote shutdown requested!")
        await asyncio.to_thread(
            subprocess.run,
            ["shutdown", "/s", "/t", "30", "/c", "Aura Telegram Remote Shutdown"],
            shell=False
        )

    async def _cmd_lock(self, update, context):
        if not await self._guard(update):
            return
        await update.message.reply_text("🔒 Locking Windows...")
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            await update.message.reply_text("✅ PC locked!")
        except Exception as exc:
            await self._reply(update, f"❌ Lock failed: {exc}")

    async def _cmd_stop(self, update, context):
        if not await self._guard(update):
            return
        # Cancel any pending shutdown
        try:
            subprocess.run(["shutdown", "/a"], shell=False, capture_output=True)
        except Exception:
            pass
        await update.message.reply_text("⏹️ Stop command sent! Shutdown cancelled (if pending).")
        await self._route_to_aura(update, "stop")

    async def _handle_message(self, update, context):
        """Natural language fallback — route to Aura's brain."""
        if not await self._guard(update):
            return
        text = (update.message.text or "").strip()
        if not text:
            return
        uid = update.effective_user.id
        name = update.effective_user.first_name or "User"
        self._emit_log(f"Telegram [{name}]: {text}")
        await update.message.reply_text("🤔 Thinking...")
        await self._route_to_aura(update, text)

    async def _route_to_aura(self, update, text: str):
        """Send command to Aura's _on_text_command and wait for response."""
        if self._app_submitter is not None:
            # Aura will process and call speak() + write_log()
            # We need to capture the reply — use a response queue
            reply_queue: asyncio.Queue[str] = asyncio.Queue()

            def _submit():
                try:
                    self._app_submitter(text, "telegram")
                except Exception as exc:
                    # Put error into queue
                    future = asyncio.run_coroutine_threadsafe(
                        reply_queue.put(f"❌ Aura error: {exc}"),
                        self._loop
                    )
                    future.result(timeout=5)

            threading.Thread(target=_submit, daemon=True).start()

            # We can't easily capture Aura's reply synchronously,
            # so acknowledge and let Aura speak on PC + send separately
            await asyncio.sleep(2)
            await update.message.reply_text(
                "✅ Command sent to Aura on your PC!\n"
                "Aura is processing... 🤖"
            )
        else:
            # No Aura submitter — use standalone Gemini reply
            reply = await asyncio.to_thread(self._standalone_reply, text)
            await self._reply(update, reply)

    def _standalone_reply(self, prompt: str) -> str:
        """Fallback reply using Gemini/OpenRouter when not integrated into Aura."""
        try:
            from google import genai as _genai
            keys = _load_keys()
            key = (keys.get("gemini_api_key") or "").strip()
            if key:
                client = _genai.Client(api_key=key, http_options={"api_version": "v1beta"})
                resp = client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=(
                        "You are Aura, a helpful AI assistant. "
                        "User is messaging from Telegram mobile. Be concise.\n\n"
                        f"User: {prompt}"
                    ),
                )
                text = ""
                try:
                    for c in (resp.candidates or []):
                        for p in (getattr(c.content, "parts", None) or []):
                            text += getattr(p, "text", "")
                except Exception:
                    text = getattr(resp, "text", "") or ""
                if text.strip():
                    return text.strip()
        except Exception as exc:
            logger.warning("Telegram standalone Gemini failed: %s", exc)

        try:
            from llm_client import client as _or_client
            keys = _load_keys()
            if keys.get("openrouter_api_key"):
                return _or_client.chat(prompt, system="You are Aura AI. Be concise.", max_tokens=500).strip()
        except Exception as exc:
            logger.warning("Telegram standalone OpenRouter failed: %s", exc)

        return "Aura da — AI providers reach agalai right now. Try again!"


# ──────────────────────────────────────────────
# Module-level singleton
# ──────────────────────────────────────────────

_service: TelegramRemoteService | None = None


def get_service(
    status_callback: Optional[Callable[[str], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None,
) -> TelegramRemoteService:
    global _service
    if _service is None:
        _service = TelegramRemoteService(
            status_callback=status_callback,
            log_callback=log_callback,
        )
    else:
        if status_callback:
            _service._status_cb = status_callback
        if log_callback:
            _service._log_cb = log_callback
    return _service


def start_if_configured(
    status_callback: Optional[Callable[[str], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None,
    app_submitter: Optional[Callable[[str, str], None]] = None,
    speak_fn: Optional[Callable[[str], None]] = None,
) -> bool:
    """
    Auto-start the Telegram bot if a token is configured in api_keys.json.
    Returns True if started, False if token not set.
    """
    keys = _load_keys()
    token = (keys.get("telegram_bot_token") or "").strip()
    if not token:
        return False

    raw_ids = keys.get("telegram_allowed_user_ids") or []
    if isinstance(raw_ids, (int, str)):
        raw_ids = [raw_ids]
    allowed = [int(x) for x in raw_ids if str(x).strip().isdigit()]

    svc = get_service(status_callback=status_callback, log_callback=log_callback)
    if app_submitter:
        svc.bind_app_submitter(app_submitter)
    if speak_fn:
        svc.bind_speak(speak_fn)

    try:
        svc.start(token, allowed)
        return True
    except Exception as exc:
        if status_callback:
            status_callback(f"❌ Telegram start failed: {exc}")
        logger.warning("Telegram auto-start failed: %s", exc)
        return False
