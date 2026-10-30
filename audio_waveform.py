import math
import random
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QBrush, QPen
from PyQt6.QtWidgets import QWidget


class AuraAudioWaveform(QWidget):
    """
    Futuristic Sci-Fi Sound Equalizer / Waveform visualizer for Aura.
    Renders 48 glowing holographic frequency bars responsive to audio levels.
    """

    def __init__(self, parent=None, bar_count: int = 42):
        super().__init__(parent)
        self.setFixedHeight(54)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._bar_count = bar_count
        self._audio_level = 0.0
        self._phase = 0.0
        self._state = "LISTENING"
        self._bars = [0.1] * bar_count

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(24)  # ~40 FPS

    def set_audio_level(self, lvl: float):
        self._audio_level = max(0.0, min(1.0, float(lvl)))

    def set_state(self, state: str):
        self._state = (state or "LISTENING").upper()

    def _tick(self):
        self._phase += 0.12
        lvl = self._audio_level

        for i in range(self._bar_count):
            # Center-weighted bell curve
            dist_from_center = abs(i - self._bar_count / 2.0) / (self._bar_count / 2.0)
            bell = math.exp(-2.5 * dist_from_center * dist_from_center)

            # Harmonic wave oscillation
            wave = (
                math.sin(self._phase + i * 0.35) * 0.3 +
                math.cos(self._phase * 1.5 - i * 0.2) * 0.2 +
                0.5
            )

            if lvl > 0.05:
                # Active speech audio modulation with dynamic jitter
                target = bell * (lvl * 1.2 + random.uniform(0.0, 0.4 * lvl))
            else:
                # Ambient idle breathing wave
                speed = 0.25 if self._state == "THINKING" else 0.12
                target = bell * (0.12 + 0.14 * wave)

            # Smooth decay / lerp
            self._bars[i] += (target - self._bars[i]) * 0.4

        self._audio_level *= 0.88  # natural falloff
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        mid_y = h / 2.0
        bar_w = max(2.0, (w - (self._bar_count * 3)) / float(self._bar_count))

        # Center reference guide line
        pen_line = QPen(QColor(0, 240, 255, 40), 1.0)
        painter.setPen(pen_line)
        painter.drawLine(0, int(mid_y), w, int(mid_y))

        # Color based on state — Neon Cyberpunk Liquid Glass
        if self._state == "THINKING":
            top_col = QColor(57, 255, 20, 240)    # Neon green
            bot_col = QColor(0, 245, 255, 150)    # Cyan base
        elif self._state == "SPEAKING":
            top_col = QColor(255, 255, 255, 255)  # White burst
            bot_col = QColor(0, 245, 255, 200)    # Vivid cyan
        elif self._state == "MUTED":
            top_col = QColor(255, 34, 68, 200)    # Neon red
            bot_col = QColor(140, 10, 30, 80)     # Dim red
        else:
            top_col = QColor(0, 245, 255, 220)    # Electric cyan
            bot_col = QColor(57, 255, 20, 130)    # Neon green base

        for i, val in enumerate(self._bars):
            val = max(0.04, min(1.0, val))
            bar_h = val * (h * 0.88)
            bx = i * (bar_w + 3.0) + (w - (self._bar_count * (bar_w + 3.0))) / 2.0
            by = mid_y - (bar_h / 2.0)

            grad = QLinearGradient(bx, by, bx, by + bar_h)
            grad.setColorAt(0.0, top_col)
            grad.setColorAt(0.5, bot_col)
            grad.setColorAt(1.0, top_col)

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(bx, by, bar_w, bar_h), bar_w / 2.0, bar_w / 2.0)
