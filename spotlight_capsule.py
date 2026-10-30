"""
Aura Spotlight Capsule — Global Floating Command Hub (Alt + Space)
==================================================================
A sleek, holographic Iron Man HUD floating command capsule that pops up globally
anywhere on the screen via Alt + Space. Supports direct typing, live voice listening,
response display, quick-action triggers, and smooth windowless animations.
"""

from __future__ import annotations

import os
import sys
import time
import platform
import threading
from typing import Callable, Optional

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QLabel,
    QPushButton, QGraphicsDropShadowEffect, QFrame, QScrollArea,
    QApplication
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve,
    QPoint, QRect
)
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QBrush, QPen, QRadialGradient,
    QLinearGradient, QKeyEvent
)


class MiniArcOrb(QWidget):
    """Miniature glowing Arc Reactor core that pulses with voice audio and AI state."""
    def __init__(self, parent=None, size: int = 34):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self._angle = 0.0
        self._audio_level = 0.0
        self._state = "IDLE"

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(25)  # 40 FPS

    def set_audio_level(self, level: float):
        self._audio_level = max(0.0, min(1.0, float(level)))
        self.update()

    def set_state(self, state: str):
        self._state = (state or "IDLE").upper()
        self.update()

    def _on_tick(self):
        speed = 4.0 if self._state in ("THINKING", "PROCESSING") else (2.0 if self._state == "SPEAKING" else 1.0)
        self._angle = (self._angle + speed) % 360.0
        # Smoothly decay audio level
        self._audio_level = max(0.0, self._audio_level - 0.04)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        r = min(w, h) / 2.0 - 2.0

        # Color palette by state
        if self._state == "LISTENING":
            core_col = QColor("#00f0ff")
            glow_col = QColor(0, 240, 255, 120)
        elif self._state == "SPEAKING":
            core_col = QColor("#a855f7")
            glow_col = QColor(168, 85, 247, 130)
        elif self._state in ("THINKING", "PROCESSING"):
            core_col = QColor("#c084fc")
            glow_col = QColor(192, 132, 252, 130)
        elif self._state == "MUTED":
            core_col = QColor("#ef4444")
            glow_col = QColor(239, 68, 68, 100)
        else:
            core_col = QColor("#00f0ff")
            glow_col = QColor(0, 240, 255, 60)

        # Outer ambient glow
        rad = QRadialGradient(cx, cy, r)
        rad.setColorAt(0.0, glow_col)
        rad.setColorAt(0.7, QColor(glow_col.red(), glow_col.green(), glow_col.blue(), 20))
        rad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(rad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx - r), int(cy - r), int(2 * r), int(2 * r))

        # Rotating outer notched ring
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self._angle)
        pen = QPen(core_col, 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        outer_r = r - 3.0
        # Draw 3 circular arcs
        for i in range(3):
            painter.drawArc(
                int(-outer_r), int(-outer_r), int(2 * outer_r), int(2 * outer_r),
                i * 120 * 16, 75 * 16
            )
        painter.restore()

        # Inner pulsing core with audio reaction
        pulse = 0.5 + 0.5 * self._audio_level
        inner_r = max(3.0, (r * 0.45) * (0.8 + 0.4 * pulse))

        core_grad = QRadialGradient(cx, cy, inner_r)
        core_grad.setColorAt(0.0, QColor(255, 255, 255, 240))
        core_grad.setColorAt(0.6, core_col)
        core_grad.setColorAt(1.0, QColor(core_col.red(), core_col.green(), core_col.blue(), 0))
        painter.setBrush(QBrush(core_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx - inner_r), int(cy - inner_r), int(2 * inner_r), int(2 * inner_r))


class GlobalHotkeyListener:
    """Zero-dependency Windows background listener for Alt + Space shortcut."""
    def __init__(self, callback: Callable[[], None], chord=("alt", "space")):
        self._callback = callback
        self._chord = chord
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if platform.system() != "Windows":
            return
        self.stop()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="aura-spotlight-hotkey", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.6)
        self._thread = None

    def _run(self):
        import ctypes
        user32 = ctypes.windll.user32
        VK_MENU = 0x12   # Alt key
        VK_SPACE = 0x20  # Space key

        was_down = False
        while not self._stop_event.is_set():
            alt_down = bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)
            space_down = bool(user32.GetAsyncKeyState(VK_SPACE) & 0x8000)
            is_chord = alt_down and space_down

            if is_chord and not was_down:
                was_down = True
                try:
                    self._callback()
                except Exception as e:
                    print(f"[Spotlight] Hotkey callback error: {e}")
            elif not is_chord:
                was_down = False

            time.sleep(0.035)  # ~28 Hz check


class AuraSpotlightCapsule(QWidget):
    """
    Holographic Floating Spotlight Capsule Widget.
    Toggled globally via Alt + Space.
    """
    submitted = pyqtSignal(str)
    mic_toggled = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent=None, on_submit: Optional[Callable[[str], None]] = None):
        super().__init__(parent)
        self._on_submit_callback = on_submit

        # Window properties: Topmost, frameless, popup tool window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._width = 680
        self._base_height = 58
        self._expanded = False

        self._init_ui()
        self._init_animations()
        self._init_hotkey()

    def _init_ui(self):
        self.setFixedSize(self._width, self._base_height)

        # Outer root layout
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(10, 10, 10, 10)
        root_lay.setSpacing(0)

        # Main Capsule Container Card
        self._card = QFrame(self)
        self._card.setObjectName("capsuleCard")
        self._card.setStyleSheet("""
            QFrame#capsuleCard {
                background: rgba(10, 14, 26, 0.94);
                border: 1.5px solid rgba(0, 240, 255, 0.55);
                border-radius: 20px;
            }
        """)

        # Drop shadow for ambient holographic glow
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(28)
        glow.setColor(QColor(0, 240, 255, 110))
        glow.setOffset(0, 4)
        self._card.setGraphicsEffect(glow)

        card_lay = QVBoxLayout(self._card)
        card_lay.setContentsMargins(14, 8, 14, 8)
        card_lay.setSpacing(8)

        # Top Bar: Orb + Input + Mic Button + Close Button
        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        top_row.setContentsMargins(0, 0, 0, 0)

        # Mini Arc Reactor Orb
        self._orb = MiniArcOrb(self, size=32)
        top_row.addWidget(self._orb, 0, Qt.AlignmentFlag.AlignVCenter)

        # Input field
        self._input = QLineEdit(self)
        self._input.setPlaceholderText("Ask Aura anything, type command... (Esc to close)")
        self._input.setFont(QFont("Consolas", 12))
        self._input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #ffffff;
                selection-background-color: #00f0ff;
                selection-color: #000000;
                padding: 4px 2px;
            }
            QLineEdit::placeholder {
                color: rgba(160, 180, 210, 0.55);
                font-size: 11pt;
            }
        """)
        self._input.returnPressed.connect(self._on_enter_pressed)
        top_row.addWidget(self._input, 1, Qt.AlignmentFlag.AlignVCenter)

        # Voice Listening Mic Pill
        self._mic_btn = QPushButton("🎤", self)
        self._mic_btn.setFixedSize(30, 30)
        self._mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mic_btn.setToolTip("Toggle Microphone (Aura Listen)")
        self._mic_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 240, 255, 0.12);
                border: 1px solid rgba(0, 240, 255, 0.35);
                border-radius: 15px;
                color: #00f0ff;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(0, 240, 255, 0.28);
                border: 1px solid #00f0ff;
            }
        """)
        self._mic_btn.clicked.connect(self._on_mic_clicked)
        top_row.addWidget(self._mic_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        # Status badge label
        self._status_badge = QLabel("READY", self)
        self._status_badge.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self._status_badge.setStyleSheet("""
            QLabel {
                color: #00f0ff;
                background: rgba(0, 240, 255, 0.08);
                border: 1px solid rgba(0, 240, 255, 0.25);
                border-radius: 6px;
                padding: 3px 7px;
                letter-spacing: 1px;
            }
        """)
        top_row.addWidget(self._status_badge, 0, Qt.AlignmentFlag.AlignVCenter)

        # Close '✕' Button
        self._close_btn = QPushButton("✕", self)
        self._close_btn.setFixedSize(24, 24)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(180, 200, 220, 0.6);
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #ff4757;
            }
        """)
        self._close_btn.clicked.connect(self.hide_capsule)
        top_row.addWidget(self._close_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        card_lay.addLayout(top_row)

        # Expandable Response & Actions Pane (initially hidden)
        self._response_frame = QFrame(self)
        self._response_frame.setStyleSheet("background: transparent; border: none;")
        self._response_frame.setVisible(False)

        resp_lay = QVBoxLayout(self._response_frame)
        resp_lay.setContentsMargins(4, 4, 4, 4)
        resp_lay.setSpacing(6)

        # Divider line
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background: rgba(0, 240, 255, 0.2); max-height: 1px;")
        resp_lay.addWidget(div)

        # Live Response Text Label
        self._response_lbl = QLabel(self)
        self._response_lbl.setFont(QFont("Segoe UI", 10))
        self._response_lbl.setWordWrap(True)
        self._response_lbl.setStyleSheet("color: #d8e8f8; line-height: 140%;")
        resp_lay.addWidget(self._response_lbl)

        # Quick Action Chips Row
        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)
        chips_row.setContentsMargins(0, 4, 0, 0)

        quick_cmds = [
            ("⚡ Open Chrome", "Chrome open pannu"),
            ("🎵 Play Song", "YouTube la trending song podu"),
            ("🔊 Volume 70%", "Volume 70"),
            ("📷 Check Screen", "Screen paaru"),
        ]
        for label, cmd in quick_cmds:
            btn = QPushButton(label, self)
            btn.setFont(QFont("Consolas", 8))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 240, 255, 0.08);
                    border: 1px solid rgba(0, 240, 255, 0.22);
                    border-radius: 8px;
                    color: #88ddff;
                    padding: 3px 8px;
                }
                QPushButton:hover {
                    background: rgba(0, 240, 255, 0.22);
                    border: 1px solid #00f0ff;
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(lambda _, c=cmd: self._trigger_quick_command(c))
            chips_row.addWidget(btn)

        chips_row.addStretch(1)
        resp_lay.addLayout(chips_row)

        card_lay.addWidget(self._response_frame)
        root_lay.addWidget(self._card)

    def _init_animations(self):
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(160)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _init_hotkey(self):
        # Register global background hotkey listener for Alt + Space
        self._hotkey = GlobalHotkeyListener(self._on_hotkey_triggered)
        self._hotkey.start()

    def _on_hotkey_triggered(self):
        # Signal handler called from background thread: schedule on Qt main thread
        QTimer.singleShot(0, self.toggle_capsule)

    def toggle_capsule(self):
        if self.isVisible():
            self.hide_capsule()
        else:
            self.show_capsule()

    def show_capsule(self):
        # Position at top-center of active screen
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            x = int(geom.x() + (geom.width() - self._width) / 2)
            y = int(geom.y() + (geom.height() * 0.14))  # 14% down from top
            self.move(x, y)

        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self.activateWindow()

        # Fade in
        self._fade_anim.stop()
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

        self._input.setFocus()
        self._input.selectAll()

    def hide_capsule(self):
        def _finish_hide():
            self.hide()
            self.closed.emit()

        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(_finish_hide)
        self._fade_anim.start()

    def set_response_text(self, text: str):
        cleaned = (text or "").strip()
        if not cleaned:
            self._response_frame.setVisible(False)
            self._expanded = False
            self.setFixedSize(self._width, self._base_height)
            return

        # Show response and expand height
        self._response_lbl.setText(cleaned)
        self._response_frame.setVisible(True)
        self._expanded = True
        self.setFixedSize(self._width, 160)
        self.updateGeometry()

    def set_audio_level(self, level: float):
        self._orb.set_audio_level(level)

    def set_state(self, state: str):
        st = (state or "READY").upper()
        self._orb.set_state(st)
        self._status_badge.setText(st)

        color_map = {
            "LISTENING":  ("#00f0ff", "rgba(0, 240, 255, 0.12)", "rgba(0, 240, 255, 0.4)"),
            "SPEAKING":   ("#a855f7", "rgba(168, 85, 247, 0.12)", "rgba(168, 85, 247, 0.4)"),
            "THINKING":   ("#c084fc", "rgba(192, 132, 252, 0.12)", "rgba(192, 132, 252, 0.4)"),
            "PROCESSING": ("#00f0ff", "rgba(0, 240, 255, 0.12)", "rgba(0, 240, 255, 0.4)"),
            "MUTED":      ("#ef4444", "rgba(239, 68, 68, 0.12)", "rgba(239, 68, 68, 0.4)"),
        }
        col, bg, border = color_map.get(st, ("#00f0ff", "rgba(0, 240, 255, 0.08)", "rgba(0, 240, 255, 0.25)"))
        self._status_badge.setStyleSheet(f"""
            QLabel {{
                color: {col};
                background: {bg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 3px 7px;
                letter-spacing: 1px;
            }}
        """)

    def _on_enter_pressed(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self.set_state("THINKING")
        self.set_response_text(f"Working on: '{text}'...")

        self.submitted.emit(text)
        if self._on_submit_callback:
            try:
                self._on_submit_callback(text)
            except Exception as e:
                print(f"[Spotlight] Submit callback error: {e}")

    def _trigger_quick_command(self, cmd: str):
        self._input.setText(cmd)
        self._on_enter_pressed()

    def _on_mic_clicked(self):
        self.mic_toggled.emit()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.hide_capsule()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        if hasattr(self, "_hotkey") and self._hotkey:
            self._hotkey.stop()
        super().closeEvent(event)
