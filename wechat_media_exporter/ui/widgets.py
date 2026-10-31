from __future__ import annotations

import hashlib
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QImageReader,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QPushButton,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
    QWidgetItem,
)

from wechat_media_exporter.models import MediaItem


class FlowLayout(QLayout):
    """A wrapping layout used by the compact media grid."""

    def __init__(self, parent: QWidget | None = None, margin: int = 0, spacing: int = 8):
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int) -> QLayoutItem | None:
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientations()

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def _do_layout(self, rect: QRect, *, test_only: bool) -> int:
        margins = self.contentsMargins()
        effective = rect.adjusted(
            margins.left(), margins.top(), -margins.right(), -margins.bottom()
        )
        x = effective.x()
        y = effective.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._items:
            widget = item.widget()
            if widget is not None and not widget.isVisible():
                continue
            item_spacing = spacing
            if widget is not None:
                item_spacing = widget.style().layoutSpacing(
                    QSizePolicy.ControlType.PushButton,
                    QSizePolicy.ControlType.PushButton,
                    Qt.Orientation.Horizontal,
                )
            next_x = x + item.sizeHint().width() + item_spacing
            if next_x - item_spacing > effective.right() and line_height > 0:
                x = effective.x()
                y += line_height + spacing
                next_x = x + item.sizeHint().width() + item_spacing
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y() + margins.bottom()


def _read_local_thumbnail(path: Path, size: QSize) -> QPixmap | None:
    if not path.is_file():
        return None
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    image_size = reader.size()
    if not image_size.isValid():
        return None
    scaled = image_size.scaled(size * 2, Qt.AspectRatioMode.KeepAspectRatioByExpanding)
    reader.setScaledSize(scaled)
    image = reader.read()
    if image.isNull():
        return None
    pixmap = QPixmap.fromImage(image)
    return pixmap.scaled(
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )


def _round_rect(painter: QPainter, rect: QRect, radius: float, color: QColor) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawRoundedRect(rect, radius, radius)


def build_thumbnail(
    item: MediaItem,
    size: QSize,
    selected: bool,
    image_path: Path | None = None,
) -> QPixmap:
    device_ratio = 2
    pixmap = QPixmap(size * device_ratio)
    pixmap.setDevicePixelRatio(device_ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    canvas = QRect(0, 0, size.width(), size.height())

    preview_path = image_path or item.local_path
    local_thumbnail = _read_local_thumbnail(preview_path, size) if preview_path else None
    if local_thumbnail:
        painter.drawPixmap(canvas, local_thumbnail)
    else:
        seed = int(hashlib.sha1(item.name.encode("utf-8")).hexdigest()[:8], 16)
        palettes = (
            ("#76A9B5", "#D7E5D5", "#315A49"),
            ("#D9A273", "#775044", "#F2D8BB"),
            ("#8BA59B", "#D8D8C7", "#536E60"),
            ("#56728D", "#C4B3A7", "#263D4B"),
            ("#B7A0A6", "#D9D8B9", "#6C8271"),
        )
        first, second, third = palettes[seed % len(palettes)]
        if item.kind == "video":
            first, second, third = (
                ("#18363D", "#2C6671", "#C4895B") if seed % 2 else ("#35445D", "#83677B", "#D5966D")
            )
        elif item.kind == "document":
            first, second, third = "#E6E8E2", "#CBD3CE", "#72867B"
        elif item.kind == "archive":
            first, second, third = "#806B36", "#C8AA61", "#5F512D"
        elif item.kind == "audio":
            first, second, third = "#5B4A73", "#9878A8", "#423B58"
        elif item.kind == "file":
            first, second, third = "#66716C", "#9BA6A0", "#414C47"
        gradient = QLinearGradient(canvas.topLeft(), canvas.bottomRight())
        gradient.setColorAt(0, QColor(first))
        gradient.setColorAt(0.62, QColor(second))
        gradient.setColorAt(1, QColor(third))
        painter.fillRect(canvas, gradient)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 55))
        painter.drawEllipse(
            QRect(
                int(size.width() * (0.48 + (seed % 17) / 100)),
                -int(size.height() * 0.18),
                int(size.width() * 0.54),
                int(size.height() * 0.72),
            )
        )
        painter.setBrush(QColor(255, 255, 255, 32))
        painter.drawEllipse(
            QRect(
                -int(size.width() * 0.1),
                int(size.height() * 0.56),
                int(size.width() * 0.48),
                int(size.height() * 0.55),
            )
        )

    overlay = QLinearGradient(canvas.bottomLeft(), canvas.topLeft())
    overlay.setColorAt(0, QColor(0, 0, 0, 66))
    overlay.setColorAt(0.58, QColor(0, 0, 0, 0))
    painter.fillRect(canvas, overlay)

    font = QFont("Microsoft YaHei UI", 8)
    painter.setFont(font)
    kind_rect = QRect(6, 6, 37, 19)
    _round_rect(painter, kind_rect, 5, QColor(16, 25, 19, 155))
    painter.setPen(QColor("#FFFFFF"))
    painter.drawText(kind_rect, Qt.AlignmentFlag.AlignCenter, item.kind_label)

    check_rect = QRect(size.width() - 26, 6, 20, 20)
    _round_rect(
        painter,
        check_rect,
        5,
        QColor("#07894B") if selected else QColor(255, 255, 255, 218),
    )
    if selected:
        painter.setPen(QPen(QColor("#FFFFFF"), 1.8))
        painter.drawLine(
            check_rect.left() + 5,
            check_rect.center().y(),
            check_rect.left() + 9,
            check_rect.bottom() - 5,
        )
        painter.drawLine(
            check_rect.left() + 9,
            check_rect.bottom() - 5,
            check_rect.right() - 4,
            check_rect.top() + 5,
        )

    if item.kind in {"video", "audio"}:
        center = canvas.center()
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1))
        painter.setBrush(QColor(10, 16, 13, 115))
        painter.drawEllipse(center, 15, 15)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        triangle = QPainterPath()
        triangle.moveTo(center.x() - 3, center.y() - 6)
        triangle.lineTo(center.x() + 7, center.y())
        triangle.lineTo(center.x() - 3, center.y() + 6)
        triangle.closeSubpath()
        painter.drawPath(triangle)
        if item.duration_seconds:
            duration = f"{item.duration_seconds // 60:02d}:{item.duration_seconds % 60:02d}"
            duration_rect = QRect(size.width() - 43, size.height() - 24, 37, 17)
            _round_rect(painter, duration_rect, 4, QColor(10, 16, 13, 165))
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(duration_rect, Qt.AlignmentFlag.AlignCenter, duration)

    painter.end()
    return pixmap


class MediaCard(QFrame):
    selection_changed = Signal(object, bool)
    open_requested = Signal(object)

    def __init__(self, item: MediaItem, parent: QWidget | None = None):
        super().__init__(parent)
        self.item = item
        self._selected = item.selected
        self._preview_path: Path | None = None
        self.setObjectName("MediaCard")
        self.setFixedSize(128, 123)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(
            f"{item.remote_path}\n来源：{item.source_root}\n单击查看或播放，右上角勾选导出"
        )
        self.setAccessibleName(f"{item.kind_label} {item.name}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 5)
        layout.setSpacing(2)

        self.thumbnail = QLabel(self)
        self.thumbnail.setFixedSize(122, 75)
        self.thumbnail.setScaledContents(False)
        layout.addWidget(self.thumbnail, 0, Qt.AlignmentFlag.AlignHCenter)

        body = QWidget(self)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(5, 0, 5, 0)
        body_layout.setSpacing(2)

        self.name_label = QLabel(item.name, body)
        self.name_label.setObjectName("MediaName")
        self.name_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.name_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        body_layout.addWidget(self.name_label)

        meta = QHBoxLayout()
        meta.setContentsMargins(0, 0, 0, 0)
        meta.setSpacing(5)
        self.meta_label = QLabel(f"{item.size_label} · {item.day_label}", body)
        self.meta_label.setObjectName("MediaMeta")
        self.meta_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        meta.addWidget(self.meta_label, 1)
        if item.duplicate_of:
            duplicate = QLabel("重复", body)
            duplicate.setObjectName("DuplicateMeta")
            meta.addWidget(duplicate, 0, Qt.AlignmentFlag.AlignRight)
        body_layout.addLayout(meta)
        layout.addWidget(body)
        self._refresh()

    @property
    def selected(self) -> bool:
        return self._selected

    def set_selected(self, selected: bool, *, notify: bool = True) -> None:
        selected = bool(selected)
        if selected == self._selected:
            return
        self._selected = selected
        self.item.selected = selected
        self._refresh()
        if notify:
            self.selection_changed.emit(self.item, selected)

    def toggle(self) -> None:
        self.set_selected(not self._selected)

    def set_preview(self, path: Path) -> None:
        self._preview_path = path
        self._refresh()

    def _refresh(self) -> None:
        self.setProperty("selected", self._selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.thumbnail.setPixmap(
            build_thumbnail(
                self.item,
                QSize(122, 75),
                self._selected,
                image_path=self._preview_path,
            )
        )

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.LeftButton:
            position = event.position().toPoint()
            if QRect(self.width() - 31, 0, 31, 31).contains(position):
                self.toggle()
            else:
                self.open_requested.emit(self.item)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.key() == Qt.Key.Key_Space:
            self.toggle()
            event.accept()
            return
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            self.open_requested.emit(self.item)
            event.accept()
            return
        super().keyPressEvent(event)


class MonthSection(QWidget):
    selection_changed = Signal(object, bool)
    open_requested = Signal(object)
    select_month_requested = Signal(object)

    def __init__(
        self,
        month_key: str,
        title: str,
        items: list[MediaItem],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.month_key = month_key
        self.items = items
        self.cards: list[MediaCard] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(7)
        title_label = QLabel(title, self)
        title_label.setObjectName("SectionTitle")
        header.addWidget(title_label)
        meta_label = QLabel(
            f"{len(items)} 项 · {format_size(sum(item.size_bytes for item in items))}", self
        )
        meta_label.setObjectName("SectionMeta")
        header.addWidget(meta_label)
        header.addStretch(1)
        select_button = QPushButton("勾选本月", self)
        select_button.setFlat(True)
        select_button.setCursor(Qt.CursorShape.PointingHandCursor)
        select_button.clicked.connect(lambda: self.select_month_requested.emit(self))
        header.addWidget(select_button)
        layout.addLayout(header)

        grid_holder = QWidget(self)
        self.flow = FlowLayout(grid_holder, spacing=7)
        for item in items:
            card = MediaCard(item, grid_holder)
            card.selection_changed.connect(self.selection_changed)
            card.open_requested.connect(self.open_requested)
            self.flow.addWidget(card)
            self.cards.append(card)
        layout.addWidget(grid_holder)

    def set_all_selected(self, selected: bool) -> None:
        for card in self.cards:
            card.set_selected(selected)


class StatCard(QFrame):
    def __init__(self, title: str, icon: QStyle.StandardPixmap, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setMinimumHeight(58)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(11, 8, 11, 8)
        layout.setSpacing(2)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel(self)
        icon_label.setPixmap(self.style().standardIcon(icon).pixmap(14, 14))
        title_row.addWidget(icon_label)
        title_label = QLabel(title, self)
        title_label.setObjectName("Muted")
        title_row.addWidget(title_label)
        title_row.addStretch(1)
        layout.addLayout(title_row)

        self.value_label = QLabel("0", self)
        self.value_label.setStyleSheet("font-size: 19px; font-weight: 600; color: #1B231D;")
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


def format_size(size_bytes: int) -> str:
    value = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size_bytes} B"


class EmptyState(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 32, 24, 32)
        title = QLabel("没有符合当前筛选条件的媒体", self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 15px; font-weight: 600;")
        subtitle = QLabel("连接手机并重新扫描，或调整媒体分类和搜索条件。", self)
        subtitle.setObjectName("Muted")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)


def clear_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            continue
        widget = item.widget()
        child_layout = item.layout()
        if widget is not None:
            widget.deleteLater()
        elif child_layout is not None:
            clear_layout(child_layout)


def widget_item(widget: QWidget) -> QWidgetItem:
    return QWidgetItem(widget)
