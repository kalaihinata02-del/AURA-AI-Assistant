"""
AURA Executive Cyber Dashboard Widgets
======================================
Custom PyQt6 Glassmorphism Widgets matching the high-end AURA executive mockup:
1. Left Navigation Sidebar with Quick Actions
2. Animated Sparkline Wave Charts (CPU, RAM, Disk, Network)
3. 2x2 System Status Grid
4. Wake Word Toggle Card
5. Recent Activities Timeline
6. Mountain Scenic Inspiration Banner Card
7. 4 Featured Capabilities Glass Bento Cards
"""

from __future__ import annotations

import os
import sys
import math
import time
import random
from pathlib import Path
from typing import Optional, Callable

import psutil
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QSize, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QRadialGradient,
    QLinearGradient, QFont, QPainterPath, QPixmap, QIcon
)
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSizePolicy, QGraphicsDropShadowEffect
)

BASE_DIR = Path(__file__).resolve().parent


# ── Color Palette Constants ───────────────────────────────────────────────────
C_BG_GLASS   = "rgba(11, 18, 33, 0.72)"
C_BORDER     = "rgba(41, 121, 255, 0.16)"
C_BORDER_HOV = "rgba(0, 240, 255, 0.40)"
C_CYAN       = "#00f0ff"
C_BLUE       = "#2979ff"
C_VIOLET     = "#7c4dff"
C_GREEN      = "#00e676"
C_WHITE      = "#ffffff"
C_TEXT_MUTED = "#94a3b8"
C_TEXT_DIM   = "#64748b"


# -----------------------------------------------------------------------------
# 1. ANIMATED MINI SPARKLINE CHART
# -----------------------------------------------------------------------------
class AuraSparkline(QWidget):
    """Draws a live mini acoustic/metric waveform sparkline."""
    def __init__(self, color: QColor, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setMinimumWidth(60)
        self.color = color
        self._history = [random.uniform(0.2, 0.5) for _ in range(16)]
        self._phase = random.uniform(0, math.pi)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(120)

    def push_value(self, val: float):
        norm = max(0.05, min(1.0, float(val) / 100.0))
        self._history.append(norm)
        if len(self._history) > 16:
            self._history.pop(0)
        self.update()

    def _tick(self):
        self._phase = (self._phase + 0.12) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        n = len(self._history)
        if n < 2:
            return

        step_x = w / float(n - 1)
        path = QPainterPath()
        path_fill = QPainterPath()

        points = []
        for i, val in enumerate(self._history):
            px = i * step_x
            # Add subtle organic wave oscillation
            osc = math.sin(self._phase + i * 0.4) * 2.5
            py = h - (val * (h - 8.0)) - 4.0 + osc
            py = max(2.0, min(h - 2.0, py))
            points.append(QPointF(px, py))

        path.moveTo(points[0])
        path_fill.moveTo(points[0])

        for i in range(1, len(points)):
            p0 = points[i - 1]
            p1 = points[i]
            cpx = (p0.x() + p1.x()) / 2.0
            path.cubicTo(cpx, p0.y(), cpx, p1.y(), p1.x(), p1.y())
            path_fill.cubicTo(cpx, p0.y(), cpx, p1.y(), p1.x(), p1.y())

        path_fill.lineTo(w, h)
        path_fill.lineTo(0, h)
        path_fill.closeSubpath()

        # Fill gradient
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor(self.color.red(), self.color.green(), self.color.blue(), 70))
        grad.setColorAt(1.0, QColor(self.color.red(), self.color.green(), self.color.blue(), 0))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path_fill)

        # Stroke line
        pen = QPen(self.color, 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)


# -----------------------------------------------------------------------------
# 2. LEFT SIDEBAR NAVIGATION WITH QUICK ACTIONS
# -----------------------------------------------------------------------------
class AuraSidebar(QWidget):
    nav_changed = pyqtSignal(str)
    quick_action_triggered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)
        self.setStyleSheet(f"""
            QWidget#AuraSidebar {{
                background: rgba(8, 13, 24, 0.85);
                border-right: 1px solid rgba(41, 121, 255, 0.12);
            }}
        """)
        self.setObjectName("AuraSidebar")

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 16, 14, 16)
        root.setSpacing(10)

        # ── 1. Logo Block ──
        logo_box = QHBoxLayout()
        logo_box.setSpacing(10)

        # Stylized glowing vector logo
        self._logo_icon = QLabel()
        self._logo_icon.setFixedSize(32, 32)
        self._logo_icon.setStyleSheet("background: transparent;")
        self._render_logo_icon()
        logo_box.addWidget(self._logo_icon)

        brand_lay = QVBoxLayout()
        brand_lay.setSpacing(1)
        lbl_brand = QLabel("AURA")
        lbl_brand.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_brand.setStyleSheet("color: #ffffff; letter-spacing: 2px;")
        lbl_sub = QLabel("Your AI Companion")
        lbl_sub.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        lbl_sub.setStyleSheet(f"color: {C_CYAN}; letter-spacing: 0.5px;")
        brand_lay.addWidget(lbl_brand)
        brand_lay.addWidget(lbl_sub)
        logo_box.addLayout(brand_lay)
        logo_box.addStretch()
        root.addLayout(logo_box)

        root.addSpacing(10)

        # ── 2. Navigation Items ──
        self._nav_btns = {}
        nav_items = [
            ("home", "Home", "🏠"),
            ("voice", "Voice Assistant", "🎙️"),
            ("apps", "Apps", "🔲"),
            ("tools", "Tools", "🔧"),
            ("settings", "Settings", "⚙️"),
        ]

        for nav_id, title, icon in nav_items:
            btn = QPushButton(f"  {icon}  {title}")
            btn.setCheckable(True)
            btn.setFixedHeight(38)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
            btn.clicked.connect(lambda _, nid=nav_id: self._select_nav(nid))
            self._nav_btns[nav_id] = btn
            root.addWidget(btn)

        self._select_nav("home")

        root.addSpacing(14)

        # ── 3. Quick Actions Section ──
        lbl_qa = QLabel("QUICK ACTIONS")
        lbl_qa.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_qa.setStyleSheet(f"color: {C_TEXT_DIM}; letter-spacing: 1px; padding-left: 4px;")
        root.addWidget(lbl_qa)

        quick_apps = [
            ("code", "VS Code", "Visual Studio Code", "#007acc", "💻"),
            ("chrome", "Chrome", "Google Chrome", "#ea4335", "🌐"),
            ("notepad", "Notepad", "Notepad", "#00bcd4", "📝"),
            ("terminal", "Terminal", "Terminal", "#8e24aa", "⌨️"),
            ("explorer", "File Explorer", "File Explorer", "#fbc02d", "📁"),
        ]

        for app_id, name, desc, color_hex, emoji_icon in quick_apps:
            btn_app = self._build_app_row(app_id, name, desc, color_hex, emoji_icon)
            root.addWidget(btn_app)

        root.addStretch()

        # ── 4. Bottom Quote Block ──
        quote_box = QFrame()
        quote_box.setStyleSheet("background: transparent; border: none;")
        q_lay = QVBoxLayout(quote_box)
        q_lay.setContentsMargins(4, 4, 4, 4)
        q_lay.setSpacing(2)

        q1 = QLabel("Smarter tools.")
        q1.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        q1.setStyleSheet(f"color: {C_TEXT_MUTED}; font-style: italic;")
        q2 = QLabel("Bigger dreams.")
        q2.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        q2.setStyleSheet(f"color: {C_TEXT_MUTED}; font-style: italic;")
        q_auth = QLabel("— AURA")
        q_auth.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        q_auth.setStyleSheet(f"color: {C_CYAN};")

        q_lay.addWidget(q1)
        q_lay.addWidget(q2)
        q_lay.addWidget(q_auth)
        root.addWidget(quote_box)

    def _render_logo_icon(self):
        pm = QPixmap(32, 32)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        grad = QLinearGradient(0, 0, 32, 32)
        grad.setColorAt(0.0, QColor(0, 240, 255))
        grad.setColorAt(1.0, QColor(124, 77, 255))

        path = QPainterPath()
        path.moveTo(16, 2)
        path.lineTo(30, 29)
        path.lineTo(21, 29)
        path.lineTo(16, 17)
        path.lineTo(11, 29)
        path.lineTo(2, 29)
        path.closeSubpath()

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(path)
        p.end()
        self._logo_icon.setPixmap(pm)

    def _build_app_row(self, app_id: str, name: str, desc: str, color_hex: str, emoji_icon: str) -> QPushButton:
        btn = QPushButton()
        btn.setFixedHeight(38)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 8px;
                text-align: left;
                padding-left: 6px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(41, 121, 255, 0.25);
            }}
        """)
        lay = QHBoxLayout(btn)
        lay.setContentsMargins(6, 2, 6, 2)
        lay.setSpacing(8)

        icon_lbl = QLabel(emoji_icon)
        icon_lbl.setFont(QFont("Segoe UI", 12))
        lay.addWidget(icon_lbl)

        txt_lay = QVBoxLayout()
        txt_lay.setSpacing(0)
        lbl_name = QLabel(name)
        lbl_name.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_name.setStyleSheet("color: #ffffff;")

        lbl_desc = QLabel(f"Open {desc}")
        lbl_desc.setFont(QFont("Segoe UI", 7))
        lbl_desc.setStyleSheet(f"color: {C_TEXT_DIM};")

        txt_lay.addWidget(lbl_name)
        txt_lay.addWidget(lbl_desc)
        lay.addLayout(txt_lay)
        lay.addStretch()

        btn.clicked.connect(lambda: self.quick_action_triggered.emit(app_id))
        return btn

    def _select_nav(self, active_id: str):
        for nid, btn in self._nav_btns.items():
            if nid == active_id:
                btn.setChecked(True)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 rgba(41, 121, 255, 0.32),
                            stop:1 rgba(0, 240, 255, 0.08));
                        color: #ffffff;
                        border: 1px solid rgba(0, 240, 255, 0.45);
                        border-left: 3px solid {C_CYAN};
                        border-radius: 9px;
                        font-weight: bold;
                        text-align: left;
                        padding-left: 10px;
                    }}
                """)
            else:
                btn.setChecked(False)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {C_TEXT_MUTED};
                        border: 1px solid transparent;
                        border-radius: 9px;
                        text-align: left;
                        padding-left: 10px;
                    }}
                    QPushButton:hover {{
                        background: rgba(255, 255, 255, 0.05);
                        color: #ffffff;
                        border: 1px solid rgba(41, 121, 255, 0.20);
                    }}
                """)
        self.nav_changed.emit(active_id)


# -----------------------------------------------------------------------------
# 3. INTERACTIVE WAKE WORD CARD
# -----------------------------------------------------------------------------
class WakeWordCard(QFrame):
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {C_BG_GLASS};
                border: 1px solid {C_BORDER};
                border-radius: 14px;
            }}
            QFrame:hover {{
                border: 1px solid {C_BORDER_HOV};
            }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)

        # Mic wave icon block
        icn_box = QLabel("🎙️")
        icn_box.setFont(QFont("Segoe UI", 14))
        lay.addWidget(icn_box)

        # Text labels
        txt_lay = QVBoxLayout()
        txt_lay.setSpacing(2)
        t_lbl = QLabel("Wake Word")
        t_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        t_lbl.setStyleSheet("color: #ffffff;")
        sub_lbl = QLabel('Say "Hey AURA" to activate')
        sub_lbl.setFont(QFont("Segoe UI", 8))
        sub_lbl.setStyleSheet(f"color: {C_TEXT_MUTED};")
        txt_lay.addWidget(t_lbl)
        txt_lay.addWidget(sub_lbl)
        lay.addLayout(txt_lay)
        lay.addStretch()

        # Toggle Switch
        self._toggle_btn = QPushButton("ON")
        self._toggle_btn.setFixedSize(44, 24)
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(True)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self._update_toggle_style(True)
        self._toggle_btn.clicked.connect(self._on_click)
        lay.addWidget(self._toggle_btn)

    def _on_click(self):
        state = self._toggle_btn.isChecked()
        self._update_toggle_style(state)
        self.toggled.emit(state)

    def _update_toggle_style(self, active: bool):
        if active:
            self._toggle_btn.setText("ON")
            self._toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {C_BLUE}, stop:1 {C_CYAN});
                    color: #ffffff;
                    border: none;
                    border-radius: 12px;
                }}
            """)
        else:
            self._toggle_btn.setText("OFF")
            self._toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255, 255, 255, 0.12);
                    color: {C_TEXT_DIM};
                    border: 1px solid rgba(255, 255, 255, 0.18);
                    border-radius: 12px;
                }}
            """)


# -----------------------------------------------------------------------------
# 4. RECENT ACTIVITIES CARD
# -----------------------------------------------------------------------------
class RecentActivitiesCard(QFrame):
    activity_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {C_BG_GLASS};
                border: 1px solid {C_BORDER};
                border-radius: 14px;
            }}
            QFrame:hover {{
                border: 1px solid {C_BORDER_HOV};
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("🕒  Recent Activities")
        lbl_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #ffffff;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        btn_view_all = QPushButton("View All →")
        btn_view_all.setFont(QFont("Segoe UI", 8))
        btn_view_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_view_all.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C_CYAN}; border: none; }}
            QPushButton:hover {{ text-decoration: underline; }}
        """)
        hdr.addWidget(btn_view_all)
        lay.addLayout(hdr)

        # Activity rows
        self._activities = [
            ("💻", "Opened Visual Studio Code", "2 minutes ago", "code"),
            ("🌐", "Opened Google Chrome", "5 minutes ago", "chrome"),
            ("📝", "Opened Notepad", "12 minutes ago", "notepad"),
            ("⚙️", "System Information", "15 minutes ago", "system info"),
            ("▲", "AURA Assistant started", "1 hour ago", "status"),
        ]

        self._row_widgets = []
        for icon, title, time_str, cmd in self._activities:
            row = self._build_row(icon, title, time_str, cmd)
            self._row_widgets.append(row)
            lay.addWidget(row)

    def add_activity(self, title: str, app_id: str = ""):
        """Dynamically prepend newly executed activity."""
        icon_map = {
            "code": "💻", "chrome": "🌐", "notepad": "📝",
            "terminal": "⌨️", "explorer": "📁", "spotify": "🎵"
        }
        icn = icon_map.get(app_id.lower(), "⚡")
        new_row = self._build_row(icn, title, "Just now", app_id)
        self.layout().insertWidget(1, new_row)

    def _build_row(self, icon: str, title: str, time_str: str, cmd: str) -> QWidget:
        row = QFrame()
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        row.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 2px 4px;
            }}
            QFrame:hover {{
                background: rgba(255, 255, 255, 0.04);
            }}
        """)
        rlay = QHBoxLayout(row)
        rlay.setContentsMargins(4, 3, 4, 3)
        rlay.setSpacing(10)

        lbl_icn = QLabel(icon)
        lbl_icn.setFont(QFont("Segoe UI", 10))
        rlay.addWidget(lbl_icn)

        txt_box = QVBoxLayout()
        txt_box.setSpacing(1)
        lbl_t = QLabel(title)
        lbl_t.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        lbl_t.setStyleSheet("color: #ffffff;")
        lbl_time = QLabel(time_str)
        lbl_time.setFont(QFont("Segoe UI", 7))
        lbl_time.setStyleSheet(f"color: {C_TEXT_DIM};")
        txt_box.addWidget(lbl_t)
        txt_box.addWidget(lbl_time)
        rlay.addLayout(txt_box)
        rlay.addStretch()

        arrow = QLabel("›")
        arrow.setFont(QFont("Segoe UI", 12))
        arrow.setStyleSheet(f"color: {C_TEXT_DIM};")
        rlay.addWidget(arrow)

        row.mousePressEvent = lambda e: self.activity_clicked.emit(cmd)
        return row


# -----------------------------------------------------------------------------
# 5. 2x2 SYSTEM STATUS METRIC CARD WITH SPARKLINE CHARTS
# -----------------------------------------------------------------------------
class SystemStatusCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {C_BG_GLASS};
                border: 1px solid {C_BORDER};
                border-radius: 14px;
            }}
            QFrame:hover {{
                border: 1px solid {C_BORDER_HOV};
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)

        # Header
        hdr = QLabel("⚡  System Status")
        hdr.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        hdr.setStyleSheet("color: #ffffff;")
        lay.addWidget(hdr)

        # 2x2 Grid
        grid = QGridLayout()
        grid.setSpacing(8)

        # CPU Tile
        self._cpu_lbl = QLabel("12%")
        self._cpu_chart = AuraSparkline(QColor(0, 240, 255))
        grid.addWidget(self._build_tile("💻 CPU Usage", self._cpu_lbl, self._cpu_chart), 0, 0)

        # Memory Tile
        self._mem_lbl = QLabel("38%")
        self._mem_chart = AuraSparkline(QColor(41, 121, 255))
        grid.addWidget(self._build_tile("🧠 Memory Usage", self._mem_lbl, self._mem_chart), 0, 1)

        # Disk Tile
        self._disk_lbl = QLabel("22%")
        self._disk_chart = AuraSparkline(QColor(124, 77, 255))
        grid.addWidget(self._build_tile("💾 Disk Usage", self._disk_lbl, self._disk_chart), 1, 0)

        # Network Tile
        self._net_lbl = QLabel("Connected")
        self._net_chart = AuraSparkline(QColor(0, 230, 118))
        grid.addWidget(self._build_tile("📶 Network", self._net_lbl, self._net_chart), 1, 1)

        lay.addLayout(grid)

        # Live poll timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_metrics)
        self._timer.start(2000)
        self._poll_metrics()

    def _build_tile(self, title: str, val_lbl: QLabel, chart: AuraSparkline) -> QFrame:
        tile = QFrame()
        tile.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
        """)
        t_lay = QVBoxLayout(tile)
        t_lay.setContentsMargins(10, 8, 10, 8)
        t_lay.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        lbl_t.setStyleSheet(f"color: {C_TEXT_MUTED};")
        t_lay.addWidget(lbl_t)

        val_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        val_lbl.setStyleSheet("color: #ffffff;")
        t_lay.addWidget(val_lbl)

        t_lay.addWidget(chart)
        return tile

    def _poll_metrics(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage("C:\\").percent if sys.platform == "win32" else 20

            self._cpu_lbl.setText(f"{int(cpu)}%")
            self._cpu_chart.push_value(cpu)

            self._mem_lbl.setText(f"{int(mem)}%")
            self._mem_chart.push_value(mem)

            self._disk_lbl.setText(f"{int(disk)}%")
            self._disk_chart.push_value(disk)

            self._net_lbl.setText("Connected")
            self._net_chart.push_value(random.uniform(20, 60))
        except Exception:
            pass


# -----------------------------------------------------------------------------
# 6. MOUNTAIN SCENIC INSPIRATION CARD
# -----------------------------------------------------------------------------
class QuoteMountainCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(105)
        self.setObjectName("QuoteMountainCard")

        bg_path = BASE_DIR / "assets" / "quote_mountain.jpg"
        if bg_path.exists():
            clean_p = str(bg_path).replace("\\", "/")
            self.setStyleSheet(f"""
                QFrame#QuoteMountainCard {{
                    background-image: url("{clean_p}");
                    background-position: center;
                    background-repeat: no-repeat;
                    border: 1px solid rgba(41, 121, 255, 0.20);
                    border-radius: 14px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#QuoteMountainCard {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(8, 14, 28, 0.9), stop:1 rgba(15, 25, 48, 0.9));
                    border: 1px solid rgba(41, 121, 255, 0.20);
                    border-radius: 14px;
                }}
            """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 12)
        lay.setSpacing(2)

        q_txt = QLabel('"The future belongs to those\nwho build it."')
        q_txt.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        q_txt.setStyleSheet("color: #ffffff; background: transparent; line-height: 1.3;")
        lay.addWidget(q_txt)

        b_row = QHBoxLayout()
        auth = QLabel("— AURA")
        auth.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        auth.setStyleSheet(f"color: {C_CYAN}; background: transparent;")
        b_row.addWidget(auth)
        b_row.addStretch()

        logo_small = QLabel("▲")
        logo_small.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        logo_small.setStyleSheet("color: rgba(0, 240, 255, 0.85); background: transparent;")
        b_row.addWidget(logo_small)
        lay.addLayout(b_row)


# -----------------------------------------------------------------------------
# 7. FEATURED CAPABILITIES BENTO SECTION (4 CARDS)
# -----------------------------------------------------------------------------
class FeaturedCapabilitiesSection(QWidget):
    card_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(140)
        self.setStyleSheet("background: transparent;")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # Section Title
        hdr = QLabel("★  Featured Capabilities")
        hdr.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C_CYAN}; letter-spacing: 0.5px;")
        root.addWidget(hdr)

        # 4 Cards Row
        row = QHBoxLayout()
        row.setSpacing(10)

        cards_data = [
            ("voice", "🎙️", "Voice Commands", "Control your PC with your voice"),
            ("ai", "🧠", "Smart Assistance", "Get instant answers and help"),
            ("apps", "🔲", "App Integration", "Open and manage your favorite apps"),
            ("tools", "🔧", "Productivity Tools", "Work smarter, not harder"),
        ]

        for cid, icon, title, desc in cards_data:
            c = self._build_card(cid, icon, title, desc)
            row.addWidget(c)

        root.addLayout(row)

    def _build_card(self, cid: str, icon: str, title: str, desc: str) -> QFrame:
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet(f"""
            QFrame {{
                background: {C_BG_GLASS};
                border: 1px solid {C_BORDER};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border: 1px solid {C_BORDER_HOV};
                background: rgba(18, 28, 52, 0.80);
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 10)
        lay.setSpacing(4)

        icn = QLabel(icon)
        icn.setFont(QFont("Segoe UI", 14))
        icn.setStyleSheet("background: transparent;")
        lay.addWidget(icn)

        t_lbl = QLabel(title)
        t_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        t_lbl.setStyleSheet("color: #ffffff; background: transparent;")
        lay.addWidget(t_lbl)

        d_lbl = QLabel(desc)
        d_lbl.setWordWrap(True)
        d_lbl.setFont(QFont("Segoe UI", 7))
        d_lbl.setStyleSheet(f"color: {C_TEXT_MUTED}; background: transparent;")
        lay.addWidget(d_lbl)
        lay.addStretch()

        arr_row = QHBoxLayout()
        arr_row.addStretch()
        arr = QLabel("→")
        arr.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        arr.setStyleSheet(f"color: {C_CYAN}; background: transparent;")
        arr_row.addWidget(arr)
        lay.addLayout(arr_row)

        card.mousePressEvent = lambda e: self.card_selected.emit(cid)
        return card
