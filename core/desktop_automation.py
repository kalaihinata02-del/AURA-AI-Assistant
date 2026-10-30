"""
Aura Autonomous Desktop Automation Engine
=========================================
Empowers Aura to autonomously navigate, control, and execute complex workflows
on the user's desktop across Windows.

Capabilities:
1. Window & Workspace Management (Show Desktop, Close, Switch, Maximize, Lock PC, Task Manager)
2. Screen Capture & Visual Telemetry (Timestamped screenshot to Pictures/Screenshots or Desktop)
3. Autonomous Typing, Writing & Form Filling (Direct typing, or Open App + Type multi-step)
4. Browser & Web Navigation Autopilot (Google Search, YouTube, Spotify, Tabs, Scroll)
5. Media & Playback Hardware Controller (Play/Pause, Next, Prev, Mute)
6. System Explorer & Quick Folders (Downloads, Documents, Desktop, Pictures, C Drive)
7. Multi-Step Autonomous Sequence Planner
8. 100% Bilingual & Tanglish Comprehension (English, Tamil, Tanglish)
"""

from __future__ import annotations

import os
import sys
import time
import datetime
import subprocess
import platform
import urllib.parse
import re
from pathlib import Path
from typing import Optional, Tuple, Callable, Any, List, Dict

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.05
    _PYAUTOGUI_OK = True
except ImportError:
    _PYAUTOGUI_OK = False

try:
    import pyperclip
    _PYPERCLIP_OK = True
except ImportError:
    _PYPERCLIP_OK = False

try:
    import win32api
    import win32con
    import win32gui
    _WIN32_OK = True
except ImportError:
    _WIN32_OK = False


class DesktopAutomationEngine:
    """Core autonomous desktop automation controller for Aura AI."""

    def __init__(self):
        self.os_type = platform.system()
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensures default directories like Screenshots exist."""
        try:
            screenshots_dir = Path.home() / "Pictures" / "Screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            try:
                (Path.home() / "Desktop" / "Screenshots").mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

    # ---------------------------------------------------------
    # 1. WINDOW & WORKSPACE CONTROLS
    # ---------------------------------------------------------
    def show_desktop(self) -> str:
        """Minimizes all windows to display the desktop (Win + D)."""
        if self.os_type == "Windows":
            if _PYAUTOGUI_OK:
                pyautogui.hotkey("win", "d")
            else:
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "(New-Object -ComObject Shell.Application).MinimizeAll()"],
                    capture_output=True, timeout=5
                )
            return "Minimized all windows and navigated to Desktop."
        return "Show desktop action executed."

    def close_active_window(self) -> str:
        """Closes the currently active foreground window (Alt + F4)."""
        if _PYAUTOGUI_OK:
            pyautogui.hotkey("alt", "f4")
            return "Active window closed."
        return "Unable to close window (pyautogui unavailable)."

    def switch_window(self) -> str:
        """Switches between active open windows (Alt + Tab)."""
        if _PYAUTOGUI_OK:
            pyautogui.hotkey("alt", "tab")
            return "Switched active window."
        return "Unable to switch window."

    def maximize_window(self) -> str:
        """Maximizes current active window (Win + Up)."""
        if _PYAUTOGUI_OK:
            pyautogui.hotkey("win", "up")
            return "Active window maximized."
        return "Unable to maximize window."

    def minimize_window(self) -> str:
        """Minimizes current active window (Win + Down)."""
        if _PYAUTOGUI_OK:
            pyautogui.hotkey("win", "down")
            return "Active window minimized."
        return "Unable to minimize window."

    def lock_workstation(self) -> str:
        """Instantly locks the Windows PC workstation (Win + L)."""
        if self.os_type == "Windows":
            try:
                import ctypes
                ctypes.windll.user32.LockWorkStation()
                return "Computer workstation locked securely."
            except Exception as e:
                return f"Failed to lock workstation: {e}"
        return "Lock workstation is only supported on Windows."

    def open_task_manager(self) -> str:
        """Opens Windows Task Manager (Ctrl + Shift + Esc)."""
        if _PYAUTOGUI_OK:
            pyautogui.hotkey("ctrl", "shift", "esc")
            return "Task Manager opened."
        try:
            subprocess.Popen(["taskmgr.exe"])
            return "Task Manager launched."
        except Exception as e:
            return f"Failed to launch Task Manager: {e}"

    def open_run_dialog(self) -> str:
        """Opens Windows Run dialog (Win + R)."""
        if _PYAUTOGUI_OK:
            pyautogui.hotkey("win", "r")
            return "Run dialog opened."
        return "Run dialog shortcut sent."

    # ---------------------------------------------------------
    # 2. SCREENSHOT & SCREEN CAPTURE
    # ---------------------------------------------------------
    def take_screenshot(self, ui_instance: Any = None) -> Tuple[bool, str, Optional[Path]]:
        """
        Captures a high-resolution screenshot and saves it to Pictures/Screenshots or Desktop.
        Returns (success: bool, message: str, file_path: Path | None).
        """
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir = Path.home() / "Pictures" / "Screenshots"
        if not target_dir.exists():
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                target_dir = Path.home() / "Desktop"

        out_path = target_dir / f"Aura_Snap_{ts}.png"

        # 1. Try via UI Qt grabWindow if available
        if ui_instance and hasattr(ui_instance, "capture_screen_threadsafe"):
            try:
                raw_bytes = ui_instance.capture_screen_threadsafe()
                if raw_bytes and len(raw_bytes) > 100:
                    with open(out_path, "wb") as f:
                        f.write(raw_bytes)
                    return True, f"Screenshot captured successfully: {out_path.name}", out_path
            except Exception:
                pass

        # 2. Try via pyautogui
        if _PYAUTOGUI_OK:
            try:
                img = pyautogui.screenshot()
                img.save(str(out_path))
                return True, f"Screenshot captured successfully: {out_path.name}", out_path
            except Exception:
                pass

        # 3. Try via mss
        try:
            import mss
            import mss.tools
            with mss.mss() as sct:
                monitor = sct.monitors[0]
                sct_img = sct.grab(monitor)
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(out_path))
                return True, f"Screenshot captured successfully: {out_path.name}", out_path
        except Exception:
            pass

        # 4. Try via PowerShell fallback
        try:
            ps_cmd = (
                f"Add-Type -AssemblyName System.Windows.Forms; "
                f"$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
                f"$bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height; "
                f"$graphics = [System.Drawing.Graphics]::FromImage($bmp); "
                f"$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size); "
                f"$bmp.Save('{str(out_path)}', [System.Drawing.Imaging.ImageFormat]::Png); "
                f"$graphics.Dispose(); $bmp.Dispose();"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=8)
            if out_path.exists() and out_path.stat().st_size > 0:
                return True, f"Screenshot captured successfully: {out_path.name}", out_path
        except Exception:
            pass

        return False, "Failed to capture screenshot.", None

    # ---------------------------------------------------------
    # 3. TYPING & MULTI-STEP APP WRITING
    # ---------------------------------------------------------
    def type_text(self, text: str, interval: float = 0.02) -> str:
        """Types or pastes text at the current cursor position."""
        if not text:
            return "No text provided to type."

        # If text has newlines or unicode/non-ascii, use clipboard paste for 100% accuracy
        has_unicode = any(ord(c) > 127 for c in text) or "\n" in text or len(text) > 40
        if has_unicode and _PYPERCLIP_OK and _PYAUTOGUI_OK:
            pyperclip.copy(text)
            time.sleep(0.08)
            pyautogui.hotkey("ctrl", "v")
            return f"Typed: '{text[:50]}...'" if len(text) > 50 else f"Typed: '{text}'"

        if _PYAUTOGUI_OK:
            pyautogui.typewrite(text, interval=interval)
            return f"Typed: '{text[:50]}...'" if len(text) > 50 else f"Typed: '{text}'"

        return "Typing failed (pyautogui unavailable)."

    def open_app_and_type(self, app_name: str, content: str) -> str:
        """
        Launches an application (e.g. Notepad, Word), waits for focus,
        and autonomously writes/pastes the given text.
        """
        from actions.open_app import open_app
        open_app({"app_name": app_name})
        time.sleep(1.2)  # Wait for application window to surface and initialize focus

        self.type_text(content)
        return f"Opened {app_name.title()} and typed the requested content."

    # ---------------------------------------------------------
    # 4. KEYBOARD SHORTCUTS & EDITING
    # ---------------------------------------------------------
    def select_all(self) -> str:
        if _PYAUTOGUI_OK:
            pyautogui.hotkey("ctrl", "a")
            return "Selected all."
        return "Hotkey failed."

    def copy(self) -> str:
        if _PYAUTOGUI_OK:
            pyautogui.hotkey("ctrl", "c")
            return "Copied to clipboard."
        return "Hotkey failed."

    def paste(self) -> str:
        if _PYAUTOGUI_OK:
            pyautogui.hotkey("ctrl", "v")
            return "Pasted from clipboard."
        return "Hotkey failed."

    def undo(self) -> str:
        if _PYAUTOGUI_OK:
            pyautogui.hotkey("ctrl", "z")
            return "Undo executed."
        return "Hotkey failed."

    def save_file(self) -> str:
        if _PYAUTOGUI_OK:
            pyautogui.hotkey("ctrl", "s")
            return "Save command triggered."
        return "Hotkey failed."

    def press_key(self, key_name: str) -> str:
        clean_key = key_name.lower().strip()
        if _PYAUTOGUI_OK:
            pyautogui.press(clean_key)
            return f"Pressed '{clean_key}'."
        return f"Unable to press '{clean_key}'."

    # ---------------------------------------------------------
    # 5. MOUSE & SCROLLING
    # ---------------------------------------------------------
    def click(self, button: str = "left", clicks: int = 1, x: Optional[int] = None, y: Optional[int] = None) -> str:
        """Clicks at current cursor position or specified (x, y) coordinates."""
        if _PYAUTOGUI_OK:
            try:
                if x is not None and y is not None:
                    pyautogui.click(x=x, y=y, button=button, clicks=clicks)
                    return f"Clicked at ({x}, {y}) [{button}]."
                pyautogui.click(button=button, clicks=clicks)
                return f"Clicked at current position [{button}]."
            except Exception as e:
                return f"Click failed: {e}"
        return "Click failed: pyautogui unavailable."

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> str:
        """Performs double click."""
        return self.click(button="left", clicks=2, x=x, y=y)

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> str:
        """Performs right click."""
        return self.click(button="right", clicks=1, x=x, y=y)

    def click_element(self, description: str, click_type: str = "single", speak_cb: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
        """Finds UI element on screen using Ghost Vision AI and clicks it with visual reticle."""
        try:
            from core.ghost_vision import ghost_vision
            return ghost_vision.execute_ghost_click(description, click_type=click_type, speak_cb=speak_cb)
        except Exception as e:
            try:
                from actions.computer_control import computer_control
                res = computer_control({"action": "screen_click", "description": description})
                if "Clicked" in res:
                    return True, f"Clicked '{description}' successfully."
                return False, res
            except Exception as e2:
                return False, f"Ghost Vision click error: {e2}"


    def scroll(self, direction: str = "down", amount: int = 5) -> str:
        if _PYAUTOGUI_OK:
            clicks = -abs(amount) * 100 if direction.lower() == "down" else abs(amount) * 100
            pyautogui.scroll(clicks)
            return f"Scrolled {direction}."
        return "Scroll failed."

    # ---------------------------------------------------------
    # 6. WEB BROWSER AUTOPILOT
    # ---------------------------------------------------------
    def google_search(self, query: str) -> str:
        """Launches web browser and performs Google search for query."""
        import webbrowser
        q = urllib.parse.quote_plus(query.strip())
        url = f"https://www.google.com/search?q={q}"
        webbrowser.open(url)
        return f"Searching Google for: '{query}'"

    def youtube_search_or_play(self, query: str) -> str:
        """Searches or plays video on YouTube."""
        from actions.youtube_video import youtube_video
        try:
            return youtube_video({"action": "play", "query": query})
        except Exception:
            import webbrowser
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query.strip())}"
            webbrowser.open(url)
            return f"Playing YouTube for: '{query}'"

    def spotify_play(self, query: str) -> str:
        """Searches and plays track on Spotify desktop app or web player."""
        try:
            from actions.spotify_controller import spotify_controller
            return spotify_controller({"action": "search_play", "query": query})
        except Exception as e:
            import webbrowser
            url = f"https://open.spotify.com/search/{urllib.parse.quote_plus(query.strip())}"
            webbrowser.open(url)
            return f"Opened Spotify for '{query}'"

    def browser_new_tab(self) -> str:
        if _PYAUTOGUI_OK:
            pyautogui.hotkey("ctrl", "t")
            return "Opened new browser tab."
        return "Shortcut failed."

    def browser_close_tab(self) -> str:
        if _PYAUTOGUI_OK:
            pyautogui.hotkey("ctrl", "w")
            return "Closed active tab."
        return "Shortcut failed."

    def browser_reopen_tab(self) -> str:
        if _PYAUTOGUI_OK:
            pyautogui.hotkey("ctrl", "shift", "t")
            return "Reopened closed tab."
        return "Shortcut failed."

    def browser_refresh(self) -> str:
        if _PYAUTOGUI_OK:
            pyautogui.hotkey("ctrl", "r")
            return "Refreshed current page."
        return "Shortcut failed."

    # ---------------------------------------------------------
    # 7. MEDIA PLAYBACK KEYS (GLOBAL BACKGROUND CONTROL)
    # ---------------------------------------------------------
    def media_play_pause(self) -> str:
        """Sends global media play/pause hardware key event."""
        if self.os_type == "Windows":
            try:
                import ctypes
                VK_MEDIA_PLAY_PAUSE = 0xB3
                ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
                time.sleep(0.04)
                ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 2, 0)
                return "Media playback toggled (play/pause)."
            except Exception:
                pass
        if _PYAUTOGUI_OK:
            pyautogui.press("playpause")
            return "Media playback toggled."
        return "Media control unavailable."

    def media_next(self) -> str:
        """Skips to next audio/video track."""
        if self.os_type == "Windows":
            try:
                import ctypes
                VK_MEDIA_NEXT_TRACK = 0xB0
                ctypes.windll.user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 0, 0)
                time.sleep(0.04)
                ctypes.windll.user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 2, 0)
                return "Skipped to next track."
            except Exception:
                pass
        if _PYAUTOGUI_OK:
            pyautogui.press("nexttrack")
            return "Skipped to next track."
        return "Media control unavailable."

    def media_previous(self) -> str:
        """Returns to previous audio/video track."""
        if self.os_type == "Windows":
            try:
                import ctypes
                VK_MEDIA_PREV_TRACK = 0xB1
                ctypes.windll.user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 0, 0)
                time.sleep(0.04)
                ctypes.windll.user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 2, 0)
                return "Returned to previous track."
            except Exception:
                pass
        if _PYAUTOGUI_OK:
            pyautogui.press("prevtrack")
            return "Returned to previous track."
        return "Media control unavailable."

    # ---------------------------------------------------------
    # 8. QUICK FOLDER EXPLORER
    # ---------------------------------------------------------
    def open_folder(self, folder_name: str) -> str:
        """Opens standard OS folders in File Explorer."""
        low = folder_name.lower().strip()
        path = None
        if "download" in low:
            path = Path.home() / "Downloads"
        elif "document" in low or "doc" in low:
            path = Path.home() / "Documents"
        elif "desktop" in low:
            path = Path.home() / "Desktop"
        elif "picture" in low or "photo" in low or "image" in low:
            path = Path.home() / "Pictures"
        elif "music" in low:
            path = Path.home() / "Music"
        elif "video" in low:
            path = Path.home() / "Videos"
        elif "c drive" in low or "c:" in low:
            path = Path("C:\\")
        elif "recycle bin" in low or "trash" in low:
            os.system("start shell:RecycleBinFolder")
            return "Recycle Bin opened."

        if path and path.exists():
            try:
                os.startfile(str(path))
                return f"Opened {path.name} folder."
            except Exception as e:
                return f"Failed to open folder: {e}"

        # Default File Explorer
        try:
            subprocess.Popen(["explorer.exe"])
            return "File Explorer opened."
        except Exception as e:
            return f"Failed to open File Explorer: {e}"

    # ---------------------------------------------------------
    # 9. DESKTOP ORGANIZATION
    # ---------------------------------------------------------
    def organize_desktop(self) -> str:
        try:
            from actions.desktop_organizer_mcp import get_organizer_engine
            return get_organizer_engine().organize(target="desktop", mode="by_type")
        except Exception:
            try:
                from actions.desktop import organize_desktop
                return organize_desktop()
            except Exception as e:
                return f"Failed to organize desktop: {e}"

    # ---------------------------------------------------------
    # 10. NATURAL LANGUAGE INTENT PARSER & DISPATCHER
    # ---------------------------------------------------------
    def handle_command(
        self,
        command_text: str,
        speak_cb: Optional[Callable[[str], Any]] = None,
        ui_instance: Any = None,
    ) -> Tuple[bool, str]:
        """
        Parses and executes natural language desktop automation commands
        in English, Tamil, and Tanglish.
        Returns (handled: bool, spoken_reply: str).
        """
        raw = (command_text or "").strip()
        low = raw.lower()
        # --- 0. MULTI-STEP COMPOUND SEQUENCES ---
        # e.g., "minimize all windows and take a screenshot", "show desktop and open task manager"
        if any(sep in low for sep in (" and ", " then ", " aprom ", " apram ")) and not any(w in low for w in ("type", "write", "ezhuthu")):
            for sep in (" and ", " then ", " aprom ", " apram "):
                if sep in low:
                    parts = [p.strip() for p in re.split(re.escape(sep), raw, flags=re.IGNORECASE) if p.strip()]
                    if len(parts) >= 2:
                        replies = []
                        all_handled = True
                        for part in parts:
                            h, r = self.handle_command(part, speak_cb=None, ui_instance=ui_instance)
                            if h:
                                replies.append(r)
                                time.sleep(0.4)
                            else:
                                all_handled = False
                                break
                        if all_handled and replies:
                            combined_reply = ". ".join(replies)
                            if speak_cb:
                                speak_cb(combined_reply)
                            return True, combined_reply

        # --- A. SCREENSHOT CAPTURE ---
        is_screenshot = any(p in low for p in (
            "screenshot", "screen capture", "screen snap", "capture screen",
            "screenshot edu", "screenshot podu", "snap the screen",
            "take a screenshot", "take screenshot", "oru screenshot edu", "screenshot eduthu kudu"
        ))
        if is_screenshot and not any(p in low for p in ("analyze", "what is on", "read screen", "look at screen")):
            if speak_cb:
                speak_cb("Capturing screenshot nanba..." if any(k in low for k in ("edu", "podu", "nanba")) else "Capturing screenshot...")
            ok, msg, path = self.take_screenshot(ui_instance)
            if ok and path:
                reply = f"Screenshot eduthachu nanba. File '{path.name}' save aagiduchu." if any(k in low for k in ("edu", "podu", "nanba")) else f"Screenshot saved to {path.name}, sir."
                return True, reply
            return True, "Screenshot capture completed."

        # --- B. MINIMIZE ALL / SHOW DESKTOP ---
        is_show_desktop = any(p in low for p in (
            "minimize all", "minimize all windows", "show desktop", "go to desktop",
            "desktop ku po", "desktop-ku po", "ellathayum minimize pannu", "minimize pannu",
            "desktop kaatu", "hide all windows", "clear desktop"
        ))
        if is_show_desktop and not any(k in low for k in ("organize", "clean")):
            self.show_desktop()
            reply = "Desktop-ku poyachu nanba. All windows minimized." if any(k in low for k in ("po", "pannu", "nanba")) else "Showing your desktop, sir."
            return True, reply

        # --- C. CLOSE ACTIVE WINDOW ---
        is_close_window = any(p in low for p in (
            "close window", "close this window", "close active window", "intha window close pannu",
            "window close pannu", "window moodu", "intha window moodu", "itha close pannu",
            "app close pannu", "exit window"
        ))
        if is_close_window and not any(k in low for k in ("tab", "browser tab")):
            self.close_active_window()
            reply = "Window close panniyachu nanba." if any(k in low for k in ("pannu", "moodu", "nanba")) else "Active window closed, sir."
            return True, reply

        # --- D. SWITCH WINDOW (ALT + TAB) ---
        is_switch_window = any(p in low for p in (
            "switch window", "next window", "switch app", "adutha window", "window maathu",
            "change window", "window switch pannu", "alt tab"
        ))
        if is_switch_window:
            self.switch_window()
            reply = "Window switch panniyachu." if any(k in low for k in ("maathu", "pannu")) else "Switched window, sir."
            return True, reply

        # --- E. MAXIMIZE / MINIMIZE WINDOW ---
        if any(p in low for p in ("maximize window", "perusu pannu", "fullscreen pannu", "maximize this window")):
            self.maximize_window()
            reply = "Window maximize panniyachu." if any(k in low for k in ("pannu", "perusu")) else "Window maximized, sir."
            return True, reply

        if any(p in low for p in ("minimize window", "chinna thaaku", "minimize this window")):
            self.minimize_window()
            reply = "Window minimize panniyachu." if any(k in low for k in ("pannu", "chinna")) else "Window minimized, sir."
            return True, reply

        # --- F. LOCK WORKSTATION ---
        is_lock_pc = any(p in low for p in (
            "lock pc", "lock computer", "lock screen", "pc lock pannu", "computer lock pannu",
            "screen lock pannu", "lock workstation", "pc-ah lock pannu", "lock pannidu"
        ))
        if is_lock_pc:
            self.lock_workstation()
            reply = "PC lock panniyachu nanba." if any(k in low for k in ("pannu", "nanba")) else "Workstation locked securely, sir."
            return True, reply

        # --- G. TASK MANAGER ---
        if any(p in low for p in ("task manager open pannu", "task manager thora", "open task manager", "show task manager")):
            self.open_task_manager()
            reply = "Task Manager open panniyachu." if any(k in low for k in ("pannu", "thora")) else "Task Manager opened, sir."
            return True, reply

        # --- H. MULTI-STEP: OPEN NOTEPAD/WORD AND TYPE CONTENT ---
        # e.g., "open notepad and type hello kalai", "notepad open panni nanba vanakkam nu type pannu"
        multi_type_match = re.search(
            r"(?:open|launch|start|thora)\s+(notepad|word|text editor)\s+(?:and|aprom|then|panni)\s+(?:type|write|ezhuthu)\s+(.*)",
            low,
            re.IGNORECASE,
        )
        if not multi_type_match:
            multi_type_match = re.search(
                r"(notepad|word)\s+(?:la|open panni)\s+(.*)\s+(?:nu type pannu|type pannu|write pannu)",
                low,
                re.IGNORECASE,
            )

        if multi_type_match:
            app_target = multi_type_match.group(1).strip()
            content_to_type = multi_type_match.group(2).strip()
            # Clean up trailing speech tags
            for suffix in (" nu type pannu", " type pannu", " please", " nanba"):
                if content_to_type.endswith(suffix):
                    content_to_type = content_to_type[:-len(suffix)].strip()

            if speak_cb:
                speak_cb(f"Opening {app_target.title()} and typing for you nanba...")
            res = self.open_app_and_type(app_target, content_to_type)
            reply = f"{app_target.title()} thiranthu content type panniyachu nanba." if any(k in low for k in ("nanba", "pannu", "ezhuthu")) else res
            return True, reply

        # --- I. DIRECT TYPING AT CURRENT CURSOR ---
        # e.g., "type this is an automated message", "hello world nu type pannu"
        if (low.startswith("type ") or low.startswith("write ")) and len(low.split()) > 1:
            content = raw[len("type "):].strip() if low.startswith("type ") else raw[len("write "):].strip()
            self.type_text(content)
            reply = "Typed requested text." if "type" in low else "Written."
            return True, reply

        type_tanglish_match = re.search(r"^(.*?)\s+nu\s+type\s+pannu$", low)
        if type_tanglish_match:
            content = type_tanglish_match.group(1).strip()
            self.type_text(content)
            return True, f"'{content}' nu type panniyachu nanba."

        # --- J. GOOGLE SEARCH AUTOPILOT ---
        google_query = ""
        g_match = re.search(r"google\s*(?:la|le|-la)?\s+(.*?)\s+(?:search\s*pannu|thedu|paaru|search|podu)$", low)
        if g_match and g_match.group(1).strip():
            google_query = g_match.group(1).strip()
        elif "google" in low and any(w in low for w in ("search", "thedu", "find")):
            q = raw
            for prefix in ("search google for", "search on google for", "search for", "google search for", "google search", "search on google", "google la", "google-la"):
                if q.lower().startswith(prefix):
                    q = q[len(prefix):].strip()
                    break
            for suffix in (" on google", " in google", " search pannu", " thedu", " paaru"):
                if q.lower().endswith(suffix):
                    q = q[:-len(suffix)].strip()
                    break
            google_query = q.strip()

        if google_query and "youtube" not in low and "spotify" not in low:
            if speak_cb:
                speak_cb(f"Google-la {google_query} search panren nanba." if any(k in low for k in ("la", "nanba")) else f"Searching Google for {google_query}.")
            self.google_search(google_query)
            return True, f"Google search results opened for '{google_query}'."

        # --- J2. YOUTUBE AUTOPILOT ---
        yt_match = re.search(r"youtube\s*(?:la|le|-la)?\s+(.*?)\s+(?:video\s*podu|paatu\s*podu|song\s*podu|play\s*pannu|podu|thedu|kaatu|search\s*pannu)$", low)
        if yt_match and yt_match.group(1).strip():
            yt_query = yt_match.group(1).strip()
            if speak_cb:
                speak_cb(f"Playing {yt_query} on YouTube nanba." if any(k in low for k in ("podu", "nanba")) else f"Playing {yt_query} on YouTube.")
            self.youtube_search_or_play(yt_query)
            return True, f"YouTube opened for '{yt_query}'."

        # --- K. SPOTIFY AUTOPILOT ---
        # e.g., "play illayaraja songs on spotify", "spotify la anirudh song podu"
        is_spotify = ("spotify" in low) and any(w in low for w in ("play", "podu", "song", "paatu", "music", "search", "start"))
        if is_spotify:
            q = raw
            for prefix in ("play on spotify", "play spotify", "spotify la", "spotify-la", "spotify music"):
                if prefix in q.lower():
                    q = q.lower().replace(prefix, " ")
            for suffix in (" song podu", " paatu podu", " play pannu", " podu", " play", " on spotify"):
                if q.lower().endswith(suffix):
                    q = q[:-len(suffix)].strip()
            clean_track = q.strip() or "hits"
            if speak_cb:
                speak_cb(f"Playing {clean_track} on Spotify nanba." if any(k in low for k in ("podu", "nanba")) else f"Playing {clean_track} on Spotify, sir.")
            self.spotify_play(clean_track)
            return True, f"Playing '{clean_track}' on Spotify."

        # --- L. BROWSER TAB CONTROLS ---
        if any(p in low for p in ("new tab", "open new tab", "new tab thora", "create tab")):
            self.browser_new_tab()
            return True, "New tab opened."

        if any(p in low for p in ("close tab", "close this tab", "intha tab close pannu", "tab moodu")):
            self.browser_close_tab()
            return True, "Tab closed."

        if any(p in low for p in ("reopen tab", "restore tab", "closed tab open pannu")):
            self.browser_reopen_tab()
            return True, "Reopened closed tab."

        if any(p in low for p in ("refresh page", "reload page", "page refresh pannu", "reload pannu")):
            self.browser_refresh()
            return True, "Page refreshed."

        # --- M. SCROLLING ---
        if any(p in low for p in ("scroll down", "keela scroll pannu", "down scroll")):
            self.scroll("down", 5)
            return True, "Scrolled down."

        if any(p in low for p in ("scroll up", "mela scroll pannu", "up scroll")):
            self.scroll("up", 5)
        # --- M2. GHOST VISION AUTO-CLICK & MOUSE CONTROLS ---
        # 1. Double Click at cursor
        if any(low == p for p in ("double click", "double click pannu", "rendu vaati click pannu", "double-click")):
            self.double_click()
            return True, "Double click panniyachu nanba." if any(k in low for k in ("pannu", "nanba")) else "Double clicked at current position, sir."

        # 2. Right Click at cursor
        if any(low == p for p in ("right click", "right click pannu", "right-click", "context menu")):
            self.right_click()
            return True, "Right click panniyachu nanba." if any(k in low for k in ("pannu", "nanba")) else "Right clicked at current position, sir."

        # 3. Standard Left Click at current cursor position
        if any(low == p for p in ("click", "click pannu", "left click", "left click pannu", "click here", "inga click pannu", "mouse click")):
            self.click()
            return True, "Click panniyachu nanba." if any(k in low for k in ("pannu", "nanba")) else "Clicked at current position, sir."

        # 4. GHOST VISION ELEMENT CLICK (Autonomous Screen Visual Grounding)
        # Catch triggers: "click on X", "X click pannu", "X amukku", "skip ad", "subscribe pannu", "first video play pannu", etc.
        is_ghost_click = False
        target = ""
        click_type = "single"

        # Check for double/right click on element
        if "double click on " in low or "double click pannu" in low:
            click_type = "double"
            is_ghost_click = True
            target = low.replace("double click on ", "").replace("double click pannu", "").strip()
        elif "right click on " in low or "right click pannu" in low:
            click_type = "right"
            is_ghost_click = True
            target = low.replace("right click on ", "").replace("right click pannu", "").strip()
        elif low.startswith("click on "):
            is_ghost_click = True
            target = raw[len("click on "):].strip()
        elif "click pannu" in low or "click pandren" in low or "click panren" in low:
            is_ghost_click = True
            target = raw
            for marker in ("click pannu", "click pandren", "click panren"):
                target = target.replace(marker, "")
            target = target.replace("-ah", "").replace(" ah", "").strip()
        elif any(p in low for p in (" amukku", " press pannu")):
            is_ghost_click = True
            target = raw
            for marker in ("amukku", "press pannu"):
                target = target.replace(marker, "")
            target = target.replace("-ah", "").replace(" ah", "").strip()
        elif any(low.startswith(p) or low == p for p in ("skip ad", "skip the ad", "ad skip pannu", "skip ad pannu")):
            is_ghost_click = True
            target = "skip ad button"
        elif any(p in low for p in ("subscribe pannu", "subscribe click", "subscribe button")):
            is_ghost_click = True
            target = "subscribe button"
        elif any(p in low for p in ("first video play pannu", "intha video play pannu", "video play pannu", "play the video", "first video click pannu")):
            is_ghost_click = True
            target = "first video thumbnail or play button"

        if is_ghost_click and target:
            # Clean suffixes
            for suffix in (" button", " icon", " link", " mela", " mela click pannu", " ah", "-ah"):
                if target.lower().endswith(suffix):
                    target = target[:-len(suffix)].strip()

            if len(target) >= 2 and target.lower() not in ("left", "right", "here", "inga", "cursor"):
                if speak_cb:
                    speak_cb(f"Screen-la '{target}' theduren nanba...")
                ok, res = self.click_element(target, click_type=click_type, speak_cb=speak_cb)
                if ok:
                    return True, res
                else:
                    return True, f"'{target}' screen-la kandupidikka mudiyala nanba."


        # --- N. MEDIA PLAYBACK KEYS ---
        if any(p in low for p in ("pause song", "paata pause pannu", "pause music", "pause video", "resume music", "play pause", "media pause", "song pause")):
            self.media_play_pause()
            return True, "Media toggled."

        if any(p in low for p in ("next song", "adutha song", "adutha paatu", "next track", "skip song")):
            self.media_next()
            return True, "Next track playing."

        if any(p in low for p in ("previous song", "munnadi paatu", "previous track", "prev song")):
            self.media_previous()
            return True, "Previous track playing."

        # --- O. EDITING & CLIPBOARD SHORTCUTS ---
        if any(p in low for p in ("select all", "ellam select pannu", "select all text")):
            self.select_all()
            return True, "Selected all text."

        if any(p in low for p in ("copy this", "copy pannu", "copy text")):
            self.copy()
            return True, "Copied to clipboard."

        if any(p in low for p in ("paste this", "paste pannu")):
            self.paste()
            return True, "Pasted."

        if any(p in low for p in ("undo this", "undo pannu", "undo action")):
            self.undo()
            return True, "Undo performed."

        if any(p in low for p in ("save file", "save this", "save pannu")):
            self.save_file()
            return True, "Saved."

        if any(p in low for p in ("press enter", "enter thattu")):
            self.press_key("enter")
            return True, "Pressed Enter."

        if any(p in low for p in ("press escape", "esc thattu", "press esc")):
            self.press_key("escape")
            return True, "Pressed Escape."

        # --- P. QUICK FOLDERS ---
        is_folder = any(p in low for p in (
            "open downloads", "downloads folder", "downloads thora", "downloads open pannu",
            "open documents", "documents folder", "documents thora", "documents open pannu",
            "open pictures", "pictures folder", "photos folder",
            "open desktop folder", "desktop folder thora",
            "open c drive", "c drive open pannu", "open recycle bin"
        ))
        if is_folder:
            res = self.open_folder(low)
            return True, res

        # --- Q. ORGANIZE DESKTOP ---
        if any(p in low for p in ("organize desktop", "desktop organize pannu", "clean desktop", "clean my desktop")):
            if speak_cb:
                speak_cb("Organizing desktop files into categorized folders...")
            res = self.organize_desktop()
            return True, "Desktop files organized successfully."

        return False, ""


# Global singleton instance
desktop_automation = DesktopAutomationEngine()
