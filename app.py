import sys
import html
import tempfile
import pyodbc
from datetime import date, datetime, timedelta
from pathlib import Path
import time
from collections import defaultdict

from database import connect_db, validate_screen_values, validate_sleep_values
from analytics import (build_buckets, get_app_totals, get_bucket_totals, get_category_totals,
                       get_period_range, percent_change, previous_period_range, sum_usage)
from automatic_tracker import classify_process, get_foreground_executable

from PySide6.QtCore import Qt, QRectF, QPointF, QTimer, QSize, Signal, QSettings
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QPainter, QPen, QBrush, QPainterPath,
                           QLinearGradient, QPixmap, QIcon, QPalette, QPolygonF)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QGridLayout, QStackedWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QComboBox, QLineEdit, QSpinBox, QDateEdit, QTimeEdit,
    QMessageBox, QTextEdit, QAbstractItemView, QAbstractSpinBox, QSizePolicy,
    QScrollArea, QButtonGroup, QStyledItemDelegate, QStyle, QStyleOptionViewItem, QToolTip
)

APP_NAME = "LifeTrack"

# ─────────────────────────────────────────────────────────────────────────────
#  TASARIM SİSTEMİ  (renkler, aralıklar, yazı ölçeği)
# ─────────────────────────────────────────────────────────────────────────────
# Tek vurgu rengi (mavi) + nötr siyah/gri/beyaz tonlar. İki tema: "dark" (siyah) ve "light" (beyaz).
PALETTES = {
    "dark": {
        "colors": dict(
            BG="#0b0b0d", SIDEBAR="#101012", PANEL="#151518", PANEL_ALT="#1c1c20", INPUT="#101012",
            BORDER="#2d2d33", BORDER_SOFT="#222226", TEXT="#f5f5f7", MUTED="#9a9aa3", SOFT="#cfcfd6",
            FAINT="#62626b", ACCENT="#3b82f6", ACCENT_HI="#6aa3ff", ACCENT_PRESS="#2a6be0",
            ON_ACCENT="#ffffff", ACCENT_SOFT="#13213d", SEL="#172641", ROW_ALT="#18181b",
            ROW_HOVER="#1e1e22", GRID="#26262b", TRACK="#26262b", DANGER="#f87171", DANGER_BG="#261515",
            DANGER_HOVER="#331b1b", DANGER_BORDER="#472626", BTN_HOVER="#25252a", BTN_BORDER_HOVER="#3b3b43",
            BTN_PRESS="#1a1a1d", DIS_BG="#121214", DIS_FG="#55555d", DIS_BORDER="#1f1f23",
            SCROLL="#34343b", SCROLL_HOVER="#4b4b54", BAR_TOP="#3b4f77", BAR_BOT="#2c3d5e", NAV_HOVER="#1a1a1e",
        ),
        "category": ["#60a5fa", "#93c5fd", "#3b82f6", "#bfdbfe", "#94a3b8", "#64748b"],
        "chart": ["#3b82f6", "#60a5fa", "#93c5fd", "#94a3b8", "#64748b"],
    },
    "light": {
        "colors": dict(
            BG="#f4f5f7", SIDEBAR="#ffffff", PANEL="#ffffff", PANEL_ALT="#f1f2f5", INPUT="#ffffff",
            BORDER="#d5d8de", BORDER_SOFT="#e4e6eb", TEXT="#0f1115", MUTED="#6b7280", SOFT="#3b4250",
            FAINT="#9ca3af", ACCENT="#2563eb", ACCENT_HI="#4f8cf7", ACCENT_PRESS="#1d4ed8",
            ON_ACCENT="#ffffff", ACCENT_SOFT="#e7effd", SEL="#e2ecfd", ROW_ALT="#f8f9fb",
            ROW_HOVER="#f0f3f9", GRID="#e6e8ed", TRACK="#e8eaef", DANGER="#dc2626", DANGER_BG="#fdeeee",
            DANGER_HOVER="#fbdede", DANGER_BORDER="#f3c4c4", BTN_HOVER="#e7e9ee", BTN_BORDER_HOVER="#c3c8d1",
            BTN_PRESS="#dde0e7", DIS_BG="#f3f4f6", DIS_FG="#a3a9b4", DIS_BORDER="#e5e7eb",
            SCROLL="#c7cbd3", SCROLL_HOVER="#a9afba", BAR_TOP="#bcd1f8", BAR_BOT="#9ebbf0", NAV_HOVER="#f1f2f5",
        ),
        "category": ["#2563eb", "#0284c7", "#1e3a8a", "#3b82f6", "#64748b", "#94a3b8"],
        "chart": ["#2563eb", "#3b82f6", "#60a5fa", "#94a3b8", "#64748b"],
    },
}
CATEGORY_NAMES = ["Sosyal medya", "Video / içerik", "Oyun", "İş / eğitim", "İletişim", "Diğer"]
CATEGORY_COLORS = {}   # tablo etiketleri ve kategori grafiği aynı renkleri kullanır
CHART_PALETTE = []
THEME = "dark"

# Pylance'in isimleri görebilmesi için varsayılan (koyu tema) değerleri açıkça tanımlıyoruz.
# set_palette() bunları çalışma anında seçilen temaya göre günceller.
BG = "#0b0b0d"
SIDEBAR = "#101012"
PANEL = "#151518"
PANEL_ALT = "#1c1c20"
INPUT = "#101012"
BORDER = "#2d2d33"
BORDER_SOFT = "#222226"
TEXT = "#f5f5f7"
MUTED = "#9a9aa3"
SOFT = "#cfcfd6"
FAINT = "#62626b"
ACCENT = "#3b82f6"
ACCENT_HI = "#6aa3ff"
ACCENT_PRESS = "#2a6be0"
ON_ACCENT = "#ffffff"
ACCENT_SOFT = "#13213d"
SEL = "#172641"
ROW_ALT = "#18181b"
ROW_HOVER = "#1e1e22"
GRID = "#26262b"
TRACK = "#26262b"
DANGER = "#f87171"
DANGER_BG = "#261515"
DANGER_HOVER = "#331b1b"
DANGER_BORDER = "#472626"
BTN_HOVER = "#25252a"
BTN_BORDER_HOVER = "#3b3b43"
BTN_PRESS = "#1a1a1d"
DIS_BG = "#121214"
DIS_FG = "#55555d"
DIS_BORDER = "#1f1f23"
SCROLL = "#34343b"
SCROLL_HOVER = "#4b4b54"
BAR_TOP = "#3b4f77"
BAR_BOT = "#2c3d5e"
NAV_HOVER = "#1a1a1e"


def set_palette(name):
    """Renk sabitlerini seçilen temaya göre günceller (çizimler her seferinde güncel değeri okur)."""
    global THEME
    if name not in PALETTES:
        name = "dark"
    THEME = name
    globals().update(PALETTES[name]["colors"])
    CATEGORY_COLORS.clear()
    CATEGORY_COLORS.update(zip(CATEGORY_NAMES, PALETTES[name]["category"]))
    CHART_PALETTE[:] = PALETTES[name]["chart"]


set_palette("dark")

TR_MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
             "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
TR_DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def fmt_minutes(minutes):
    minutes = max(0, int(minutes))
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours} sa {mins} dk"
    if hours:
        return f"{hours} sa"
    return f"{mins} dk"


def duration_between(bedtime, wake_time):
    start = datetime.strptime(bedtime, "%H:%M")
    end = datetime.strptime(wake_time, "%H:%M")
    if end <= start:
        end += timedelta(days=1)
    return int((end - start).total_seconds() // 60)


def repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def make_button(text, object_name="secondaryButton", slot=None):
    btn = QPushButton(text)
    btn.setObjectName(object_name)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if slot is not None:
        btn.clicked.connect(slot)
    return btn


def chart_font(size, weight=QFont.Weight.Normal):
    font = QFont(QApplication.font())
    font.setPointSizeF(size)
    font.setWeight(weight)
    return font


# ─────────────────────────────────────────────────────────────────────────────
#  İKONLAR (emoji / sembol fontuna bağımlı değil, çizilir)
# ─────────────────────────────────────────────────────────────────────────────
def icon_pixmap(kind, color, size=20, dpr=2.0):
    """20x20'lik ızgarada çizilmiş çizgi ikon; size ile ölçeklenir."""
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 20.0, size / 20.0)
    pen = QPen(QColor(color), 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    if kind == "home":
        for x, y in ((3, 3), (11, 3), (3, 11), (11, 11)):
            p.drawRoundedRect(QRectF(x, y, 6, 6), 1.8, 1.8)
    elif kind == "clock":
        p.drawEllipse(QRectF(2.5, 2.5, 15, 15))
        p.drawLine(QPointF(10, 6), QPointF(10, 10))
        p.drawLine(QPointF(10, 10), QPointF(13, 12))
    elif kind == "moon":
        outer = QPainterPath()
        outer.addEllipse(QRectF(3, 3, 14, 14))
        cut = QPainterPath()
        cut.addEllipse(QRectF(8, 1, 13, 13))
        p.drawPath(outer.subtracted(cut))
    elif kind == "chart":
        pen.setWidthF(2.4)
        p.setPen(pen)
        p.drawLine(QPointF(5, 16), QPointF(5, 11))
        p.drawLine(QPointF(10, 16), QPointF(10, 4.5))
        p.drawLine(QPointF(15, 16), QPointF(15, 8))
    elif kind == "monitor":
        p.drawRoundedRect(QRectF(2.5, 3.5, 15, 10.5), 2.2, 2.2)
        p.drawLine(QPointF(7, 17), QPointF(13, 17))
        p.drawLine(QPointF(10, 14), QPointF(10, 17))
    elif kind == "play":
        p.drawEllipse(QRectF(2.5, 2.5, 15, 15))
        tri = QPainterPath()
        tri.moveTo(8.4, 6.9)
        tri.lineTo(13.2, 10)
        tri.lineTo(8.4, 13.1)
        tri.closeSubpath()
        p.drawPath(tri)
    elif kind == "calendar":
        p.drawRoundedRect(QRectF(3, 4.5, 14, 12.5), 2.5, 2.5)
        p.drawLine(QPointF(3, 8.5), QPointF(17, 8.5))
        p.drawLine(QPointF(7, 2.8), QPointF(7, 6))
        p.drawLine(QPointF(13, 2.8), QPointF(13, 6))
    elif kind == "plus":
        p.drawLine(QPointF(10, 4), QPointF(10, 16))
        p.drawLine(QPointF(4, 10), QPointF(16, 10))
    elif kind == "sun":
        p.drawEllipse(QRectF(6.5, 6.5, 7, 7))
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0), (-.7, -.7), (.7, -.7), (-.7, .7), (.7, .7)):
            p.drawLine(QPointF(10 + dx * 5.6, 10 + dy * 5.6), QPointF(10 + dx * 8, 10 + dy * 8))
    elif kind == "inbox":
        p.drawRoundedRect(QRectF(2.5, 3.5, 15, 13), 2.5, 2.5)
        p.drawLine(QPointF(2.5, 11), QPointF(7, 11))
        p.drawLine(QPointF(13, 11), QPointF(17.5, 11))
        p.drawLine(QPointF(7, 11), QPointF(8, 13.5))
        p.drawLine(QPointF(13, 11), QPointF(12, 13.5))
        p.drawLine(QPointF(8, 13.5), QPointF(12, 13.5))
    p.end()
    return pm


class IconChip(QWidget):
    """Yuvarlatılmış, renkli zeminli küçük ikon rozeti (stat kartları için)."""
    def __init__(self, kind, color=None, size=38, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = QColor(ACCENT)
        bg.setAlpha(34)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(QRectF(self.rect()), 11, 11)
        pm = icon_pixmap(self.kind, ACCENT, 20)
        p.drawPixmap((self.width() - 20) // 2, (self.height() - 20) // 2, pm)


# ─────────────────────────────────────────────────────────────────────────────
#  GRAFİKLER
# ─────────────────────────────────────────────────────────────────────────────
class MiniBarChart(QWidget):
    """Dikey çubuk grafik: gradyanlı çubuklar, kesikli ızgara, hover ipucu."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.hover = -1
        self.setMinimumHeight(210)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def sizeHint(self):
        return QSize(400, self.minimumHeight())

    def set_items(self, items):
        self.items = items
        self.hover = -1
        self.update()

    def _geometry(self):
        left, right, top, bottom = 6, 6, 28, 32
        return left, right, top, bottom

    def mouseMoveEvent(self, event):
        if not self.items:
            return
        left, right, top, bottom = self._geometry()
        slot = (self.width() - left - right) / len(self.items)
        idx = int((event.position().x() - left) // slot) if slot > 0 else -1
        if not 0 <= idx < len(self.items):
            idx = -1
        if idx != self.hover:
            self.hover = idx
            self.update()
        if idx >= 0:
            label, value = self.items[idx]
            QToolTip.showText(event.globalPosition().toPoint(), f"{label}  ·  {fmt_minutes(value)}", self)
        else:
            QToolTip.hideText()

    def leaveEvent(self, event):
        self.hover = -1
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        left, right, top, bottom = self._geometry()
        chart_h, chart_w = h - top - bottom, w - left - right
        if not self.items:
            p.setPen(QColor(MUTED))
            p.setFont(chart_font(10))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Henüz rapor verisi yok")
            return
        max_val = max([v for _, v in self.items] + [1])

        for i in range(4):
            y = top + chart_h * i / 3
            pen = QPen(QColor(GRID if i < 3 else BORDER), 1,
                       Qt.PenStyle.DashLine if i < 3 else Qt.PenStyle.SolidLine)
            p.setPen(pen)
            p.drawLine(QPointF(left, y), QPointF(w - right, y))

        count = len(self.items)
        slot = chart_w / count
        bar_w = max(10.0, min(44.0, slot * 0.5))
        for i, (label, value) in enumerate(self.items):
            x = left + slot * i + (slot - bar_w) / 2
            bh = max(4.0, (value / max_val) * (chart_h - 12)) if value > 0 else 4.0
            y = top + chart_h - bh
            is_last, hovered = i == count - 1, i == self.hover
            if value <= 0:
                fill = QColor(BORDER)
            else:
                c1, c2 = (QColor(ACCENT_HI), QColor(ACCENT)) if is_last else (QColor(BAR_TOP), QColor(BAR_BOT))
                if hovered:
                    c1, c2 = c1.lighter(118), c2.lighter(118)
                grad = QLinearGradient(x, y, x, y + bh)
                grad.setColorAt(0, c1)
                grad.setColorAt(1, c2)
                fill = QBrush(grad)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fill)
            p.drawRoundedRect(QRectF(x, y, bar_w, bh), min(8, bar_w / 2), min(8, bar_w / 2))

            if value > 0 and (slot >= 52 or hovered or is_last):
                p.setPen(QColor(TEXT if (hovered or is_last) else SOFT))
                p.setFont(chart_font(8, QFont.Weight.DemiBold))
                text = f"{value / 60:.1f} sa" if value >= 60 else f"{value} dk"
                p.drawText(QRectF(x - 24, y - 21, bar_w + 48, 18),
                           Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, text)
            p.setPen(QColor(TEXT if hovered else MUTED))
            p.setFont(chart_font(8))
            p.drawText(QRectF(left + slot * i, h - bottom + 9, slot, 18),
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, label)


class HorizontalBarChart(QWidget):
    """Kategori / uygulama dağılımı (değerler dakika). color_map verilirse etikete göre renklenir."""
    ROW_H = 36

    def __init__(self, parent=None, color_map=None, empty_text="Bu dönem için veri yok"):
        super().__init__(parent)
        self.items = []
        self.color_map = color_map or {}
        self.empty_text = empty_text
        self.setFixedHeight(self.ROW_H * 5 + 8)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_items(self, items):
        self.items = list(items)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.items:
            p.setPen(QColor(MUTED))
            p.setFont(chart_font(10))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.empty_text)
            return
        width = self.width()
        label_w = min(140, int(width * 0.34))
        value_w = 76
        bar_w = max(20, width - label_w - value_w - 10)
        max_value = max(value for _, value in self.items) or 1
        label_font = chart_font(9)
        fm = QFontMetrics(label_font)
        for i, (label, value) in enumerate(self.items[:5]):
            y = 4 + i * self.ROW_H
            color = QColor(self.color_map.get(label, CHART_PALETTE[i % len(CHART_PALETTE)]))
            p.setPen(QColor(SOFT))
            p.setFont(label_font)
            p.drawText(QRectF(0, y, label_w - 12, self.ROW_H),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       fm.elidedText(label, Qt.TextElideMode.ElideRight, label_w - 12))
            track = QRectF(label_w, y + self.ROW_H / 2 - 5, bar_w, 10)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(TRACK))
            p.drawRoundedRect(track, 5, 5)
            fill_w = max(10.0, bar_w * value / max_value)
            grad = QLinearGradient(track.left(), 0, track.left() + fill_w, 0)
            grad.setColorAt(0, color.darker(125))
            grad.setColorAt(1, color)
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(QRectF(track.left(), track.top(), fill_w, 10), 5, 5)
            p.setPen(QColor(TEXT))
            p.setFont(chart_font(9, QFont.Weight.DemiBold))
            p.drawText(QRectF(label_w + bar_w + 10, y, value_w, self.ROW_H),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, fmt_minutes(value))


# ─────────────────────────────────────────────────────────────────────────────
#  KÜÇÜK BİLEŞENLER
# ─────────────────────────────────────────────────────────────────────────────
class StatCard(QFrame):
    """Üstte başlık + ikon rozeti, ortada büyük değer, altta açıklama."""
    def __init__(self, title, value="—", hint="", accent=ACCENT, icon="monitor"):
        super().__init__()
        self.setObjectName("statCard")
        self.setMinimumHeight(128)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(0)
        top = QHBoxLayout()
        top.setSpacing(8)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardCaption")
        self.title_label.setWordWrap(True)
        top.addWidget(self.title_label, 1, Qt.AlignmentFlag.AlignTop)
        top.addWidget(IconChip(icon, accent), 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)
        layout.addSpacing(6)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")
        self.value_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.value_label)
        layout.addSpacing(2)
        self.hint_label = QLabel(hint)
        self.hint_label.setObjectName("muted")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)
        layout.addStretch(1)

    def set_value(self, value, hint=None):
        self.value_label.setText(value)
        if hint is not None:
            self.hint_label.setText(hint)


class SegmentedControl(QFrame):
    """QComboBox yerine geçen dönem seçici; currentIndex() / currentIndexChanged aynı çalışır."""
    currentIndexChanged = Signal(int)

    def __init__(self, labels, parent=None):
        super().__init__(parent)
        self.setObjectName("segmented")
        self._index = 0
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = []
        for i, text in enumerate(labels):
            b = QPushButton(text)
            b.setObjectName("segButton")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.group.addButton(b, i)
            lay.addWidget(b)
            self.buttons.append(b)
        self.buttons[0].setChecked(True)
        self.group.idClicked.connect(self._clicked)

    def _clicked(self, i):
        if i != self._index:
            self._index = i
            self.currentIndexChanged.emit(i)

    def currentIndex(self):
        return self._index

    def setCurrentIndex(self, i):
        self.buttons[i].setChecked(True)
        self._clicked(i)


class CategoryPillDelegate(QStyledItemDelegate):
    """Kategori hücresini renkli hap (pill) etiketi olarak çizer."""
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        text = opt.text
        opt.text = ""
        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
        color = QColor(CATEGORY_COLORS.get(text, MUTED))
        font = chart_font(8.5, QFont.Weight.DemiBold)
        fm = QFontMetrics(font)
        width = min(fm.horizontalAdvance(text) + 24, opt.rect.width() - 16)
        rect = QRectF(opt.rect.left() + 12, opt.rect.center().y() - 12, width, 24)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = QColor(color)
        bg.setAlpha(38)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, 12, 12)
        painter.setPen(color)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter,
                         fm.elidedText(text, Qt.TextElideMode.ElideRight, int(width) - 14))
        painter.restore()


# ─────────────────────────────────────────────────────────────────────────────
#  DİYALOGLAR
# ─────────────────────────────────────────────────────────────────────────────
class BaseDialog(QDialog):
    """Ortak diyalog iskeleti: başlık, alt başlık, etiket-üstte alanlar, buton satırı."""
    def __init__(self, parent, title, subtitle, width=480):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(width)
        self.setModal(True)
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(30, 28, 30, 26)
        self.outer.setSpacing(0)
        head = QLabel(title)
        head.setObjectName("dialogTitle")
        sub = QLabel(subtitle)
        sub.setObjectName("muted")
        sub.setWordWrap(True)
        self.outer.addWidget(head)
        self.outer.addSpacing(4)
        self.outer.addWidget(sub)
        self.outer.addSpacing(22)
        self.body = QVBoxLayout()
        self.body.setSpacing(16)
        self.outer.addLayout(self.body)

    def _field(self, label, widget):
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        cap = QLabel(label)
        cap.setObjectName("fieldLabel")
        lay.addWidget(cap)
        if not isinstance(widget, QTextEdit):
            widget.setMinimumHeight(42)
        if isinstance(widget, (QSpinBox, QTimeEdit)) and widget.lineEdit() is not None:
            widget.lineEdit().setTextMargins(13, 0, 0, 0)  # QSS padding iç editöre uygulanmıyor
        lay.addWidget(widget)
        lay.addStretch(1)
        return box

    def add_fields(self, *pairs):
        if len(pairs) == 1:
            self.body.addWidget(self._field(*pairs[0]))
            return
        row = QHBoxLayout()
        row.setSpacing(14)
        for pair in pairs:
            row.addWidget(self._field(*pair), 1, Qt.AlignmentFlag.AlignTop)
        self.body.addLayout(row)

    def add_buttons(self, save_text="Kaydet"):
        self.outer.addSpacing(24)
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addStretch(1)
        cancel = make_button("Vazgeç", "secondaryButton", self.reject)
        save = make_button(save_text, "primaryButton", self.accept)
        save.setDefault(True)
        row.addWidget(cancel)
        row.addWidget(save)
        self.outer.addLayout(row)


class RecordDialog(BaseDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent,
                         "Kullanım kaydını düzenle" if record else "Yeni kullanım kaydı",
                         "Hangi cihazda, ne kadar süre geçirdiğini ekle.")
        self.record = record
        self.day = QDateEdit()
        self.day.setCalendarPopup(True)
        self.day.setDisplayFormat("dd.MM.yyyy")
        self.day.setDate(date.today())
        self.device = QComboBox()
        self.device.addItems(["Telefon", "Bilgisayar", "Televizyon", "Tablet", "Diğer"])
        self.category = QComboBox()
        self.category.addItems(["Sosyal medya", "Video / içerik", "Oyun", "İş / eğitim", "İletişim", "Diğer"])
        self.app_name = QLineEdit()
        self.app_name.setPlaceholderText("Örn. Instagram, TikTok, YouTube")
        self.minutes = QSpinBox()
        self.minutes.setRange(1, 1440)
        self.minutes.setSuffix(" dakika")
        self.note = QTextEdit()
        self.note.setFixedHeight(78)
        self.note.setPlaceholderText("İsteğe bağlı kısa not")

        self.add_fields(("Tarih", self.day), ("Cihaz", self.device))
        self.add_fields(("Kategori", self.category), ("Süre", self.minutes))
        self.add_fields(("Uygulama / etkinlik", self.app_name))
        self.add_fields(("Not", self.note))
        self.add_buttons()

        if record:
            self.day.setDate(date.fromisoformat(record["record_date"]))
            self.device.setCurrentText(record["device"])
            self.category.setCurrentText(record["category"])
            self.app_name.setText(record["app_name"])
            self.minutes.setValue(record["minutes"])
            self.note.setPlainText(record["note"])

    def values(self):
        return (
            self.day.date().toString("yyyy-MM-dd"),
            self.device.currentText(),
            self.category.currentText(),
            self.app_name.text().strip(),
            self.minutes.value(),
            self.note.toPlainText().strip()
        )


class SleepDialog(BaseDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent,
                         "Uyku kaydını düzenle" if record else "Yeni uyku kaydı",
                         "Yatış ve kalkış saatini gir; süre otomatik hesaplanır.")
        self.record = record
        self.day = QDateEdit()
        self.day.setCalendarPopup(True)
        self.day.setDisplayFormat("dd.MM.yyyy")
        self.day.setDate(date.today())
        self.bed = QTimeEdit()
        self.bed.setDisplayFormat("HH:mm")
        self.bed.setTime(datetime.strptime("23:30", "%H:%M").time())
        self.wake = QTimeEdit()
        self.wake.setDisplayFormat("HH:mm")
        self.wake.setTime(datetime.strptime("07:30", "%H:%M").time())
        self.note = QLineEdit()
        self.note.setPlaceholderText("İsteğe bağlı not")

        box = QFrame()
        box.setObjectName("durationBox")
        bl = QHBoxLayout(box)
        bl.setContentsMargins(16, 12, 16, 12)
        cap = QLabel("Hesaplanan süre")
        cap.setObjectName("muted")
        self.duration_label = QLabel("8 sa")
        self.duration_label.setObjectName("durationValue")
        bl.addWidget(cap)
        bl.addStretch(1)
        bl.addWidget(self.duration_label)
        self.bed.timeChanged.connect(self.update_duration)
        self.wake.timeChanged.connect(self.update_duration)

        self.add_fields(("Uyku tarihi (yatış günü)", self.day))
        self.add_fields(("Yatış saati", self.bed), ("Kalkış saati", self.wake))
        self.body.addWidget(box)
        self.add_fields(("Not", self.note))
        self.add_buttons()

        if record:
            self.day.setDate(date.fromisoformat(record["sleep_date"]))
            self.bed.setTime(datetime.strptime(record["bedtime"], "%H:%M").time())
            self.wake.setTime(datetime.strptime(record["wake_time"], "%H:%M").time())
            self.note.setText(record["note"])
        self.update_duration()

    def update_duration(self, *args):
        mins = duration_between(self.bed.time().toString("HH:mm"), self.wake.time().toString("HH:mm"))
        self.duration_label.setText(fmt_minutes(mins))

    def values(self):
        bed = self.bed.time().toString("HH:mm")
        wake = self.wake.time().toString("HH:mm")
        return (self.day.date().toString("yyyy-MM-dd"), bed, wake,
                duration_between(bed, wake), self.note.text().strip())


# ─────────────────────────────────────────────────────────────────────────────
#  ANA PENCERE
# ─────────────────────────────────────────────────────────────────────────────
class LifeTrackWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.conn = connect_db()
        self.setWindowTitle("LifeTrack — Kişisel Yaşam Analizi")
        self.resize(1280, 840)
        self.setMinimumSize(1120, 720)
        self.current_page = "dashboard"
        self.tracking_active = False
        self.tracking_last_tick = None
        self.tracking_current_app = None
        self.tracking_seconds = defaultdict(int)
        self.empty_icons = []
        self.tracking_timer = QTimer(self)
        self.tracking_timer.setInterval(2000)
        self.tracking_timer.timeout.connect(self.tracking_tick)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        # ── Sol menü ────────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(244)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 24, 16, 18)
        side_layout.setSpacing(4)

        logo_row = QHBoxLayout()
        logo_row.setContentsMargins(6, 0, 0, 0)
        logo_row.setSpacing(12)
        logo_mark = QLabel("L")
        logo_mark.setObjectName("logoMark")
        logo_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_mark.setFixedSize(40, 40)
        logo_text = QVBoxLayout()
        logo_text.setSpacing(0)
        logo_name = QLabel("LifeTrack")
        logo_name.setObjectName("logoName")
        tagline = QLabel("Dijital yaşam dengesi")
        tagline.setObjectName("muted")
        logo_text.addWidget(logo_name)
        logo_text.addWidget(tagline)
        logo_row.addWidget(logo_mark)
        logo_row.addLayout(logo_text)
        logo_row.addStretch()
        side_layout.addLayout(logo_row)
        side_layout.addSpacing(26)

        menu_caption = QLabel("MENÜ")
        menu_caption.setObjectName("menuCaption")
        side_layout.addWidget(menu_caption)

        self.nav_buttons = {}
        self.nav_icon_kinds = {}
        nav_items = [
            ("dashboard", "home", "Genel Bakış"),
            ("usage", "clock", "Zaman Kayıtları"),
            ("sleep", "moon", "Uyku Takibi"),
            ("reports", "chart", "Raporlar && Öneriler"),
        ]
        for key, icon_kind, label in nav_items:
            btn = QPushButton("  " + label)  # "&&" -> görünen tek "&"
            btn.setObjectName("navButton")
            btn.setIconSize(QSize(20, 20))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, k=key: self.show_page(k))
            side_layout.addWidget(btn)
            self.nav_buttons[key] = btn
            self.nav_icon_kinds[key] = icon_kind
        side_layout.addStretch()

        self.side_tracking = QLabel()
        self.side_tracking.setObjectName("sideStatus")
        side_layout.addWidget(self.side_tracking)
        side_layout.addSpacing(8)
        local_note = QLabel("Veriler bu bilgisayarda yerel olarak saklanır.")
        local_note.setObjectName("localNote")
        local_note.setWordWrap(True)
        side_layout.addWidget(local_note)

        # ── Sağ taraf: başlık + sayfalar ────────────────────────────────────
        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(32, 28, 32, 24)
        main_layout.setSpacing(22)

        header = QHBoxLayout()
        header.setSpacing(16)
        titles = QVBoxLayout()
        titles.setSpacing(3)
        self.header_title = QLabel("Genel Bakış")
        self.header_title.setObjectName("pageTitle")
        self.header_subtitle = QLabel("Dijital alışkanlıklarını ve dinlenme düzenini takip et.")
        self.header_subtitle.setObjectName("muted")
        titles.addWidget(self.header_title)
        titles.addWidget(self.header_subtitle)
        header.addLayout(titles, 1)
        today = date.today()
        self.header_date = QLabel(f"{today.day} {TR_MONTHS[today.month - 1]} {today.year}, {TR_DAYS[today.weekday()]}")
        self.header_date.setObjectName("chip")
        header.addWidget(self.header_date, 0, Qt.AlignmentFlag.AlignTop)
        self.theme_btn = make_button("", "secondaryButton", self.toggle_theme)
        self.theme_btn.setIconSize(QSize(18, 18))
        header.addWidget(self.theme_btn, 0, Qt.AlignmentFlag.AlignTop)
        main_layout.addLayout(header)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 1)
        root_layout.addWidget(sidebar)
        root_layout.addWidget(main, 1)

        self.pages = {}
        self.pages["dashboard"] = self.build_dashboard()
        self.pages["usage"] = self.build_usage_page()
        self.pages["sleep"] = self.build_sleep_page()
        self.pages["reports"] = self.build_reports_page()
        for key in ["dashboard", "usage", "sleep", "reports"]:
            self.stack.addWidget(self.pages[key])
        self.set_tracking_indicator(False)
        self.update_theme_button()
        self.show_page("dashboard")
        self.refresh_all()

    # ── Yardımcılar ─────────────────────────────────────────────────────────
    def label(self, text, object_name=None):
        w = QLabel(text)
        if object_name:
            w.setObjectName(object_name)
        return w

    def section_title(self, text):
        return self.label(text, "sectionTitle")

    def panel(self, margins=(22, 18, 22, 20), spacing=12):
        frame = QFrame()
        frame.setObjectName("panel")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(*margins)
        lay.setSpacing(spacing)
        return frame, lay

    def panel_header(self, title, subtitle=None):
        """Başlık (+ isteğe bağlı alt başlık) solda; sağa widget eklemek için HBox döner."""
        row = QHBoxLayout()
        row.setSpacing(8)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(self.section_title(title))
        if subtitle:
            col.addWidget(self.label(subtitle, "muted"))
        row.addLayout(col)
        row.addStretch(1)
        return row

    def scroll_wrap(self, page):
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setWidget(page)
        return area

    def make_empty_state(self, icon_kind, title, text):
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 36, 0, 36)
        lay.setSpacing(6)
        icon = QLabel()
        icon.setPixmap(icon_pixmap(icon_kind, MUTED, 34))
        self.empty_icons.append((icon, icon_kind))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = self.label(title, "emptyTitle")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s = self.label(text, "muted")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s.setWordWrap(True)
        lay.addStretch(1)
        lay.addWidget(icon)
        lay.addWidget(t)
        lay.addWidget(s)
        lay.addStretch(1)
        return box

    def update_theme_button(self):
        if THEME == "dark":
            self.theme_btn.setText("  Açık tema")
            self.theme_btn.setIcon(QIcon(icon_pixmap("sun", TEXT, 18)))
        else:
            self.theme_btn.setText("  Koyu tema")
            self.theme_btn.setIcon(QIcon(icon_pixmap("moon", TEXT, 18)))

    def toggle_theme(self):
        set_palette("light" if THEME == "dark" else "dark")
        QSettings("LifeTrack", "LifeTrack").setValue("theme", THEME)
        apply_theme(QApplication.instance())
        self.update_theme_button()
        for icon_label, kind in self.empty_icons:
            icon_label.setPixmap(icon_pixmap(kind, MUTED, 34))
        self.set_tracking_indicator(self.tracking_active)
        self.show_page(self.current_page)
        self.refresh_all()

    def set_tracking_indicator(self, active):
        dot = ACCENT if active else FAINT
        text = "Takip açık" if active else "Takip kapalı"
        self.side_tracking.setText(f"<span style='color:{dot};'>●</span>&nbsp;&nbsp;{text}")
        if hasattr(self, "tracking_dot"):
            self.tracking_dot.setProperty("active", active)
            repolish(self.tracking_dot)
            self.tracking_title.setText("Otomatik takip çalışıyor" if active else "Otomatik takip")

    def format_report_lines(self, lines):
        """Analiz satırlarını okunaklı paragraflara çevirir."""
        parts = []
        for i, line in enumerate(lines):
            text = html.escape(line)
            if i == 0:
                style, text = f"color:{TEXT}; font-weight:600;", text
            elif line.startswith("İpucu:"):
                style = f"color:{ACCENT};"
            elif line.startswith("Not:"):
                style = f"color:{MUTED}; font-size:9pt;"
            else:
                style = f"color:{SOFT};"
            parts.append(f"<p style='margin:0 0 11px 0; line-height:140%; {style}'>{text}</p>")
        return "".join(parts)

    # ── Sayfalar ────────────────────────────────────────────────────────────
    def build_dashboard(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 8, 8)
        layout.setSpacing(18)

        cards = QHBoxLayout()
        cards.setSpacing(16)
        self.card_screen = StatCard("BUGÜN EKRAN SÜRESİ", "0 dk", "Kullanım kayıtlarından", ACCENT, "monitor")
        self.card_social = StatCard("SOSYAL MEDYA & VİDEO", "0 dk", "Sosyal medya ve içerik kayıtları", ACCENT, "play")
        self.card_sleep = StatCard("SON UYKU KAYDI", "—", "Uyku kaydı ekleyerek başla", ACCENT, "moon")
        self.card_target = StatCard("HAFTALIK EKRAN SÜRESİ", "0 sa", "Son 7 günün toplamı", ACCENT, "calendar")
        for c in (self.card_screen, self.card_social, self.card_sleep, self.card_target):
            cards.addWidget(c, 1)
        layout.addLayout(cards)

        bottom = QHBoxLayout()
        bottom.setSpacing(16)

        chart_panel, cp = self.panel()
        cp.addLayout(self.panel_header("Ekran süresi", "Son 7 gün · günlük toplam"))
        self.dashboard_chart = MiniBarChart()
        self.dashboard_chart.setMinimumHeight(250)
        cp.addWidget(self.dashboard_chart, 1)
        bottom.addWidget(chart_panel, 5)

        right = QVBoxLayout()
        right.setSpacing(16)
        quick_panel, ql = self.panel(spacing=10)
        ql.addWidget(self.section_title("Hızlı işlem"))
        ql.addSpacing(2)
        add_usage = make_button("＋   Kullanım kaydı ekle", "primaryButton", self.add_usage)
        add_sleep = make_button("＋   Uyku kaydı ekle", "secondaryButton", self.add_sleep)
        ql.addWidget(add_usage)
        ql.addWidget(add_sleep)
        right.addWidget(quick_panel)

        insight_panel, il = self.panel(spacing=8)
        il.addWidget(self.section_title("Bugünün notu"))
        self.insight_text = QLabel("Kayıt ekledikçe burada kişisel özetler görünecek.")
        self.insight_text.setObjectName("insightText")
        self.insight_text.setWordWrap(True)
        self.insight_text.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        il.addWidget(self.insight_text)
        il.addStretch(1)
        right.addWidget(insight_panel, 1)
        bottom.addLayout(right, 3)

        layout.addLayout(bottom, 1)
        return self.scroll_wrap(page)

    def build_usage_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Otomatik takip kartı
        track_card, tl = self.panel(margins=(22, 16, 22, 16))
        row = QHBoxLayout()
        row.setSpacing(14)
        self.tracking_dot = QLabel("●")
        self.tracking_dot.setObjectName("statusDot")
        self.tracking_dot.setProperty("active", False)
        row.addWidget(self.tracking_dot, 0, Qt.AlignmentFlag.AlignTop)
        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        self.tracking_title = self.section_title("Otomatik takip")
        text_col.addWidget(self.tracking_title)
        self.tracking_status = QLabel("Otomatik takip kapalı. Takip yalnızca sen başlattığında çalışır.")
        self.tracking_status.setObjectName("muted")
        self.tracking_status.setWordWrap(True)
        text_col.addWidget(self.tracking_status)
        row.addLayout(text_col, 1)
        self.tracking_start_btn = make_button("▶   Takibi başlat", "primaryButton", self.start_tracking)
        self.tracking_stop_btn = make_button("■   Durdur", "secondaryButton", self.stop_tracking)
        self.tracking_stop_btn.setEnabled(False)
        row.addWidget(self.tracking_start_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.tracking_stop_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        tl.addLayout(row)
        layout.addWidget(track_card)

        # Kayıt listesi paneli
        table_panel, pl = self.panel(margins=(22, 18, 22, 16))
        head = self.panel_header("Kullanım kayıtları", "Cihaz ve uygulama kullanım kayıtlarını yönet.")
        self.add_usage_btn = make_button("＋   Yeni kayıt", "primaryButton", self.add_usage)
        self.edit_usage_btn = make_button("Düzenle", "secondaryButton", self.edit_usage)
        self.delete_usage_btn = make_button("Sil", "dangerButton", self.delete_usage)
        head.addWidget(self.add_usage_btn)
        head.addWidget(self.edit_usage_btn)
        head.addWidget(self.delete_usage_btn)
        pl.addLayout(head)

        self.usage_table = QTableWidget(0, 6)
        self.usage_table.setHorizontalHeaderLabels(["Tarih", "Cihaz", "Kategori", "Uygulama / etkinlik", "Süre", "Not"])
        self.configure_table(self.usage_table, {0: 120, 1: 120, 2: 168, 4: 110})
        self.usage_table.setItemDelegateForColumn(2, CategoryPillDelegate(self.usage_table))
        pl.addWidget(self.usage_table, 1)
        self.usage_empty = self.make_empty_state("inbox", "Henüz kullanım kaydı yok",
                                                 "“Yeni kayıt” ile ekleyebilir ya da otomatik takibi başlatabilirsin.")
        pl.addWidget(self.usage_empty, 1)
        self.usage_total = QLabel("Toplam: 0 dk")
        self.usage_total.setObjectName("muted")
        pl.addWidget(self.usage_total)
        layout.addWidget(table_panel, 1)
        return page

    def build_sleep_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        table_panel, pl = self.panel(margins=(22, 18, 22, 16))
        head = self.panel_header("Uyku kayıtları", "Yatış ve kalkış saatlerini gir; süre otomatik hesaplanır.")
        add = make_button("＋   Uyku kaydı", "primaryButton", self.add_sleep)
        edit = make_button("Düzenle", "secondaryButton", self.edit_sleep)
        delete = make_button("Sil", "dangerButton", self.delete_sleep)
        head.addWidget(add)
        head.addWidget(edit)
        head.addWidget(delete)
        pl.addLayout(head)

        self.sleep_table = QTableWidget(0, 5)
        self.sleep_table.setHorizontalHeaderLabels(["Uyku tarihi", "Yatış", "Kalkış", "Süre", "Not"])
        self.configure_table(self.sleep_table, {0: 130, 1: 100, 2: 100, 3: 120})
        pl.addWidget(self.sleep_table, 1)
        self.sleep_empty = self.make_empty_state("moon", "Henüz uyku kaydı yok",
                                                 "İlk kaydını “Uyku kaydı” butonuyla ekleyebilirsin.")
        pl.addWidget(self.sleep_empty, 1)
        self.sleep_summary = QLabel("Uyku kayıtları burada listelenir.")
        self.sleep_summary.setObjectName("muted")
        pl.addWidget(self.sleep_summary)
        layout.addWidget(table_panel, 1)
        return page

    def build_reports_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 8, 8)
        layout.setSpacing(16)

        selector = QHBoxLayout()
        selector.setSpacing(12)
        selector.addWidget(self.label("Rapor dönemi", "muted"))
        self.report_period = SegmentedControl(["Son 7 gün", "Son 30 gün", "Bu yıl"])
        self.report_period.currentIndexChanged.connect(self.refresh_reports)
        selector.addWidget(self.report_period)
        selector.addStretch()
        layout.addLayout(selector)

        cards = QHBoxLayout()
        cards.setSpacing(16)
        self.report_total_card = StatCard("DÖNEM TOPLAMI", "0 dk", "Seçili dönemdeki kayıtlar", ACCENT, "monitor")
        self.report_average_card = StatCard("GÜNLÜK ORTALAMA", "0 dk", "Takvim günlerine göre", ACCENT, "clock")
        self.report_change_card = StatCard("ÖNCEKİ DÖNEME GÖRE", "—", "Aynı uzunluktaki dönemle kıyas", ACCENT, "chart")
        for c in (self.report_total_card, self.report_average_card, self.report_change_card):
            cards.addWidget(c, 1)
        layout.addLayout(cards)

        chart_panel, cp = self.panel()
        cp.addLayout(self.panel_header("Ekran süresi eğilimi", "Seçili dönemin zaman içindeki dağılımı"))
        self.report_chart = MiniBarChart()
        self.report_chart.setMinimumHeight(220)
        cp.addWidget(self.report_chart)
        layout.addWidget(chart_panel)

        breakdown_row = QHBoxLayout()
        breakdown_row.setSpacing(16)
        category_panel, cpl = self.panel()
        cpl.addLayout(self.panel_header("Kategori dağılımı"))
        self.category_chart = HorizontalBarChart(color_map=CATEGORY_COLORS, empty_text="Bu dönem için kategori verisi yok")
        cpl.addWidget(self.category_chart)
        app_panel, apl = self.panel()
        apl.addLayout(self.panel_header("En çok kullanılan uygulamalar"))
        self.app_chart = HorizontalBarChart(empty_text="Bu dönem için uygulama verisi yok")
        apl.addWidget(self.app_chart)
        breakdown_row.addWidget(category_panel, 1)
        breakdown_row.addWidget(app_panel, 1)
        layout.addLayout(breakdown_row)

        self.report_summary, sl = self.panel()
        sl.addLayout(self.panel_header("Analiz ve öneriler"))
        self.report_text = QLabel("Kayıt ekledikçe dönem özeti ve öneriler burada görünecek.")
        self.report_text.setTextFormat(Qt.TextFormat.RichText)
        self.report_text.setWordWrap(True)
        self.report_text.setObjectName("insightText")
        self.report_text.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        sl.addWidget(self.report_text)
        layout.addWidget(self.report_summary)
        layout.addStretch(1)
        return self.scroll_wrap(page)

    def configure_table(self, table, fixed_widths=None):
        fixed_widths = fixed_widths or {}
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setSortingEnabled(False)
        table.setWordWrap(False)
        table.setTextElideMode(Qt.TextElideMode.ElideRight)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(48)
        header = table.horizontalHeader()
        header.setHighlightSections(False)
        header.setMinimumHeight(40)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        for col in range(table.columnCount()):
            if col in fixed_widths:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
                table.setColumnWidth(col, fixed_widths[col])
            else:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

    def show_page(self, key):
        titles = {
            "dashboard": ("Genel Bakış", "Dijital alışkanlıklarını ve dinlenme düzenini takip et."),
            "usage": ("Zaman Kayıtları", "Cihaz, uygulama ve etkinlik sürelerini kaydet."),
            "sleep": ("Uyku Takibi", "Uyku saatlerini kaydet ve zaman içindeki değişimi gör."),
            "reports": ("Raporlar & Öneriler", "Kayıtlarına dayalı dönemsel özetler ve alışkanlık önerileri.")
        }
        self.current_page = key
        self.stack.setCurrentWidget(self.pages[key])
        self.header_title.setText(titles[key][0])
        self.header_subtitle.setText(titles[key][1])
        for k, btn in self.nav_buttons.items():
            active = k == key
            btn.setProperty("active", active)
            btn.setIcon(QIcon(icon_pixmap(self.nav_icon_kinds[k], ACCENT if active else MUTED)))
            repolish(btn)
        if key == "reports":
            self.refresh_reports()

    def add_usage(self):
        dialog = RecordDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                values = validate_screen_values(dialog.values())
                with self.conn:
                    self.conn.execute(
                        "INSERT INTO dbo.screen_records(record_date, device, category, app_name, minutes, note) VALUES(?,?,?,?,?,?)",
                        values
                    )
            except (ValueError, pyodbc.Error) as exc:
                QMessageBox.warning(self, "Kayıt kaydedilemedi", str(exc))
                return
            self.refresh_all()

    def selected_id(self, table):
        row = table.currentRow()
        if row < 0:
            return None
        item = table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def edit_usage(self):
        record_id = self.selected_id(self.usage_table)
        if not record_id:
            QMessageBox.information(self, "Kayıt seç", "Düzenlemek için önce bir kayıt seç.")
            return
        record = self.conn.execute("SELECT * FROM dbo.screen_records WHERE id=?", (record_id,)).fetchone()
        dialog = RecordDialog(self, record)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                values = validate_screen_values(dialog.values())
                with self.conn:
                    self.conn.execute(
                        """UPDATE dbo.screen_records SET record_date=?, device=?, category=?, app_name=?, minutes=?, note=? WHERE id=?""",
                        (*values, record_id)
                    )
            except (ValueError, pyodbc.Error) as exc:
                QMessageBox.warning(self, "Kayıt güncellenemedi", str(exc))
                return
            self.refresh_all()

    def delete_usage(self):
        record_id = self.selected_id(self.usage_table)
        if not record_id:
            QMessageBox.information(self, "Kayıt seç", "Silmek için önce bir kayıt seç.")
            return
        answer = QMessageBox.question(self, "Kaydı sil", "Seçili kullanım kaydı silinsin mi?")
        if answer == QMessageBox.StandardButton.Yes:
            try:
                with self.conn:
                    self.conn.execute("DELETE FROM dbo.screen_records WHERE id=?", (record_id,))
            except pyodbc.Error as exc:
                QMessageBox.warning(self, "Kayıt silinemedi", str(exc))
                return
            self.refresh_all()

    def add_sleep(self):
        dialog = SleepDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                values = validate_sleep_values(dialog.values())
                with self.conn:
                    self.conn.execute(
                        "INSERT INTO dbo.sleep_records(sleep_date, bedtime, wake_time, duration_minutes, note) VALUES(?,?,?,?,?)",
                        values
                    )
            except (ValueError, pyodbc.Error) as exc:
                QMessageBox.warning(self, "Uyku kaydı kaydedilemedi", str(exc))
                return
            self.refresh_all()

    def edit_sleep(self):
        record_id = self.selected_id(self.sleep_table)
        if not record_id:
            QMessageBox.information(self, "Kayıt seç", "Düzenlemek için önce bir uyku kaydı seç.")
            return
        record = self.conn.execute("SELECT * FROM dbo.sleep_records WHERE id=?", (record_id,)).fetchone()
        dialog = SleepDialog(self, record)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                values = validate_sleep_values(dialog.values())
                with self.conn:
                    self.conn.execute(
                        """UPDATE dbo.sleep_records SET sleep_date=?, bedtime=?, wake_time=?, duration_minutes=?, note=? WHERE id=?""",
                        (*values, record_id)
                    )
            except (ValueError, pyodbc.Error) as exc:
                QMessageBox.warning(self, "Uyku kaydı güncellenemedi", str(exc))
                return
            self.refresh_all()

    def delete_sleep(self):
        record_id = self.selected_id(self.sleep_table)
        if not record_id:
            QMessageBox.information(self, "Kayıt seç", "Silmek için önce bir uyku kaydı seç.")
            return
        answer = QMessageBox.question(self, "Kaydı sil", "Seçili uyku kaydı silinsin mi?")
        if answer == QMessageBox.StandardButton.Yes:
            try:
                with self.conn:
                    self.conn.execute("DELETE FROM dbo.sleep_records WHERE id=?", (record_id,))
            except pyodbc.Error as exc:
                QMessageBox.warning(self, "Uyku kaydı silinemedi", str(exc))
                return
            self.refresh_all()

    def start_tracking(self):
        import os
        if os.name != "nt":
            QMessageBox.information(self, "Windows gerekli", "Otomatik takip bu sürümde Windows 10/11 için tasarlandı.")
            return
        self.tracking_active = True
        self.tracking_last_tick = time.monotonic()
        self.tracking_current_app = None
        # Sample immediately so the first interval is attributed to the active app.
        self.tracking_tick()
        self.tracking_timer.start()
        self.tracking_start_btn.setEnabled(False)
        self.tracking_stop_btn.setEnabled(True)
        self.set_tracking_indicator(True)
        self.tracking_status.setText("Otomatik takip açık. Yalnızca etkin uygulamanın adı ve süresi kaydedilir; pencere başlığı, yazılan metin ve web adresleri okunmaz. 60 saniyeden uzun hareketsizlikte süre sayılmaz.")

    def stop_tracking(self):
        if not self.tracking_active:
            return
        self.tracking_tick()
        self.tracking_timer.stop()
        self.tracking_active = False
        self.tracking_current_app = None
        self.tracking_last_tick = None
        self._flush_tracking_seconds()
        self.tracking_start_btn.setEnabled(True)
        self.tracking_stop_btn.setEnabled(False)
        self.set_tracking_indicator(False)
        self.tracking_status.setText("Otomatik takip durduruldu. Kaydedilen tam dakikalar Zaman Kayıtları listesine eklendi.")
        self.refresh_all()

    def tracking_tick(self):
        if not self.tracking_active:
            return
        now = time.monotonic()
        executable = get_foreground_executable()
        app_key = classify_process(executable) if executable else None
        if self.tracking_last_tick is not None and self.tracking_current_app is not None:
            # Avoid over-counting if the UI was paused or the computer slept.
            elapsed = max(0, min(6, int(now - self.tracking_last_tick)))
            self.tracking_seconds[self.tracking_current_app] += elapsed
        self.tracking_current_app = app_key
        self.tracking_last_tick = now
        self._flush_tracking_seconds()

    def _flush_tracking_seconds(self):
        today = date.today().isoformat()
        wrote = False
        for (app_name, category), seconds in list(self.tracking_seconds.items()):
            minutes = seconds // 60
            if minutes < 1:
                continue
            try:
                with self.conn:
                    self.conn.execute(
                        "INSERT INTO dbo.screen_records(record_date, device, category, app_name, minutes, note) VALUES(?,?,?,?,?,?)",
                        validate_screen_values((today, "Bilgisayar", category, app_name, int(minutes), "Otomatik takip"))
                    )
                self.tracking_seconds[(app_name, category)] -= minutes * 60
                wrote = True
            except (pyodbc.Error, ValueError) as exc:
                self.tracking_status.setText(f"Otomatik kayıt hatası: {exc}")
        if wrote and hasattr(self, "usage_table"):
            self.refresh_all()

    def refresh_all(self):
        self.refresh_usage_table()
        self.refresh_sleep_table()
        self.refresh_dashboard()
        self.refresh_reports()

    def refresh_usage_table(self):
        rows = self.conn.execute("SELECT * FROM dbo.screen_records ORDER BY record_date DESC, id DESC").fetchall()
        self.usage_table.setRowCount(0)
        total = 0
        for r in rows:
            row = self.usage_table.rowCount()
            self.usage_table.insertRow(row)
            vals = [r["record_date"], r["device"], r["category"], r["app_name"] or "—", fmt_minutes(r["minutes"]), r["note"] or "—"]
            for col, value in enumerate(vals):
                item = QTableWidgetItem(str(value))
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, r["id"])
                elif col in (4,):
                    item.setForeground(QColor(TEXT))
                    item.setFont(chart_font(10, QFont.Weight.DemiBold))
                elif col in (1, 5):
                    item.setForeground(QColor(MUTED))
                self.usage_table.setItem(row, col, item)
            total += r["minutes"]
        self.usage_table.setVisible(bool(rows))
        self.usage_empty.setVisible(not rows)
        self.usage_total.setText(f"Toplam kayıtlı kullanım: {fmt_minutes(total)}  ·  {len(rows)} kayıt")

    def refresh_sleep_table(self):
        rows = self.conn.execute("SELECT * FROM dbo.sleep_records ORDER BY sleep_date DESC, id DESC").fetchall()
        self.sleep_table.setRowCount(0)
        for r in rows:
            row = self.sleep_table.rowCount()
            self.sleep_table.insertRow(row)
            vals = [r["sleep_date"], r["bedtime"], r["wake_time"], fmt_minutes(r["duration_minutes"]), r["note"] or "—"]
            for col, value in enumerate(vals):
                item = QTableWidgetItem(str(value))
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, r["id"])
                elif col == 3:
                    item.setForeground(QColor(ACCENT))
                    item.setFont(chart_font(10, QFont.Weight.DemiBold))
                elif col == 4:
                    item.setForeground(QColor(MUTED))
                self.sleep_table.setItem(row, col, item)
        self.sleep_table.setVisible(bool(rows))
        self.sleep_empty.setVisible(not rows)
        if rows:
            avg = sum(r["duration_minutes"] for r in rows[:7]) / min(7, len(rows))
            self.sleep_summary.setText(f"{len(rows)} kayıt  ·  Son {min(7, len(rows))} kaydın ortalaması: {fmt_minutes(round(avg))}")
        else:
            self.sleep_summary.setText("Henüz uyku kaydı yok. İlk kaydını ekleyebilirsin.")

    def refresh_dashboard(self):
        today = date.today()
        today_str = today.isoformat()
        today_total = self.conn.execute(
            "SELECT COALESCE(SUM(minutes),0) FROM dbo.screen_records WHERE record_date=?", (today_str,)
        ).fetchone()[0]
        social_total = self.conn.execute(
            """SELECT COALESCE(SUM(minutes),0) FROM dbo.screen_records
               WHERE record_date=? AND category IN (N'Sosyal medya', N'Video / içerik')""", (today_str,)
        ).fetchone()[0]
        week_start = (today - timedelta(days=6)).isoformat()
        week_total = self.conn.execute(
            "SELECT COALESCE(SUM(minutes),0) FROM dbo.screen_records WHERE record_date BETWEEN ? AND ?",
            (week_start, today_str)
        ).fetchone()[0]
        last_sleep = self.conn.execute("SELECT TOP (1) * FROM dbo.sleep_records ORDER BY sleep_date DESC, id DESC").fetchone()
        self.card_screen.set_value(fmt_minutes(today_total), "Bugün kaydedilen tüm kategoriler")
        self.card_social.set_value(fmt_minutes(social_total), "Sosyal medya + video / içerik")
        self.card_target.set_value(fmt_minutes(week_total), "Son 7 günün kayıtlı toplamı")
        if last_sleep:
            self.card_sleep.set_value(fmt_minutes(last_sleep["duration_minutes"]), f"{last_sleep['sleep_date']} • {last_sleep['bedtime']}–{last_sleep['wake_time']}")
        else:
            self.card_sleep.set_value("—", "Henüz uyku kaydı eklenmedi")
        chart_items = []
        for offset in range(6, -1, -1):
            d = today - timedelta(days=offset)
            total = self.conn.execute(
                "SELECT COALESCE(SUM(minutes),0) FROM dbo.screen_records WHERE record_date=?", (d.isoformat(),)
            ).fetchone()[0]
            chart_items.append((d.strftime("%d %b"), total))
        self.dashboard_chart.set_items(chart_items)
        if today_total == 0 and not last_sleep:
            self.insight_text.setText("Başlamak için bir ekran süresi veya uyku kaydı ekle. Verilerin geldikçe günlük özetler burada güncellenecek.")
        else:
            pieces = []
            if today_total:
                pieces.append(f"Bugün {fmt_minutes(today_total)} kullanım kaydı girdin.")
            if last_sleep:
                if last_sleep["duration_minutes"] < 7 * 60:
                    pieces.append("Son uyku kaydın 7 saatin altında. Tek bir kayıt yerine birkaç haftalık eğilimi takip etmek daha anlamlıdır.")
                elif last_sleep["duration_minutes"] <= 9 * 60:
                    pieces.append("Son uyku kaydın yetişkinler için yaygın önerilen süre aralığında. Düzenlilik de önemlidir.")
                else:
                    pieces.append("Son uyku süren uzun görünüyor; bunun tek seferlik mi yoksa sürekli bir eğilim mi olduğunu takip edebilirsin.")
            self.insight_text.setText(" ".join(pieces))

    def refresh_reports(self, *args):
        if not hasattr(self, "report_period"):
            return
        choice = self.report_period.currentIndex()
        today = date.today()
        start, end, period_label = get_period_range(choice, today)
        previous_start, previous_end = previous_period_range(start, end)

        buckets = build_buckets(choice, start, end)
        self.report_chart.set_items(get_bucket_totals(self.conn, buckets))
        category_totals = get_category_totals(self.conn, start, end)
        self.category_chart.set_items(category_totals)
        app_totals = get_app_totals(self.conn, start, end, limit=5)
        self.app_chart.set_items(app_totals)

        total = sum_usage(self.conn, start, end)
        previous_total = sum_usage(self.conn, previous_start, previous_end)
        days_in_period = (end - start).days + 1
        avg_day = total / max(1, days_in_period)
        change = percent_change(total, previous_total)
        self.report_total_card.set_value(fmt_minutes(total), f"{period_label} • {days_in_period} gün")
        self.report_average_card.set_value(fmt_minutes(round(avg_day)), "Takvim günü başına kayıtlı kullanım")
        if previous_total == 0:
            change_text = "Önceki dönemde kayıt yok" if total == 0 else "Yeni kayıtlar var"
            self.report_change_card.set_value(change_text, f"Önceki dönem: {fmt_minutes(previous_total)}")
        else:
            delta = total - previous_total
            delta_label = ("+" if delta > 0 else "−" if delta < 0 else "") + fmt_minutes(abs(delta))
            pct_text = "0%" if change == 0 else f"{change:+.1f}%"
            self.report_change_card.set_value(pct_text, f"Önceki döneme göre {delta_label} • önceki {fmt_minutes(previous_total)}")

        count = self.conn.execute(
            "SELECT COUNT(*) FROM dbo.screen_records WHERE record_date BETWEEN ? AND ?",
            (start.isoformat(), end.isoformat()),
        ).fetchone()[0]
        sleep = self.conn.execute(
            "SELECT AVG(duration_minutes), COUNT(*) FROM dbo.sleep_records WHERE sleep_date BETWEEN ? AND ?",
            (start.isoformat(), end.isoformat()),
        ).fetchone()
        lines = [f"{period_label}: {fmt_minutes(total)} kayıtlı ekran süresi, {count} kullanım kaydı ve günlük ortalama {fmt_minutes(round(avg_day))}."]
        if previous_total:
            if change is not None and change > 0:
                lines.append(f"Önceki eşit uzunluktaki döneme göre kullanım {change:.1f}% arttı.")
            elif change is not None and change < 0:
                lines.append(f"Önceki eşit uzunluktaki döneme göre kullanım {abs(change):.1f}% azaldı.")
            else:
                lines.append("Toplam ekran süresi önceki eşit uzunluktaki dönemle aynı.")
        elif total:
            lines.append("Önceki dönemde kayıt bulunmadığı için yüzde değişim hesaplanmadı.")
        if category_totals:
            category, minutes = category_totals[0]
            share = minutes / total * 100 if total else 0
            lines.append(f"En yüksek kategori: {category} — {fmt_minutes(minutes)} (toplamın %{share:.1f} kadarı).")
            lines.append("Kategori toplamları yalnızca kaydedilen verileri kapsar; kayıt girilmeyen kullanım süreleri hesaba katılmaz.")
        else:
            lines.append("Kategori dağılımını görmek için bu döneme ekran kullanım kayıtları ekle.")
        if app_totals:
            app_name, app_minutes = app_totals[0]
            lines.append(f"En çok kullanılan uygulama/kayıt: {app_name} — {fmt_minutes(app_minutes)}.")
            if len(app_totals) > 1 and app_totals[0][1] > app_totals[1][1] * 1.5:
                lines.append("İlk sıradaki uygulama diğerlerinden belirgin biçimde önde; istersen bu kullanım için küçük bir hedef belirleyebilirsin.")
        if sleep[1]:
            lines.append(f"Bu dönemde {sleep[1]} uyku kaydı var; kayıt başına ortalama süre {fmt_minutes(round(sleep[0]))}.")
        else:
            lines.append("Uyku karşılaştırması için bu döneme ait uyku kayıtları ekleyebilirsin.")
        if avg_day > 5 * 60:
            lines.append("İpucu: Ekran süresini değiştirmek istiyorsan önce en yüksek kategoriye bakıp küçük ve ölçülebilir bir hedef belirleyebilirsin.")
        elif total > 0:
            lines.append("İpucu: Kayıtları düzenli tut; haftalar arası karşılaştırmalar tek bir güne bakmaktan daha anlamlıdır.")
        else:
            lines.append("İlk kullanım kaydını ekleyerek kişisel raporunu oluşturmaya başlayabilirsin.")
        lines.append("Not: Analizler yalnızca girilen verilere dayanır; tıbbi teşhis değildir.")
        self.report_text.setText(self.format_report_lines(lines))

    def closeEvent(self, event):
        if self.tracking_active:
            self.stop_tracking()
        self.tracking_timer.stop()
        self.conn.close()
        event.accept()


def build_stylesheet(arrow_url):
    return f"""
/* ── Temel ─────────────────────────────────────────────────────────── */
QMainWindow, QDialog {{ background: {BG}; }}
QWidget {{ color: {TEXT}; font-size: 10pt; }}
QLabel {{ background: transparent; }}
QToolTip {{ background: {PANEL_ALT}; color: {TEXT}; border: 1px solid {BORDER}; padding: 6px 10px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

/* ── Yazı hiyerarşisi ──────────────────────────────────────────────── */
QLabel#pageTitle {{ font-size: 22pt; font-weight: 700; }}
QLabel#sectionTitle {{ font-size: 12pt; font-weight: 700; }}
QLabel#dialogTitle {{ font-size: 16pt; font-weight: 700; }}
QLabel#statValue {{ font-size: 19pt; font-weight: 700; }}
QLabel#cardCaption {{ color: {MUTED}; font-size: 8pt; font-weight: 700; }}
QLabel#fieldLabel {{ color: {MUTED}; font-size: 9pt; font-weight: 600; }}
QLabel#menuCaption {{ color: {FAINT}; font-size: 8pt; font-weight: 700; padding: 0 0 6px 8px; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#emptyTitle {{ font-size: 12pt; font-weight: 700; }}
QLabel#insightText {{ font-size: 10.5pt; color: {SOFT}; }}
QLabel#chip {{ background: {PANEL}; border: 1px solid {BORDER_SOFT}; border-radius: 10px; padding: 8px 14px; color: {MUTED}; font-weight: 600; }}
QLabel#statusDot {{ color: {FAINT}; font-size: 13pt; }}
QLabel#statusDot[active="true"] {{ color: {ACCENT}; }}
QLabel#durationValue {{ color: {ACCENT}; font-size: 15pt; font-weight: 700; }}

/* ── Sol menü ──────────────────────────────────────────────────────── */
QFrame#sidebar {{ background: {SIDEBAR}; border-right: 1px solid {BORDER_SOFT}; }}
QLabel#logoMark {{ background: {ACCENT}; color: {ON_ACCENT}; font-size: 19pt; font-weight: 800; border-radius: 11px; }}
QLabel#logoName {{ font-size: 15pt; font-weight: 700; }}
QLabel#sideStatus {{ background: {PANEL}; border: 1px solid {BORDER_SOFT}; border-radius: 10px; padding: 10px 12px; color: {SOFT}; font-weight: 600; }}
QLabel#localNote {{ color: {FAINT}; font-size: 8.5pt; padding: 0 4px; }}
QPushButton#navButton {{ background: transparent; border: none; color: {MUTED}; text-align: left; padding: 11px 12px; border-radius: 10px; font-weight: 600; }}
QPushButton#navButton:hover {{ background: {NAV_HOVER}; color: {TEXT}; }}
QPushButton#navButton[active="true"] {{ background: {ACCENT_SOFT}; color: {ACCENT}; }}

/* ── Paneller ──────────────────────────────────────────────────────── */
QFrame#panel, QFrame#statCard {{ background: {PANEL}; border: 1px solid {BORDER_SOFT}; border-radius: 14px; }}
QFrame#durationBox {{ background: {INPUT}; border: 1px solid {BORDER_SOFT}; border-radius: 10px; }}
QFrame#segmented {{ background: {PANEL}; border: 1px solid {BORDER_SOFT}; border-radius: 11px; }}

/* ── Butonlar ──────────────────────────────────────────────────────── */
QPushButton {{ background: {PANEL_ALT}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 9px; padding: 9px 18px; font-weight: 600; min-height: 20px; }}
QPushButton:hover {{ background: {BTN_HOVER}; border-color: {BTN_BORDER_HOVER}; }}
QPushButton:pressed {{ background: {BTN_PRESS}; }}
QPushButton:disabled {{ background: {DIS_BG}; color: {DIS_FG}; border-color: {DIS_BORDER}; }}
QPushButton#primaryButton {{ background: {ACCENT}; color: {ON_ACCENT}; border: none; font-weight: 700; }}
QPushButton#primaryButton:hover {{ background: {ACCENT_HI}; }}
QPushButton#primaryButton:pressed {{ background: {ACCENT_PRESS}; }}
QPushButton#primaryButton:disabled {{ background: {DIS_BG}; color: {DIS_FG}; }}
QPushButton#dangerButton {{ background: {DANGER_BG}; color: {DANGER}; border: 1px solid {DANGER_BORDER}; }}
QPushButton#dangerButton:hover {{ background: {DANGER_HOVER}; border-color: {DANGER}; }}
QPushButton#segButton {{ background: transparent; border: none; color: {MUTED}; padding: 7px 20px; border-radius: 8px; }}
QPushButton#segButton:hover {{ color: {TEXT}; }}
QPushButton#segButton:checked {{ background: {ACCENT_SOFT}; color: {ACCENT}; }}

/* ── Form alanları ─────────────────────────────────────────────────── */
QLineEdit, QSpinBox, QComboBox, QDateEdit, QTimeEdit, QTextEdit {{ background: {INPUT}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 9px; padding: 8px 12px; min-height: 22px; selection-background-color: {ACCENT}; selection-color: {ON_ACCENT}; }}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus, QTextEdit:focus {{ border: 1px solid {ACCENT}; }}
QSpinBox::up-button, QSpinBox::down-button, QTimeEdit::up-button, QTimeEdit::down-button {{ width: 0px; border: none; }}
QAbstractSpinBox QLineEdit, QComboBox QLineEdit {{ background: transparent; border: none; padding: 0; min-height: 0; }}
QComboBox::drop-down, QDateEdit::drop-down {{ border: none; width: 30px; }}
QComboBox::down-arrow, QDateEdit::down-arrow {{ image: url({arrow_url}); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 8px; padding: 4px; outline: none; selection-background-color: {SEL}; selection-color: {TEXT}; }}
QCalendarWidget QWidget {{ background: {PANEL}; color: {TEXT}; }}
QCalendarWidget QToolButton {{ background: transparent; color: {TEXT}; border: none; padding: 6px 10px; font-weight: 600; }}
QCalendarWidget QToolButton:hover {{ background: {PANEL_ALT}; border-radius: 8px; }}
QCalendarWidget QAbstractItemView {{ selection-background-color: {ACCENT}; selection-color: {ON_ACCENT}; outline: none; }}

/* ── Tablolar ──────────────────────────────────────────────────────── */
QTableWidget {{ background: transparent; alternate-background-color: {ROW_ALT}; border: none; outline: none; selection-background-color: {SEL}; selection-color: {TEXT}; }}
QTableWidget::item {{ padding: 0 12px; border: none; }}
QTableWidget::item:hover {{ background: {ROW_HOVER}; }}
QTableWidget::item:selected {{ background: {SEL}; color: {TEXT}; }}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{ background: transparent; color: {MUTED}; border: none; border-bottom: 1px solid {BORDER_SOFT}; padding: 0 12px; font-size: 9pt; font-weight: 700; }}

/* ── Kaydırma çubukları ────────────────────────────────────────────── */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {SCROLL}; border-radius: 4px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {SCROLL_HOVER}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {SCROLL}; border-radius: 4px; min-width: 28px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ── Mesaj kutuları ────────────────────────────────────────────────── */
QMessageBox {{ background: {BG}; }}
QMessageBox QLabel {{ color: {TEXT}; font-size: 10pt; }}
QMessageBox QPushButton {{ min-width: 84px; }}
"""


def apply_theme(app):
    """Yazı tipi, koyu palet ve stil dosyasını uygular."""
    app.setStyle("Fusion")

    font = QFont()
    font.setFamilies(["Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica Neue", "Arial"])
    font.setPointSize(10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    pal = QPalette()
    roles = {
        QPalette.ColorRole.Window: BG, QPalette.ColorRole.WindowText: TEXT,
        QPalette.ColorRole.Base: INPUT, QPalette.ColorRole.AlternateBase: PANEL_ALT,
        QPalette.ColorRole.Text: TEXT, QPalette.ColorRole.Button: PANEL_ALT,
        QPalette.ColorRole.ButtonText: TEXT, QPalette.ColorRole.Highlight: SEL,
        QPalette.ColorRole.HighlightedText: TEXT, QPalette.ColorRole.ToolTipBase: PANEL_ALT,
        QPalette.ColorRole.ToolTipText: TEXT, QPalette.ColorRole.PlaceholderText: FAINT,
    }
    for role, color in roles.items():
        pal.setColor(role, QColor(color))
    app.setPalette(pal)

    # Açılır liste oku için küçük bir ikon üret (QSS yalnızca dosya yolu kabul eder).
    asset_dir = Path(tempfile.gettempdir()) / "lifetrack_ui"
    asset_dir.mkdir(exist_ok=True)
    arrow = QPixmap(24, 24)
    arrow.fill(Qt.GlobalColor.transparent)
    p = QPainter(arrow)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(MUTED), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.drawPolyline(QPolygonF([QPointF(5, 9), QPointF(12, 16), QPointF(19, 9)]))
    p.end()
    arrow_path = asset_dir / f"arrow_down_{THEME}.png"
    arrow.save(str(arrow_path))
    app.setStyleSheet(build_stylesheet(arrow_path.as_posix()))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    set_palette(str(QSettings("LifeTrack", "LifeTrack").value("theme", "dark")))
    apply_theme(app)
    window = LifeTrackWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()