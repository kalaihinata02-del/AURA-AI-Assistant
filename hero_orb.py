"""
AURA Hero Orb & Acoustic Waveform Ribbon Widget
================================================
Renders the signature glowing portal orb with:
- Electric Cyan (#00f0ff), Royal Blue (#2979ff), and Neon Violet (#7c4dff) gradient rings
- Central illuminated futuristic 'A' chevron emblem
- Horizontal audio-reactive wave ribbons spreading left and right
- Interactive state-aware animations (LISTENING, THINKING, SPEAKING, MUTED)
"""

from __future__ import annotations

import math
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QRadialGradient,
    QLinearGradient, QFont, QPainterPath
)
from PyQt6.QtWidgets import QWidget


class AuraHeroOrb(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(230)
        self.setMinimumWidth(500)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._state = "LISTENING"
        self._target_audio = 0.0
        self._audio_lvl = 0.0
        self._phase = 0.0
        self._rot_angle = 0.0

        # 60 FPS animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(16)

    def set_state(self, state: str):
        self._state = (state or "LISTENING").upper()
        self.update()

    def set_audio_level(self, level: float):
        self._target_audio = max(0.0, min(1.0, float(level)))

    def _on_tick(self):
        # Smooth lerp
        self._audio_lvl += (self._target_audio - self._audio_lvl) * 0.32
        self._target_audio *= 0.86

        speed = 1.0
        if self._state == "THINKING":
            speed = 2.8
        elif self._state == "SPEAKING":
            speed = 1.6
        elif self._state == "MUTED":
            speed = 0.3

        self._phase = (self._phase + 0.055 * speed) % (2 * math.pi)
        self._rot_angle = (self._rot_angle + 1.2 * speed) % 360.0
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def _get_colors(self):
        if self._state == "THINKING":
            return (
                QColor(124, 77, 255),   # Neon Violet
                QColor(0, 240, 255),    # Cyan
                QColor(41, 121, 255),   # Royal Blue
            )
        elif self._state == "SPEAKING":
            return (
                QColor(0, 240, 255),    # Electric Cyan
                QColor(255, 255, 255),  # Pure White
                QColor(41, 121, 255),   # Royal Blue
            )
        elif self._state == "MUTED":
            return (
                QColor(255, 59, 48),    # Neon Red
                QColor(255, 120, 100),  # Soft red
                QColor(140, 10, 20),    # Dim Red
            )
        else:  # LISTENING / IDLE
            return (
                QColor(0, 240, 255),    # Electric Cyan
                QColor(41, 121, 255),   # Royal Blue
                QColor(124, 77, 255),   # Neon Violet
            )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0 - 12.0  # Slightly raised to leave room for status badge

        col_pri, col_sec, col_ter = self._get_colors()
        breath = 0.5 + 0.5 * math.sin(self._phase)
        orb_r = 58.0 + self._audio_lvl * 12.0

        # ── 1. Horizontal Sound Wave Ribbons (Left & Right) ──
        wave_amp = 18.0 + self._audio_lvl * 48.0
        ribbon_len = max(140.0, cx - orb_r - 20.0)

        for side in (-1, 1):  # -1 = left, 1 = right
            # Primary cyan wave
            path_wave = QPainterPath()
            start_x = cx + side * (orb_r + 4.0)
            end_x = cx + side * (orb_r + ribbon_len)
            path_wave.moveTo(start_x, cy)

            steps = 28
            for i in range(1, steps + 1):
                t = i / steps
                cur_x = start_x + (end_x - start_x) * t
                # Envelope: taper to zero at start and end
                envelope = math.sin(t * math.pi)
                wave_y = cy + math.sin(t * 3.5 * math.pi - self._phase * 1.8 * side) * wave_amp * envelope
                path_wave.lineTo(cur_x, wave_y)

            grad_wave = QLinearGradient(start_x, cy, end_x, cy)
            grad_wave.setColorAt(0.0, QColor(col_pri.red(), col_pri.green(), col_pri.blue(), 220))
            grad_wave.setColorAt(0.65, QColor(col_sec.red(), col_sec.green(), col_sec.blue(), 130))
            grad_wave.setColorAt(1.0, QColor(col_ter.red(), col_ter.green(), col_ter.blue(), 0))

            pen_wave = QPen(QBrush(grad_wave), 2.2)
            pen_wave.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_wave)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path_wave)

            # Secondary softer violet wave
            path_wave2 = QPainterPath()
            path_wave2.moveTo(start_x, cy)
            for i in range(1, steps + 1):
                t = i / steps
                cur_x = start_x + (end_x - start_x) * t
                envelope = math.sin(t * math.pi) ** 1.3
                wave_y = cy + math.cos(t * 4.2 * math.pi + self._phase * 1.5 * side) * (wave_amp * 0.65) * envelope
                path_wave2.lineTo(cur_x, wave_y)

            grad_wave2 = QLinearGradient(start_x, cy, end_x, cy)
            grad_wave2.setColorAt(0.0, QColor(col_ter.red(), col_ter.green(), col_ter.blue(), 160))
            grad_wave2.setColorAt(0.7, QColor(col_pri.red(), col_pri.green(), col_pri.blue(), 60))
            grad_wave2.setColorAt(1.0, QColor(col_sec.red(), col_sec.green(), col_sec.blue(), 0))

            pen_wave2 = QPen(QBrush(grad_wave2), 1.4)
            painter.setPen(pen_wave2)
            painter.drawPath(path_wave2)

        # ── 2. Center Orb Halo Ambient Glow ──
        halo_r = orb_r * (1.75 + breath * 0.25 + self._audio_lvl * 0.4)
        halo_grad = QRadialGradient(cx, cy, halo_r)
        halo_grad.setColorAt(0.0, QColor(col_pri.red(), col_pri.green(), col_pri.blue(), int(130 + self._audio_lvl * 90)))
        halo_grad.setColorAt(0.45, QColor(col_sec.red(), col_sec.green(), col_sec.blue(), int(65 + breath * 30)))
        halo_grad.setColorAt(0.8, QColor(col_ter.red(), col_ter.green(), col_ter.blue(), 18))
        halo_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(halo_grad))
        painter.drawEllipse(QPointF(cx, cy), halo_r, halo_r)

        # ── 3. Gradient Outer Ring ──
        outer_rect = QRectF(cx - orb_r, cy - orb_r, orb_r * 2, orb_r * 2)

        # Gradient ring stroke
        grad_ring = QLinearGradient(cx - orb_r, cy - orb_r, cx + orb_r, cy + orb_r)
        grad_ring.setColorAt(0.0, col_pri)
        grad_ring.setColorAt(0.5, col_sec)
        grad_ring.setColorAt(1.0, col_ter)

        pen_ring = QPen(QBrush(grad_ring), 4.2 + self._audio_lvl * 2.0)
        pen_ring.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_ring)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(outer_rect)

        # Inner fine tech ring
        r_tech = orb_r - 6.0
        pen_tech = QPen(QColor(col_pri.red(), col_pri.green(), col_pri.blue(), 80), 1.0, Qt.PenStyle.DotLine)
        painter.setPen(pen_tech)
        painter.drawEllipse(QPointF(cx, cy), r_tech, r_tech)

        # ── 4. Dark Translucent Glass Core ──
        core_r = orb_r - 9.0
        core_grad = QRadialGradient(cx, cy, core_r)
        core_grad.setColorAt(0.0, QColor(10, 16, 32, 230))
        core_grad.setColorAt(0.85, QColor(5, 8, 18, 245))
        core_grad.setColorAt(1.0, QColor(0, 0, 0, 255))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(core_grad))
        painter.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # ── 5. Stylized Illuminated 'A' Chevron Emblem ──
        painter.save()
        painter.translate(cx, cy)

        # Scaling factor based on orb radius
        s = orb_r * 0.42

        # Draw futuristic gradient 'A'
        a_path = QPainterPath()
        # Top apex
        a_path.moveTo(0, -s * 1.1)
        # Right outer leg
        a_path.lineTo(s * 0.95, s * 0.95)
        # Right inner slant
        a_path.lineTo(s * 0.52, s * 0.95)
        # Crossbar right
        a_path.lineTo(s * 0.32, s * 0.28)
        # Crossbar left
        a_path.lineTo(-s * 0.32, s * 0.28)
        # Left inner slant
        a_path.lineTo(-s * 0.52, s * 0.95)
        # Left outer leg
        a_path.lineTo(-s * 0.95, s * 0.95)
        a_path.closeSubpath()

        # Inner triangle hole
        hole_path = QPainterPath()
        hole_path.moveTo(0, -s * 0.45)
        hole_path.lineTo(s * 0.22, 0.05 * s)
        hole_path.lineTo(-s * 0.22, 0.05 * s)
        hole_path.closeSubpath()

        full_a = a_path.subtracted(hole_path)

        # 'A' Fill gradient: cyan to purple
        grad_a = QLinearGradient(-s, -s, s, s)
        grad_a.setColorAt(0.0, col_pri)
        grad_a.setColorAt(0.55, col_sec)
        grad_a.setColorAt(1.0, col_ter)

        # Ambient glow behind 'A'
        a_glow_pen = QPen(QColor(col_pri.red(), col_pri.green(), col_pri.blue(), 110), 5.0)
        painter.setPen(a_glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(full_a)

        # Sharp 'A' body
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad_a))
        painter.drawPath(full_a)

        painter.restore()

        # ── 6. Floating Status Pill Badge ("||| Listening...") ──
        badge_w = 124.0
        badge_h = 28.0
        badge_x = cx - badge_w / 2.0
        badge_y = cy + orb_r + 14.0

        badge_rect = QRectF(badge_x, badge_y, badge_w, badge_h)
        badge_bg = QColor(10, 16, 32, 220)
        badge_border = QColor(col_pri.red(), col_pri.green(), col_pri.blue(), 90)

        painter.setBrush(QBrush(badge_bg))
        painter.setPen(QPen(badge_border, 1.2))
        painter.drawRoundedRect(badge_rect, 14.0, 14.0)

        # 3 Animated equalizer bars on left of badge
        bar_x = badge_x + 18.0
        bar_y_mid = badge_y + badge_h / 2.0
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(col_pri))

        for idx, phase_off in enumerate((0.0, 1.8, 3.4)):
            h_bar = 4.0 + (math.sin(self._phase * 2.2 + phase_off) * 0.5 + 0.5) * (7.0 + self._audio_lvl * 10.0)
            painter.drawRoundedRect(QRectF(bar_x + idx * 5.0, bar_y_mid - h_bar / 2.0, 2.5, h_bar), 1.0, 1.0)

        # Badge Text
        state_labels = {
            "LISTENING": "Listening...",
            "THINKING": "Thinking...",
            "SPEAKING": "Speaking...",
            "MUTED": "Muted",
        }
        badge_text = state_labels.get(self._state, "Online")

        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255, 230))
        painter.drawText(QRectF(bar_x + 20.0, badge_y, badge_w - 38.0, badge_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, badge_text)
