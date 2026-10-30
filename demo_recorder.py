# -*- coding: utf-8 -*-
"""
AURA - Pure Python Cinematic Demo Recorder
No OBS needed! mss + OpenCV + pyautogui
LinkedIn-ready video - fully automated!
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import time
import threading
import ctypes
import subprocess
from pathlib import Path
from datetime import datetime

import mss
import cv2
import numpy as np
import pyautogui
import pygetwindow as gw

pyautogui.FAILSAFE = False

# ── Config ────────────────────────────────────────────────────────────────────
OUTPUT_DIR  = Path(r"D:\Kalai\Assistant\demo_video")
FPS         = 30
AURA_TITLE  = "Aura"

# Demo sequence: (wait_before, command, label, wait_after)
DEMO_SCRIPT = [
    (3.0,  "",                            "=== Opening Shot - Aura Neon UI ===",  4.0),
    (1.0,  "what time is it",             "Time Query",                            5.0),
    (1.0,  "what is today date",          "Date Query",                            5.0),
    (1.5,  "tell me a cool tech fact",    "AI Knowledge Demo",                     9.0),
    (1.0,  "open youtube",                "App Launch Control",                    5.0),
    (2.5,  "what is on my screen",        "Jarvis Eye - Vision AI",               10.0),
    (1.5,  "take a screenshot",           "Screenshot Automation",                 5.0),
    (1.5,  "how much ram am I using",     "System Stats",                          6.0),
    (1.0,  "close youtube",               "App Close Control",                     4.0),
    (2.0,  "you are the best assistant",  "Personality Response",                  7.0),
    (1.0,  "",                            "=== Final Shot - Aura Logo Hold ===",  6.0),
]

# ── ANSI colors ───────────────────────────────────────────────────────────────
def _ansi():
    if sys.platform == "win32":
        try:
            ctypes.windll.kernel32.SetConsoleMode(
                ctypes.windll.kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

CY = "\033[96m"; GR = "\033[92m"; YL = "\033[93m"
RD = "\033[91m"; MG = "\033[95m"; WT = "\033[97m"
DIM = "\033[2m"; RST = "\033[0m"; BOLD = "\033[1m"

def log(msg, color=CY):
    ts = time.strftime("%H:%M:%S")
    print(f"{DIM}[{ts}]{RST} {color}{BOLD}[REC]{RST} {color}{msg}{RST}", flush=True)


# ── Screen Recorder ───────────────────────────────────────────────────────────
class ScreenRecorder:
    def __init__(self, output_path: str, fps: int = 30):
        self.output_path = output_path
        self.fps = fps
        self._running = False
        self._thread = None
        self._writer = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log(f"Recording STARTED -> {Path(self.output_path).name}", RD)

    def _loop(self):
        with mss.mss() as sct:
            mon = sct.monitors[1]          # Primary monitor
            w, h = mon["width"], mon["height"]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self._writer = cv2.VideoWriter(self.output_path, fourcc, self.fps, (w, h))
            frame_time = 1.0 / self.fps

            while self._running:
                t0 = time.perf_counter()
                try:
                    img   = sct.grab(mon)
                    frame = np.array(img)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    self._writer.write(frame)
                except Exception as e:
                    log(f"Frame error: {e}", RD)

                elapsed = time.perf_counter() - t0
                sleep   = frame_time - elapsed
                if sleep > 0:
                    time.sleep(sleep)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        if self._writer:
            self._writer.release()
        log(f"Recording SAVED -> {self.output_path}", GR)


# ── Aura Window ───────────────────────────────────────────────────────────────
# ── Aura Window ───────────────────────────────────────────────────────────────
def get_aura_window():
    try:
        wins = [w for w in gw.getAllWindows() if "aura" in (w.title or "").lower()]
        return wins[0] if wins else None
    except Exception:
        return None

def focus_aura() -> bool:
    try:
        w = get_aura_window()
        if w:
            if w.isMinimized:
                w.restore()
            time.sleep(0.3)
            w.activate()
            time.sleep(0.4)
            w.maximize()
            time.sleep(0.6)
            log("Aura window focused + maximized", GR)
            return True
        else:
            log("Aura window title not directly captured — please ensure Aura is visible on screen!", YL)
            return True  # Proceed anyway!
    except Exception as e:
        log(f"Focus error: {e}", YL)
        return True


def send_to_aura(command: str):
    if not command.strip():
        return
    try:
        w = get_aura_window()
        if w:
            cx = w.left + w.width  // 2
            cy = w.top  + w.height - 55
        else:
            sw, sh = pyautogui.size()
            cx = sw // 2
            cy = sh - 55
        pyautogui.click(cx, cy)
        time.sleep(0.25)

        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("delete")
        time.sleep(0.15)
        pyautogui.typewrite(command, interval=0.045)
        time.sleep(0.3)
        pyautogui.press("enter")
        log(f"Sent -> '{command}'", CY)
    except Exception as e:
        log(f"Send error: {e}", RD)



# ── Countdown ─────────────────────────────────────────────────────────────────
def countdown(n: int):
    for i in range(n, 0, -1):
        print(f"\r{YL}{BOLD}  Demo starts in: {i}s ...{RST}   ", end="", flush=True)
        time.sleep(1)
    print(f"\r{GR}{BOLD}  ACTION! Recording started!{RST}              ")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    _ansi()

    print(f"""
{CY}{'='*56}{RST}
{MG}   AURA DEMO RECORDER - Pure Python (No OBS!){RST}
{GR}   mss + OpenCV screen capture | auto commands{RST}
{CY}{'='*56}{RST}
""")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = str(OUTPUT_DIR / f"aura_demo_{ts}.mp4")
    log(f"Output: {out_file}", YL)

    # Focus Aura
    log("Focusing Aura window...", YL)
    if not focus_aura():
        return

    # Warn user
    print()
    log("DO NOT touch mouse or keyboard during demo!", RD)
    log("Sit back — Aura will demo itself!", GR)
    countdown(5)

    # Start recording
    rec = ScreenRecorder(out_file, fps=FPS)
    rec.start()
    time.sleep(1.2)

    # Run demo
    total = len(DEMO_SCRIPT)
    print()
    log(f"Running {total} demo sequences...", MG)
    print(f"{DIM}{'─'*56}{RST}")

    for idx, (wb, cmd, lbl, wa) in enumerate(DEMO_SCRIPT, 1):
        print(f"\n{YL}[{idx:02d}/{total}]{RST} {WT}{lbl}{RST}")
        if wb > 0:
            time.sleep(wb)
        if cmd.strip():
            send_to_aura(cmd)
        if wa > 0:
            print(f"  {DIM}Waiting {wa}s...{RST}")
            time.sleep(wa)

    # Final hold
    log("Sequences done! Final 3s hold...", GR)
    time.sleep(3)
    rec.stop()

    print(f"""
{GR}{'='*56}
  VIDEO COMPLETE!
{'='*56}{RST}

  {YL}{out_file}{RST}

  {WT}Next Steps:{RST}
  {CY}1.{RST} Check the MP4 file
  {CY}2.{RST} Edit in Clipchamp / CapCut / DaVinci
  {CY}3.{RST} Add cyberpunk background music
  {CY}4.{RST} Upload to LinkedIn!

{MG}  AURA - Built by Kalai{RST}
""")

    try:
        subprocess.Popen(f'explorer "{str(OUTPUT_DIR)}"')
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RD}Cancelled.{RST}")
