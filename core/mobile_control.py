"""
core/mobile_control.py
======================
📱 Mobile Control for Aura AI (PC → Android Phone)
---------------------------------------------------
Control your Android phone from your PC using ADB!

Features:
  - unlock_phone()         → Wake + unlock screen (swipe/PIN)
  - make_call(number)      → Dial a number
  - send_sms(number, msg)  → Send SMS
  - mirror_screen()        → Mirror phone on PC (scrcpy)
  - take_phone_screenshot()→ Screenshot from phone to PC
  - set_volume(level)      → Set phone volume (0-15)
  - open_app(package)      → Open any app by package name
  - get_battery()          → Phone battery %
  - get_phone_info()       → Device info
  - detect_intent(text)    → NLP — detect mobile control commands
  - process_command(text)  → Full NLP dispatcher

Requirements:
  - Android phone with USB Debugging enabled
  - Connected via USB OR WiFi ADB
  - scrcpy + adb from WinGet installation
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
import logging
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger("aura.mobile")

# ──────────────────────────────────────────────
# Tool paths
# ──────────────────────────────────────────────

_SCRCPY_DIR = Path(
    r"C:\Users\Sanju\AppData\Local\Microsoft\WinGet\Packages"
    r"\Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\scrcpy-win64-v4.1"
)
ADB_PATH    = str(_SCRCPY_DIR / "adb.exe")
SCRCPY_PATH = str(_SCRCPY_DIR / "scrcpy.exe")


def _adb(*args, timeout: int = 10) -> tuple[int, str, str]:
    """Run an adb command. Returns (returncode, stdout, stderr)."""
    cmd = [ADB_PATH] + list(args)
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as exc:
        return -1, "", str(exc)


def _adb_shell(*args, timeout: int = 10) -> tuple[int, str, str]:
    """Run adb shell command."""
    return _adb("shell", *args, timeout=timeout)


# ──────────────────────────────────────────────
# Connection helpers
# ──────────────────────────────────────────────

def is_device_connected() -> bool:
    """Check if any Android device is connected via ADB."""
    rc, out, _ = _adb("devices")
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    # Filter header line
    devices = [l for l in lines if l and not l.startswith("List") and "\t" in l]
    connected = [d for d in devices if "device" in d.split("\t")]
    return len(connected) > 0


def get_connected_devices() -> list[str]:
    """Return list of connected device IDs."""
    rc, out, _ = _adb("devices")
    devices = []
    for line in out.splitlines():
        line = line.strip()
        if line and "\t" in line and not line.startswith("List"):
            parts = line.split("\t")
            if len(parts) >= 2 and parts[1].strip() == "device":
                devices.append(parts[0].strip())
    return devices


def connect_wifi(ip: str, port: int = 5555) -> str:
    """Connect to phone over WiFi ADB."""
    rc, out, err = _adb("connect", f"{ip}:{port}", timeout=15)
    if rc == 0 and "connected" in out.lower():
        return f"✅ Connected to {ip}:{port}!"
    return f"❌ WiFi connect failed: {out or err}"


# ──────────────────────────────────────────────
# Screen & Lock
# ──────────────────────────────────────────────

def wake_screen() -> str:
    """Wake up phone screen (press power button)."""
    _adb_shell("input", "keyevent", "KEYCODE_WAKEUP")
    time.sleep(0.5)
    return "📱 Screen woken up!"


def unlock_phone(pin: str = "") -> str:
    """
    Wake and unlock the phone.
    If pin is provided, enters it after swipe.
    """
    # Wake screen
    _adb_shell("input", "keyevent", "KEYCODE_WAKEUP")
    time.sleep(0.8)

    # Swipe up to unlock (works for swipe-to-unlock)
    _adb_shell("input", "swipe", "540", "1800", "540", "900", "300")
    time.sleep(0.8)

    if pin:
        # Type PIN
        _adb_shell("input", "text", pin)
        time.sleep(0.3)
        _adb_shell("input", "keyevent", "KEYCODE_ENTER")
        return f"🔓 Phone unlocked with PIN!"

    return "🔓 Phone screen unlocked!"


def lock_phone() -> str:
    """Lock the phone screen."""
    _adb_shell("input", "keyevent", "KEYCODE_SLEEP")
    return "🔒 Phone locked!"


def get_screen_state() -> str:
    """Check if phone screen is on or off."""
    rc, out, _ = _adb_shell("dumpsys", "power")
    if "mHoldingWakeLockSuspendBlocker=true" in out or "Display Power: state=ON" in out:
        return "on"
    return "off"


# ──────────────────────────────────────────────
# Calls & SMS
# ──────────────────────────────────────────────

def make_call(number: str) -> str:
    """Dial a phone number."""
    number = re.sub(r"[^\d+]", "", number)
    if not number:
        return "❌ Invalid phone number da!"
    rc, out, err = _adb_shell(
        "am", "start",
        "-a", "android.intent.action.CALL",
        "-d", f"tel:{number}",
        timeout=10
    )
    if rc == 0:
        return f"📞 Calling {number}..."
    return f"❌ Call failed: {err or out}"


def end_call() -> str:
    """End the current call."""
    _adb_shell("input", "keyevent", "KEYCODE_ENDCALL")
    return "📵 Call ended!"


def send_sms(number: str, message: str) -> str:
    """Open SMS compose with number and message."""
    number = re.sub(r"[^\d+]", "", number)
    if not number or not message:
        return "❌ Number or message missing da!"
    # Encode spaces for URI
    encoded_msg = message.replace(" ", "%20")
    rc, out, err = _adb_shell(
        "am", "start",
        "-a", "android.intent.action.SENDTO",
        "-d", f"sms:{number}",
        "--es", "sms_body", message,
        "--ez", "exit_on_sent", "false",
        timeout=10
    )
    if rc == 0:
        return f"💬 SMS to {number} opened! Review and send from phone."
    return f"❌ SMS failed: {err or out}"


# ──────────────────────────────────────────────
# Screen Mirror
# ──────────────────────────────────────────────

_mirror_proc: Optional[subprocess.Popen] = None


def mirror_screen(
    title: str = "📱 Aura — Phone Mirror",
    always_on_top: bool = True,
    max_fps: int = 60,
) -> str:
    """Launch scrcpy to mirror phone screen on PC."""
    global _mirror_proc

    if _mirror_proc and _mirror_proc.poll() is None:
        return "📱 Mirror already running da! (close the window to stop)"

    if not is_device_connected():
        return "❌ Phone not connected! USB debug enable panni connect pannu da."

    cmd = [
        SCRCPY_PATH,
        "--window-title", title,
        "--max-fps", str(max_fps),
        "--shortcut-mod", "lalt",
    ]
    if always_on_top:
        cmd += ["--always-on-top"]

    try:
        _mirror_proc = subprocess.Popen(
            cmd,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        time.sleep(1.5)
        if _mirror_proc.poll() is None:
            return "📱 Phone screen mirrored! PC la phone screen varuchu da. Mouse/keyboard la control pannalam!"
        return "❌ scrcpy failed to start. Check phone connection."
    except Exception as exc:
        return f"❌ Mirror error: {exc}"


def stop_mirror() -> str:
    """Stop the screen mirror."""
    global _mirror_proc
    if _mirror_proc:
        try:
            _mirror_proc.terminate()
            _mirror_proc = None
            return "📱 Mirror stopped."
        except Exception as exc:
            return f"❌ Stop failed: {exc}"
    return "Mirror illai da — already stopped."


# ──────────────────────────────────────────────
# Media & Volume
# ──────────────────────────────────────────────

def set_volume(level: int) -> str:
    """Set phone volume (0-15). 15 = max."""
    level = max(0, min(15, int(level)))
    _adb_shell("media", "volume", "--stream", "3", "--set", str(level))
    return f"🔊 Phone volume set to {level}/15!"


def volume_up() -> str:
    _adb_shell("input", "keyevent", "KEYCODE_VOLUME_UP")
    return "🔊 Volume up!"


def volume_down() -> str:
    _adb_shell("input", "keyevent", "KEYCODE_VOLUME_DOWN")
    return "🔉 Volume down!"


def mute_phone() -> str:
    _adb_shell("input", "keyevent", "KEYCODE_VOLUME_MUTE")
    return "🔇 Phone muted!"


def play_pause_media() -> str:
    _adb_shell("input", "keyevent", "KEYCODE_MEDIA_PLAY_PAUSE")
    return "⏯️ Play/Pause toggled!"


# ──────────────────────────────────────────────
# Apps
# ──────────────────────────────────────────────

# Common app packages
APP_PACKAGES = {
    "whatsapp":   "com.whatsapp",
    "instagram":  "com.instagram.android",
    "youtube":    "com.google.android.youtube",
    "camera":     "com.android.camera2",
    "chrome":     "com.android.chrome",
    "gmail":      "com.google.android.gm",
    "maps":       "com.google.android.apps.maps",
    "settings":   "com.android.settings",
    "spotify":    "com.spotify.music",
    "telegram":   "org.telegram.messenger",
    "phone":      "com.android.dialer",
    "messages":   "com.google.android.apps.messaging",
    "photos":     "com.google.android.apps.photos",
    "files":      "com.google.android.apps.nbu.files",
    "clock":      "com.android.deskclock",
    "calculator": "com.android.calculator2",
    "contacts":   "com.android.contacts",
    "calendar":   "com.google.android.calendar",
}


def open_app(app_name: str) -> str:
    """Open an app on the phone by name or package."""
    name = app_name.lower().strip()
    package = APP_PACKAGES.get(name, name)  # fallback = treat as package name
    rc, out, err = _adb_shell(
        "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1",
        timeout=10
    )
    if rc == 0 and "Events injected" in out:
        return f"📲 {app_name.title()} opened on phone!"
    return f"❌ App open failed: {err or out}\nHint: package name check pannu da."


def close_app(package: str) -> str:
    """Force stop an app."""
    rc, out, err = _adb_shell("am", "force-stop", package)
    if rc == 0:
        return f"✅ App stopped!"
    return f"❌ Stop failed: {err}"


def go_home() -> str:
    """Press Home button on phone."""
    _adb_shell("input", "keyevent", "KEYCODE_HOME")
    return "🏠 Home button pressed!"


def go_back() -> str:
    """Press Back button."""
    _adb_shell("input", "keyevent", "KEYCODE_BACK")
    return "◀️ Back pressed!"


def press_recents() -> str:
    """Open recents/multitasking."""
    _adb_shell("input", "keyevent", "KEYCODE_APP_SWITCH")
    return "📋 Recents opened!"


# ──────────────────────────────────────────────
# Info & Screenshot
# ──────────────────────────────────────────────

def get_battery() -> str:
    """Get phone battery level and status."""
    rc, out, _ = _adb_shell("dumpsys", "battery", timeout=8)
    level = "?"
    status = "?"
    plugged = False
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("level:"):
            level = line.split(":")[1].strip()
        elif line.startswith("status:"):
            s = line.split(":")[1].strip()
            status = {
                "1": "Unknown", "2": "Charging ⚡",
                "3": "Discharging 🔋", "4": "Not charging",
                "5": "Full ✅"
            }.get(s, s)
        elif line.startswith("plugged:"):
            plugged = line.split(":")[1].strip() != "0"
    icon = "🔋" if not plugged else "⚡"
    return f"{icon} Phone Battery: {level}% — {status}"


def get_phone_info() -> str:
    """Get device model, Android version, IP address."""
    rc1, model, _ = _adb_shell("getprop", "ro.product.model")
    rc2, android, _ = _adb_shell("getprop", "ro.build.version.release")
    rc3, ip_out, _ = _adb_shell("ip", "route", "get", "8.8.8.8")
    ip = "?"
    for part in ip_out.split():
        if re.match(r"\d+\.\d+\.\d+\.\d+", part):
            if part != "8.8.8.8":
                ip = part
                break
    battery = get_battery()
    return (
        f"📱 Device: {model or 'Unknown'}\n"
        f"🤖 Android: {android or 'Unknown'}\n"
        f"🌐 IP: {ip}\n"
        f"{battery}"
    )


def take_phone_screenshot(save_path: str = "") -> str:
    """Take screenshot from phone and save to PC."""
    if not save_path:
        from pathlib import Path
        save_path = str(Path.home() / "Downloads" / f"phone_screenshot_{int(time.time())}.png")

    # Capture on phone
    _adb_shell("screencap", "-p", "/sdcard/aura_screen.png")
    time.sleep(0.5)

    # Pull to PC
    rc, out, err = _adb("pull", "/sdcard/aura_screen.png", save_path, timeout=15)
    if rc == 0:
        # Clean up temp file on phone
        _adb_shell("rm", "/sdcard/aura_screen.png")
        return f"📸 Phone screenshot saved to:\n{save_path}"
    return f"❌ Screenshot failed: {err or out}"


def type_text(text: str) -> str:
    """Type text on phone (into focused field)."""
    # Escape spaces and special chars for ADB
    escaped = text.replace(" ", "%s").replace("'", "\\'")
    _adb_shell("input", "text", escaped)
    return f"⌨️ Typed: {text}"


# ──────────────────────────────────────────────
# NLP Intent Detection
# ──────────────────────────────────────────────

_MOBILE_PATTERNS = [
    # Unlock / Lock
    (r"\b(unlock|open|wake).*(phone|mobile|screen)\b",          "unlock"),
    (r"\b(lock).*(phone|mobile|screen)\b",                      "lock"),
    (r"\b(phone|mobile).*(unlock|wake|open)\b",                 "unlock"),

    # Mirror
    (r"\b(mirror|show|screen|cast|display).*(phone|mobile)\b",  "mirror"),
    (r"\b(phone|mobile).*(mirror|screen|show|cast)\b",          "mirror"),
    (r"\bscrcpy\b",                                             "mirror"),

    # Call
    (r"\b(call|dial|phone call|ring)\b.*(\d[\d\s\-]+)",        "call"),
    (r"\bcall\b.*\b(someone|contact)\b",                        "call"),

    # SMS
    (r"\b(sms|text|message|msg)\b.*(\d[\d\s\-]+)",             "sms"),
    (r"\bsend.*(text|message|sms)\b",                           "sms"),

    # Screenshot
    (r"\b(screenshot|screen shot|capture).*(phone|mobile)\b",   "phone_screenshot"),
    (r"\bphone.*(screenshot|screen shot|capture)\b",            "phone_screenshot"),

    # Battery
    (r"\b(battery|charge).*(phone|mobile)\b",                   "battery"),
    (r"\bphone.*(battery|charge|level)\b",                      "battery"),

    # Volume
    (r"\b(volume|sound|loud).*(up|increase|raise|max)\b",       "volume_up"),
    (r"\b(volume|sound|quiet).*(down|decrease|low|mute)\b",     "volume_down"),
    (r"\b(mute|silent).*(phone|mobile)\b",                      "mute"),
    (r"\bphone.*(mute|silent|quiet)\b",                         "mute"),

    # App open
    (r"\bopen\b.*(whatsapp|instagram|youtube|spotify|camera|chrome|gmail|maps|telegram)\b.*\b(phone|mobile)\b", "open_app"),
    (r"\bphone\b.*\bopen\b.*(whatsapp|instagram|youtube|spotify|camera|chrome|gmail|maps|telegram)\b",          "open_app"),

    # Info
    (r"\b(phone info|device info|phone status|mobile info)\b",  "info"),

    # Navigation
    (r"\b(home|go home).*(phone|mobile)\b",                     "go_home"),
    (r"\bphone.*(home|go home)\b",                              "go_home"),
    (r"\b(back|go back).*(phone|mobile)\b",                     "go_back"),
    (r"\bconnect.*wifi.*adb\b",                                  "connect_wifi"),
]


def detect_mobile_intent(text: str) -> Optional[str]:
    """Returns intent string if text is a mobile control command, else None."""
    text_lower = text.lower()
    # Quick keyword filter first
    if not any(kw in text_lower for kw in [
        "phone", "mobile", "call", "dial", "sms", "text message",
        "mirror", "scrcpy", "unlock", "lock screen", "battery",
        "volume", "mute phone"
    ]):
        return None
    for pattern, intent in _MOBILE_PATTERNS:
        if re.search(pattern, text_lower):
            return intent
    return None


def _extract_number(text: str) -> str:
    """Extract phone number from text."""
    match = re.search(r"(\+?\d[\d\s\-]{7,14}\d)", text)
    return re.sub(r"[\s\-]", "", match.group(1)) if match else ""


def _extract_message(text: str) -> str:
    """Extract SMS message body."""
    # Try after "saying", "message", "text"
    for kw in ["saying", "message", "msg", "body"]:
        if kw in text.lower():
            idx = text.lower().index(kw)
            return text[idx + len(kw):].strip().strip("'\"")
    return "Hi da!"


def _extract_app(text: str) -> str:
    """Extract app name from text."""
    for app in APP_PACKAGES:
        if app in text.lower():
            return app
    return ""


def process_mobile_command(
    text: str,
    speak_cb: Optional[Callable[[str], None]] = None,
    pin: str = "",
) -> Optional[str]:
    """
    Full NLP dispatcher for mobile control commands.
    Returns reply string, or None if not a mobile command.
    """
    intent = detect_mobile_intent(text)
    if not intent:
        return None

    def _speak(msg: str):
        if speak_cb:
            try:
                speak_cb(msg)
            except Exception:
                pass

    if not is_device_connected():
        msg = (
            "📱 Phone connected illai da!\n\n"
            "USB cable connect pannu + Phone Settings → Developer Options → USB Debugging ON pannu!"
        )
        _speak("Phone connected illai da. USB connect panni USB debugging enable pannu.")
        return msg

    result = ""

    if intent == "unlock":
        result = unlock_phone(pin=pin)
    elif intent == "lock":
        result = lock_phone()
    elif intent == "mirror":
        result = mirror_screen()
    elif intent == "call":
        number = _extract_number(text)
        if not number:
            result = "❌ Number sollu da! Example: 'call 9876543210'"
        else:
            result = make_call(number)
    elif intent == "sms":
        number = _extract_number(text)
        msg_body = _extract_message(text)
        if not number:
            result = "❌ Number sollu da!"
        else:
            result = send_sms(number, msg_body)
    elif intent == "phone_screenshot":
        result = take_phone_screenshot()
    elif intent == "battery":
        result = get_battery()
    elif intent == "volume_up":
        result = volume_up()
    elif intent == "volume_down":
        result = volume_down()
    elif intent == "mute":
        result = mute_phone()
    elif intent == "open_app":
        app = _extract_app(text)
        if not app:
            result = "❌ App name sollu da! (whatsapp, instagram, youtube...)"
        else:
            result = open_app(app)
    elif intent == "info":
        result = get_phone_info()
    elif intent == "go_home":
        result = go_home()
    elif intent == "go_back":
        result = go_back()
    elif intent == "connect_wifi":
        # Extract IP
        ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", text)
        if ip_match:
            result = connect_wifi(ip_match.group(1))
        else:
            result = "❌ IP address sollu da! Example: 'connect wifi adb 192.168.1.5'"
    else:
        result = "📱 Mobile command recognised but handler illai."

    _speak(result.replace("❌", "").replace("✅", "").replace("📱", "").replace("📞", "").strip())
    return result
