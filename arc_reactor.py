import math
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QRadialGradient, 
    QConicalGradient, QLinearGradient, QFont, QPainterPath
)
from PyQt6.QtWidgets import QWidget


class AuraArcReactor(QWidget):
    """
    Futuristic Iron Man / Jarvis Arc Reactor Widget for Aura AI Assistant.
    Features:
    - Multi-ring counter-rotating HUD elements
    - 12 segmented magnetic coil nodes
    - Audio-reactive pulsing holographic core (scales with mic/speech volume)
    - State-aware energy signatures (LISTENING, SPEAKING, THINKING, MUTED)
    - Sci-Fi tech reticles and degree markers
    """

    def __init__(self, parent=None, size: int = 280):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._state = "LISTENING"
        self._target_audio_level = 0.0
        self._audio_level = 0.0
        self._pulse_phase = 0.0
        self._angle_outer = 0.0
        self._angle_inner = 0.0
        self._angle_core = 0.0
        self._coils = 10
        self._ripple_radii = []

        # 60 FPS animation timer
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_tick)
        self._anim_timer.start(16)

    def set_state(self, state: str):
        self._state = (state or "LISTENING").upper()
        self.update()

    def set_audio_level(self, level: float):
        self._target_audio_level = max(0.0, min(1.0, float(level)))

    def _on_tick(self):
        # Smooth lerp audio level for organic reactivity
        self._audio_level += (self._target_audio_level - self._audio_level) * 0.35
        self._target_audio_level *= 0.88  # natural decay

        speed_mult = 1.0
        if self._state == "THINKING":
            speed_mult = 3.5
        elif self._state == "SPEAKING":
            speed_mult = 1.6
        elif self._state == "MUTED":
            speed_mult = 0.2

        self._angle_outer = (self._angle_outer + 0.6 * speed_mult) % 360
        self._angle_inner = (self._angle_inner - 1.2 * speed_mult) % 360
        self._angle_core = (self._angle_core + 2.0 * speed_mult) % 360
        self._pulse_phase = (self._pulse_phase + 0.06 * speed_mult) % (2 * math.pi)

        # Trigger ripples during speaking
        if self._state == "SPEAKING" and self._audio_level > 0.15 and len(self._ripple_radii) < 4:
            if not self._ripple_radii or self._ripple_radii[-1][0] > 35:
                self._ripple_radii.append([25.0, 1.0])

        # Update ripples
        new_ripples = []
        for r, alpha in self._ripple_radii:
            r += 1.8
            alpha -= 0.03
            if alpha > 0.0 and r < self.width() * 0.48:
                new_ripples.append([r, alpha])
        self._ripple_radii = new_ripples

        self.update()

    def _get_palette(self):
        # Neon Cyberpunk Liquid Glass palette
        if self._state == "THINKING":
            return (
                QColor(57, 255, 20),    # Neon Green primary
                QColor(0, 245, 255),    # Electric Cyan secondary
                QColor(120, 255, 80),   # Bright green core
            )
        elif self._state == "SPEAKING":
            return (
                QColor(0, 245, 255),    # Electric Cyan primary
                QColor(255, 255, 255),  # White energy burst
                QColor(0, 220, 255),    # Vivid cyan core
            )
        elif self._state == "MUTED":
            return (
                QColor(255, 34, 68),    # Neon Red
                QColor(255, 80, 100),   # Soft neon red
                QColor(180, 10, 30),    # Dim core
            )
        else:  # LISTENING / IDLE — signature Neon Cyberpunk
            return (
                QColor(0, 245, 255),    # Electric Cyan
                QColor(57, 255, 20),    # Neon Green accent
                QColor(0, 255, 220),    # Turquoise-cyan glow
            )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0
        max_r = min(cx, cy) - 6.0

        pri_col, sec_col, core_col = self._get_palette()
        breath = 0.5 + 0.5 * math.sin(self._pulse_phase)
        boost = self._audio_level * 0.4

        # 1. Outer Tech Ring (with tick marks and degree marks)
        r_outer = max_r
        pen_outer = QPen(QColor(pri_col.red(), pri_col.green(), pri_col.blue(), 60), 1.2)
        painter.setPen(pen_outer)
        painter.drawEllipse(QPointF(cx, cy), r_outer, r_outer)

        # 2. Outer Rotating Segmented Arcs
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self._angle_outer)
        pen_arc = QPen(QColor(pri_col.red(), pri_col.green(), pri_col.blue(), 180), 2.5)
        painter.setPen(pen_arc)
        arc_rect = QRectF(-r_outer, -r_outer, r_outer * 2, r_outer * 2)
        for i in range(4):
            start_deg = i * 90 + 10
            painter.drawArc(arc_rect, int(start_deg * 16), int(55 * 16))

        # Tech tick marks around perimeter
        pen_tick = QPen(QColor(sec_col.red(), sec_col.green(), sec_col.blue(), 120), 1.0)
        painter.setPen(pen_tick)
        for deg in range(0, 360, 15):
            rad = math.radians(deg)
            t_len = 5.0 if deg % 45 == 0 else 2.5
            x1 = (r_outer - 1.0) * math.cos(rad)
            y1 = (r_outer - 1.0) * math.sin(rad)
            x2 = (r_outer - 1.0 - t_len) * math.cos(rad)
            y2 = (r_outer - 1.0 - t_len) * math.sin(rad)
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        painter.restore()

        # 3. Audio Shockwave Ripples (during voice activity)
        for r_rip, alpha_rip in self._ripple_radii:
            a_int = max(0, min(255, int(alpha_rip * 160)))
            pen_rip = QPen(QColor(pri_col.red(), pri_col.green(), pri_col.blue(), a_int), 1.5)
            painter.setPen(pen_rip)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), r_rip, r_rip)

        # 4. Iron Man 10-Node Arc Reactor Magnetic Coils
        r_coils = max_r * 0.72
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self._angle_inner)

        # Ring track behind coils
        pen_track = QPen(QColor(pri_col.red(), pri_col.green(), pri_col.blue(), 90), 8.0)
        pen_track.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen_track)
        coil_rect = QRectF(-r_coils, -r_coils, r_coils * 2, r_coils * 2)
        painter.drawEllipse(coil_rect)

        # Draw segmented copper/energy coils
        step_deg = 360.0 / self._coils
        for i in range(self._coils):
            angle = i * step_deg
            rad = math.radians(angle)
            nx = r_coils * math.cos(rad)
            ny = r_coils * math.sin(rad)

            # Node coil block
            painter.save()
            painter.translate(nx, ny)
            painter.rotate(angle + 90)

            node_col = QColor(core_col.red(), core_col.green(), core_col.blue(), int(200 + 55 * breath))
            painter.setBrush(QBrush(node_col))
            painter.setPen(QPen(QColor(255, 255, 255, 220), 1.0))
            painter.drawRoundedRect(QRectF(-7, -4, 14, 8), 2, 2)
            painter.restore()
        painter.restore()

        # 5. Inner Counter-Rotating Reticle Ring
        r_inner = max_r * 0.48
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(-self._angle_inner * 1.5)
        pen_reticle = QPen(QColor(sec_col.red(), sec_col.green(), sec_col.blue(), 140), 1.5, Qt.PenStyle.DashLine)
        painter.setPen(pen_reticle)
        painter.drawEllipse(QPointF(0, 0), r_inner, r_inner)

        # Reticle triangle pointer
        painter.setBrush(QBrush(QColor(pri_col.red(), pri_col.green(), pri_col.blue(), 200)))
        painter.setPen(Qt.PenStyle.NoPen)
        for tri_deg in (0, 120, 240):
            trad = math.radians(tri_deg)
            tx = (r_inner + 4) * math.cos(trad)
            ty = (r_inner + 4) * math.sin(trad)
            path = QPainterPath()
            path.moveTo(tx, ty)
            path.lineTo(tx - 4 * math.sin(trad), ty + 4 * math.cos(trad))
            path.lineTo(tx + 4 * math.sin(trad), ty - 4 * math.cos(trad))
            path.closeSubpath()
            painter.drawPath(path)
        painter.restore()

        # 6. Center Energy Reactor Core (Glowing Radial Gradient)
        core_radius = max_r * (0.28 + 0.08 * breath + boost * 0.16)

        grad = QRadialGradient(QPointF(cx, cy), core_radius * 1.6)
        grad.setColorAt(0.0, QColor(255, 255, 255, 255))
        grad.setColorAt(0.25, QColor(core_col.red(), core_col.green(), core_col.blue(), 240))
        grad.setColorAt(0.65, QColor(pri_col.red(), pri_col.green(), pri_col.blue(), 120))
        grad.setColorAt(1.0, QColor(pri_col.red(), pri_col.green(), pri_col.blue(), 0))

        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), core_radius * 1.6, core_radius * 1.6)

        # Core center geometric aperture
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self._angle_core)
        pen_aperture = QPen(QColor(255, 255, 255, 230), 1.6)
        painter.setPen(pen_aperture)
        painter.setBrush(QBrush(QColor(0, 20, 40, 180)))
        ap_r = core_radius * 0.65
        painter.drawPolygon([
            QPointF(ap_r * math.cos(math.radians(a)), ap_r * math.sin(math.radians(a)))
            for a in range(0, 360, 60)
        ])

        # Micro glowing core dot
        painter.setBrush(QBrush(QColor(255, 255, 255, 255)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(0, 0), ap_r * 0.35, ap_r * 0.35)
        painter.restore()

        # 7. Sci-Fi HUD Label text under reactor
        painter.setPen(QColor(pri_col.red(), pri_col.green(), pri_col.blue(), 180))
        font = QFont("Consolas", 8, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        painter.setFont(font)
        status_text = f"// AURA CORE : {self._state} //"
        painter.drawText(QRectF(0, h - 18, w, 18), Qt.AlignmentFlag.AlignCenter, status_text)
