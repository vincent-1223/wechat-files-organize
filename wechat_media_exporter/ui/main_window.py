from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QSize, QStandardPaths, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from wechat_media_exporter.demo import demo_report
from wechat_media_exporter.models import (
    ExportProgress,
    ExportResult,
    MediaItem,
    ScanReport,
)
from wechat_media_exporter.reports import write_scan_reports
from wechat_media_exporter.ui.widgets import (
    EmptyState,
    MonthSection,
    StatCard,
    clear_layout,
    format_size,
)
from wechat_media_exporter.workers import ExportWorker, ScanWorker


class CapabilityDialog(QDialog):
    def __init__(self, report: ScanReport, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("扫描能力报告")
        self.setMinimumSize(650, 430)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("微信媒体扫描能力报告", self)
        title.setStyleSheet("font-size: 17px; font-weight: 600;")
        layout.addWidget(title)

        note = QLabel(
            "这里只展示本次真实扫描结果。权限不足、目录不存在和缩略图会分别标记；"
            "不会把缩略图冒充原图，也不会把已发现文件数当成聊天媒体总数。",
            self,
        )
        note.setWordWrap(True)
        note.setObjectName("Muted")
        layout.addWidget(note)

        if report.device:
            device_text = (
                f"{report.device.model} · Android {report.device.android_version}"
                f" · 微信 {report.device.wechat_version}"
            )
        else:
            device_text = "尚未连接设备"
        summary = QLabel(
            f"{device_text}    |    图片 {len(report.images):,}    "
            f"视频 {len(report.videos):,}    待识别 {len(report.unknown):,}    "
            f"缩略图 {len(report.thumbnails):,}",
            self,
        )
        summary.setWordWrap(True)
        summary.setObjectName("SmallPill")
        layout.addWidget(summary)

        tree = QTreeWidget(self)
        tree.setColumnCount(3)
        tree.setHeaderLabels(["扫描目录", "状态", "说明"])
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        tree.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        tree.setColumnWidth(0, 300)
        tree.setColumnWidth(1, 78)
        for source in report.sources:
            item = QTreeWidgetItem(
                [
                    source.path,
                    source.state_label,
                    f"{source.message} · {source.file_count:,} 个文件",
                ]
            )
            if source.state == "readable":
                item.setForeground(1, Qt.GlobalColor.darkGreen)
            elif source.state in {"denied", "error"}:
                item.setForeground(1, Qt.GlobalColor.darkRed)
            else:
                item.setForeground(1, Qt.GlobalColor.darkYellow)
            tree.addTopLevelItem(item)
        layout.addWidget(tree, 1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        close_button = QPushButton("关闭", self)
        close_button.clicked.connect(self.accept)
        footer.addWidget(close_button)
        layout.addLayout(footer)


class MainWindow(QMainWindow):
    def __init__(self, *, demo: bool = False):
        super().__init__()
        self.demo = demo
        self.project_root = Path(__file__).resolve().parents[2]
        self.settings = QSettings("WeChatFilesOrganize", "WeChatFilesOrganize")
        self.report = demo_report() if demo else ScanReport(device=None)
        self.filter_mode = "all"
        self.search_term = ""
        self.sort_mode = "date"
        self._scan_worker: ScanWorker | None = None
        self._export_worker: ExportWorker | None = None
        self._card_by_path = {}
        self._month_sections: dict[str, MonthSection] = {}
        self._verified_export_count = 0

        self.setWindowTitle("微信媒体整理 [演示]" if demo else "微信媒体整理")
        self.setWindowIcon(
            QIcon(str(self.project_root / "wechat_media_exporter" / "assets" / "app-icon.svg"))
        )
        self.resize(1280, 840)
        self.setMinimumSize(980, 680)

        self._build_menu()
        self._build_ui()
        self._connect_signals()
        self._refresh_all()
        if demo:
            self._set_status("界面演示数据 · 连接真实手机后显示实际扫描结果")

    @property
    def data_directory(self) -> Path:
        location = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        )
        if not location:
            location = str(self.project_root / ".data")
        path = Path(location)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def export_directory(self) -> Path:
        configured = str(self.settings.value("export_directory", "")).strip()
        if configured:
            return Path(configured)
        documents = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        return Path(documents or str(self.project_root)) / "WeChatBackup"

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("文件")
        choose_action = QAction("选择导出目录…", self)
        choose_action.setShortcut("Ctrl+O")
        choose_action.triggered.connect(self.choose_export_directory)
        file_menu.addAction(choose_action)
        open_action = QAction("打开导出目录", self)
        open_action.triggered.connect(self.open_export_directory)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        scan_menu = menu_bar.addMenu("扫描")
        self.scan_action = QAction("重新扫描手机", self)
        self.scan_action.setShortcut("F5")
        self.scan_action.triggered.connect(self.start_scan)
        scan_menu.addAction(self.scan_action)
        self.cancel_action = QAction("取消当前任务", self)
        self.cancel_action.setEnabled(False)
        self.cancel_action.triggered.connect(self.cancel_current_task)
        scan_menu.addAction(self.cancel_action)

        view_menu = menu_bar.addMenu("视图")
        select_all_action = QAction("全选可见媒体", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.select_all_visible)
        view_menu.addAction(select_all_action)
        clear_selection_action = QAction("清除选择", self)
        clear_selection_action.triggered.connect(self.clear_selection)
        view_menu.addAction(clear_selection_action)
        focus_search_action = QAction("定位到搜索框", self)
        focus_search_action.setShortcut("Ctrl+F")
        focus_search_action.triggered.connect(lambda: self.search_edit.setFocus())
        view_menu.addAction(focus_search_action)

        help_menu = menu_bar.addMenu("帮助")
        capability_action = QAction("扫描能力报告", self)
        capability_action.triggered.connect(self.show_capability_report)
        help_menu.addAction(capability_action)
        usb_action = QAction("USB 调试连接指南", self)
        usb_action.triggered.connect(self.show_usb_help)
        help_menu.addAction(usb_action)
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("Root")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())
        body.addWidget(self._build_center(), 1)
        body.addWidget(self._build_right_panel())
        root_layout.addLayout(body, 1)
        root_layout.addWidget(self._build_status_bar())
        self.setCentralWidget(root)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame(self)
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(176)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        device = QFrame(sidebar)
        device.setObjectName("DeviceCard")
        device_layout = QHBoxLayout(device)
        device_layout.setContentsMargins(9, 8, 9, 8)
        device_layout.setSpacing(8)
        phone_icon = QLabel(device)
        phone_icon.setPixmap(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon).pixmap(22, 22)
        )
        device_layout.addWidget(phone_icon)
        device_copy = QVBoxLayout()
        device_copy.setSpacing(1)
        self.device_name = QLabel("等待设备", device)
        self.device_name.setStyleSheet("font-weight: 600;")
        self.device_state = QLabel("USB 未连接", device)
        self.device_state.setObjectName("Meta")
        device_copy.addWidget(self.device_name)
        device_copy.addWidget(self.device_state)
        device_layout.addLayout(device_copy, 1)
        layout.addWidget(device)

        category_label = QLabel("媒体分类", sidebar)
        category_label.setObjectName("Meta")
        category_label.setContentsMargins(7, 14, 0, 3)
        layout.addWidget(category_label)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: dict[str, QToolButton] = {}
        nav_specs = (
            ("all", "全部媒体", QStyle.StandardPixmap.SP_FileDialogListView),
            ("image", "图片", QStyle.StandardPixmap.SP_FileIcon),
            ("video", "视频", QStyle.StandardPixmap.SP_MediaPlay),
            ("duplicate", "重复文件", QStyle.StandardPixmap.SP_FileDialogContentsView),
        )
        for filter_mode, label, icon_type in nav_specs:
            button = QToolButton(sidebar)
            button.setObjectName("SidebarButton")
            button.setCheckable(True)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setIcon(self.style().standardIcon(icon_type))
            button.setIconSize(QSize(15, 15))
            button.setText(f"{label}    0")
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, mode=filter_mode: self.set_filter(mode))
            self.nav_group.addButton(button)
            self.nav_buttons[filter_mode] = button
            layout.addWidget(button)
        self.nav_buttons["all"].setChecked(True)

        scan_label = QLabel("扫描状态", sidebar)
        scan_label.setObjectName("Meta")
        scan_label.setContentsMargins(7, 14, 0, 3)
        layout.addWidget(scan_label)
        scan_panel = QFrame(sidebar)
        scan_panel.setObjectName("Panel")
        scan_layout = QVBoxLayout(scan_panel)
        scan_layout.setContentsMargins(9, 7, 9, 7)
        scan_layout.setSpacing(5)
        self.last_scan_label = self._info_row(scan_panel, "最近扫描", "尚未扫描")
        self.mode_label = self._info_row(scan_panel, "当前模式", "只读")
        scan_layout.addWidget(self.last_scan_label.parentWidget())
        scan_layout.addWidget(self.mode_label.parentWidget())
        layout.addWidget(scan_panel)
        layout.addStretch(1)

        storage_row = QHBoxLayout()
        storage_row.addWidget(QLabel("手机存储", sidebar))
        self.storage_value = QLabel("— / —", sidebar)
        self.storage_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        storage_row.addWidget(self.storage_value, 1)
        layout.addLayout(storage_row)

        storage_track = QProgressBar(sidebar)
        storage_track.setRange(0, 100)
        storage_track.setValue(70 if self.demo else 0)
        storage_track.setTextVisible(False)
        layout.addWidget(storage_track)

        privacy = QLabel("只读扫描，不上传媒体。\n备份校验后才可进入安全清理。", sidebar)
        privacy.setObjectName("Meta")
        privacy.setWordWrap(True)
        layout.addWidget(privacy)
        return sidebar

    def _build_center(self) -> QWidget:
        center = QWidget(self)
        layout = QVBoxLayout(center)
        layout.setContentsMargins(16, 13, 14, 12)
        layout.setSpacing(10)

        heading = QHBoxLayout()
        heading.setSpacing(10)
        title_column = QVBoxLayout()
        title_column.setSpacing(1)
        title = QLabel("媒体库", center)
        title.setObjectName("PageTitle")
        self.page_subtitle = QLabel(
            "按类型分开浏览，按月份自动归档，内容相同的文件只保留一份。", center
        )
        self.page_subtitle.setObjectName("PageSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(self.page_subtitle)
        heading.addLayout(title_column, 1)

        self.scan_button = QPushButton("重新扫描", center)
        self.scan_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.scan_button.clicked.connect(self.start_scan)
        heading.addWidget(self.scan_button)
        self.export_button = QPushButton("导出所选", center)
        self.export_button.setObjectName("PrimaryButton")
        self.export_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        )
        self.export_button.clicked.connect(self.start_export)
        heading.addWidget(self.export_button)
        layout.addLayout(heading)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self.image_stat = StatCard("图片", QStyle.StandardPixmap.SP_FileIcon, center)
        self.video_stat = StatCard("视频", QStyle.StandardPixmap.SP_MediaPlay, center)
        self.size_stat = StatCard("预计占用", QStyle.StandardPixmap.SP_DriveHDIcon, center)
        self.duplicate_stat = StatCard(
            "内容重复",
            QStyle.StandardPixmap.SP_FileDialogContentsView,
            center,
        )
        for card in (self.image_stat, self.video_stat, self.size_stat, self.duplicate_stat):
            stats_row.addWidget(card, 1)
        layout.addLayout(stats_row)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(7)
        self.search_edit = QLineEdit(center)
        self.search_edit.setPlaceholderText("搜索文件名或来源…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMinimumWidth(190)
        toolbar.addWidget(self.search_edit, 1)
        self.sort_combo = QComboBox(center)
        self.sort_combo.addItem("时间从新到旧", "date")
        self.sort_combo.addItem("文件从大到小", "size")
        self.sort_combo.addItem("文件名 A-Z", "name")
        self.sort_combo.setMinimumWidth(132)
        toolbar.addWidget(self.sort_combo)
        self.selection_label = QLabel("已选 0 项", center)
        self.selection_label.setObjectName("Muted")
        self.selection_label.setMinimumWidth(74)
        self.selection_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        toolbar.addWidget(self.selection_label)
        layout.addLayout(toolbar)

        self.month_strip = QWidget(center)
        self.month_strip_layout = QHBoxLayout(self.month_strip)
        self.month_strip_layout.setContentsMargins(0, 0, 0, 0)
        self.month_strip_layout.setSpacing(5)
        layout.addWidget(self.month_strip)

        self.scroll = QScrollArea(center)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_content = QWidget(self.scroll)
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 2, 4, 2)
        self.scroll_layout.setSpacing(5)
        self.scroll_layout.addStretch(1)
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll, 1)
        return center

    def _build_right_panel(self) -> QWidget:
        right = QWidget(self)
        right.setFixedWidth(252)
        layout = QVBoxLayout(right)
        layout.setContentsMargins(0, 13, 14, 12)
        layout.setSpacing(9)

        rules = QFrame(right)
        rules.setObjectName("Panel")
        rules_layout = QVBoxLayout(rules)
        rules_layout.setContentsMargins(12, 11, 12, 11)
        rules_layout.setSpacing(7)
        rules_title = QHBoxLayout()
        title = QLabel("整理规则", rules)
        title.setObjectName("SectionTitle")
        rules_title.addWidget(title)
        auto_badge = QLabel("自动归档", rules)
        auto_badge.setObjectName("Meta")
        rules_title.addWidget(auto_badge, 0, Qt.AlignmentFlag.AlignRight)
        rules_layout.addLayout(rules_title)
        self.rule_summary = QLabel("0 项 · 0 B", rules)
        self.rule_summary.setStyleSheet("font-size: 18px; font-weight: 600;")
        rules_layout.addWidget(self.rule_summary)

        folder = QLabel(
            "<b>WeChatBackup</b><br>"
            "└─ 2026<br>"
            "&nbsp;&nbsp;&nbsp;└─ 10<br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├─ Images/<br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└─ Videos/",
            rules,
        )
        folder.setStyleSheet(
            "font-family: 'Cascadia Mono', Consolas; font-size: 10px; "
            "background: #F4F6F3; border-radius: 6px; padding: 9px; color: #5F6A61;"
        )
        rules_layout.addWidget(folder)
        rules_layout.addWidget(self._rule_row(rules, "媒体分类", "图片 / 视频"))
        rules_layout.addWidget(self._rule_row(rules, "去重方式", "SHA-256"))
        layout.addWidget(rules)

        safety = QFrame(right)
        safety.setObjectName("SafetyPanel")
        safety_layout = QVBoxLayout(safety)
        safety_layout.setContentsMargins(12, 11, 12, 11)
        safety_layout.setSpacing(8)
        safety_title = QHBoxLayout()
        title = QLabel("扫描与安全", safety)
        title.setObjectName("SectionTitle")
        safety_title.addWidget(title)
        read_only = QLabel("只读", safety)
        read_only.setObjectName("GreenPill")
        safety_title.addWidget(read_only, 0, Qt.AlignmentFlag.AlignRight)
        safety_layout.addLayout(safety_title)

        self.coverage_label = QLabel("尚未扫描媒体来源", safety)
        self.coverage_label.setWordWrap(True)
        self.coverage_label.setObjectName("Muted")
        safety_layout.addWidget(self.coverage_label)

        self.report_button = QPushButton("查看扫描范围与原因", safety)
        self.report_button.setObjectName("SoftButton")
        self.report_button.clicked.connect(self.show_capability_report)
        safety_layout.addWidget(self.report_button)

        authorization = QHBoxLayout()
        authorization.addWidget(QLabel("清理授权", safety))
        manual = QLabel("必须由用户手动点击", safety)
        manual.setStyleSheet("color: #087B46; font-weight: 600;")
        authorization.addWidget(manual, 0, Qt.AlignmentFlag.AlignRight)
        safety_layout.addLayout(authorization)

        self.cleanup_button = QPushButton("完成备份校验后手动选择文件", safety)
        self.cleanup_button.setEnabled(False)
        self.cleanup_button.clicked.connect(self.manual_cleanup)
        safety_layout.addWidget(self.cleanup_button)
        no_delete = QLabel("软件不会自动删除任何手机文件", safety)
        no_delete.setObjectName("Meta")
        no_delete.setAlignment(Qt.AlignmentFlag.AlignCenter)
        safety_layout.addWidget(no_delete)
        layout.addWidget(safety)
        layout.addStretch(1)
        return right

    def _build_status_bar(self) -> QWidget:
        bar = QFrame(self)
        bar.setObjectName("StatusBar")
        bar.setFixedHeight(51)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(13, 7, 13, 7)
        layout.setSpacing(10)

        self.status_icon = QLabel(bar)
        self.status_icon.setPixmap(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton).pixmap(18, 18)
        )
        layout.addWidget(self.status_icon)

        copy = QVBoxLayout()
        copy.setSpacing(1)
        self.task_title = QLabel("等待导出任务", bar)
        self.task_title.setStyleSheet("font-weight: 600;")
        self.task_detail = QLabel("连接手机并完成扫描后，可勾选媒体批量导出。", bar)
        self.task_detail.setObjectName("Meta")
        copy.addWidget(self.task_title)
        copy.addWidget(self.task_detail)
        layout.addLayout(copy, 1)

        self.progress_bar = QProgressBar(bar)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(185)
        layout.addWidget(self.progress_bar)
        self.progress_text = QLabel("0%", bar)
        self.progress_text.setMinimumWidth(34)
        self.progress_text.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.progress_text)
        return bar

    def _connect_signals(self) -> None:
        self.search_edit.textChanged.connect(self._on_search_changed)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        self.search_edit.returnPressed.connect(self._refresh_media_view)

    def _on_search_changed(self, text: str) -> None:
        self.search_term = text.strip().lower()
        self._schedule_refresh()

    def _schedule_refresh(self) -> None:
        QTimer.singleShot(80, self._refresh_media_view)

    def _on_sort_changed(self, _index: int) -> None:
        self.sort_mode = str(self.sort_combo.currentData())
        self._refresh_media_view()

    def set_filter(self, mode: str) -> None:
        self.filter_mode = mode
        button = self.nav_buttons.get(mode)
        if button:
            button.setChecked(True)
        self._refresh_media_view()

    def _filtered_items(self) -> list[MediaItem]:
        items = []
        for item in self.report.items:
            if self.filter_mode == "image" and item.kind != "image":
                continue
            if self.filter_mode == "video" and item.kind != "video":
                continue
            if self.filter_mode == "duplicate" and not item.duplicate_of:
                continue
            haystack = f"{item.name} {item.remote_path} {item.source_root}".lower()
            if self.search_term and self.search_term not in haystack:
                continue
            items.append(item)
        return self._sort_items(items)

    def _sort_items(self, items: list[MediaItem]) -> list[MediaItem]:
        if self.sort_mode == "size":
            return sorted(items, key=lambda item: item.size_bytes, reverse=True)
        if self.sort_mode == "name":
            return sorted(items, key=lambda item: item.name.lower())
        return sorted(items, key=lambda item: item.modified_at, reverse=True)

    def _refresh_all(self) -> None:
        report = self.report
        if report.device:
            self.device_name.setText(report.device.display_name)
            self.device_state.setText(f"Android {report.device.android_version}")
            self.mode_label.setText("只读")
        else:
            self.device_name.setText("等待设备")
            self.device_state.setText("USB 未连接")
            self.mode_label.setText("未连接")

        counts = {
            "all": len(report.items),
            "image": len(report.images),
            "video": len(report.videos),
            "duplicate": len(report.duplicates),
        }
        labels = {
            "all": "全部媒体",
            "image": "图片",
            "video": "视频",
            "duplicate": "重复文件",
        }
        for mode, button in self.nav_buttons.items():
            button.setText(f"{labels[mode]}    {counts[mode]:,}")

        self.image_stat.set_value(f"{len(report.images):,} 项")
        self.video_stat.set_value(f"{len(report.videos):,} 项")
        self.size_stat.set_value(format_size(report.total_bytes))
        self.duplicate_stat.set_value(f"{len(report.duplicates):,} 项")
        self.last_scan_label.setText(
            report.scanned_at.astimezone().strftime("%m-%d %H:%M") if report.items else "尚未扫描"
        )

        readable = report.readable_sources
        total_sources = len(report.sources)
        if total_sources:
            denied = sum(source.state in {"denied", "error"} for source in report.sources)
            self.coverage_label.setText(
                f"{readable} / {total_sources} 个媒体来源可读取"
                + (f"；{denied} 个目录权限不足或读取失败。" if denied else "。")
                + " 缩略图会单独标记，不冒充原图。"
            )
        else:
            self.coverage_label.setText(
                "尚未扫描媒体来源。连接手机后重新扫描，即可查看真实权限结果。"
            )
        if self.demo:
            self.storage_value.setText("178 / 256 GB")

        self._refresh_month_strip()
        self._refresh_media_view()
        self._refresh_selection()

    def _refresh_month_strip(self) -> None:
        clear_layout(self.month_strip_layout)
        months = self.report.months()
        self.month_buttons: list[QPushButton] = []
        for index, (month_key, label, items) in enumerate(months):
            button = QPushButton(
                f"{label}\n{len(items)} 项 · {format_size(sum(item.size_bytes for item in items))}",
                self.month_strip,
            )
            button.setObjectName("MonthButton")
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setChecked(index == 0)
            button.clicked.connect(lambda _checked=False, key=month_key: self._scroll_to_month(key))
            self.month_strip_layout.addWidget(button)
            self.month_buttons.append(button)
        if len(months) > 3:
            older = QPushButton("更早\n继续向下浏览", self.month_strip)
            older.setObjectName("MonthButton")
            older.clicked.connect(
                lambda: self.scroll.verticalScrollBar().setValue(
                    self.scroll.verticalScrollBar().maximum()
                )
            )
            self.month_strip_layout.addWidget(older)
        self.month_strip_layout.addStretch(1)

    def _refresh_media_view(self) -> None:
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._month_sections.clear()
        self._card_by_path.clear()

        grouped: dict[str, list[MediaItem]] = {}
        for item in self._filtered_items():
            grouped.setdefault(item.month_key, []).append(item)

        if not grouped:
            self.scroll_layout.addWidget(EmptyState(self.scroll_content))
            self.scroll_layout.addStretch(1)
            return

        for month_key in sorted(grouped, reverse=True):
            items = grouped[month_key]
            section = MonthSection(month_key, items[0].month_label, items, self.scroll_content)
            section.selection_changed.connect(self._on_card_selection)
            section.select_month_requested.connect(
                lambda target: target.set_all_selected(
                    any(not card.selected for card in target.cards)
                )
            )
            self.scroll_layout.addWidget(section)
            self._month_sections[month_key] = section
            for card in section.cards:
                self._card_by_path[card.item.remote_path] = card
        self.scroll_layout.addStretch(1)

        if not self.report.items:
            self._set_status("未发现媒体。请连接手机、开启 USB 调试后重新扫描。")
        elif self.report.warning:
            self._set_status(self.report.warning)

    def _scroll_to_month(self, month_key: str) -> None:
        if month_key not in self._month_sections:
            self._set_status("当前筛选条件下没有这个月份的媒体。")
            return
        month_order = sorted(self._month_sections, reverse=True)
        for index, button in enumerate(self.month_buttons):
            button.setChecked(index == month_order.index(month_key))
        section = self._month_sections.get(month_key)
        if section:
            self.scroll.ensureWidgetVisible(section, 0, 8)

    def _on_card_selection(self, _item: MediaItem, _selected: bool) -> None:
        self._refresh_selection()

    def _refresh_selection(self) -> None:
        selected = [item for item in self.report.items if item.selected]
        size = sum(item.size_bytes for item in selected)
        self.selection_label.setText(f"已选 {len(selected)} 项")
        self.export_button.setEnabled(bool(selected) and not self.demo)
        self.cleanup_button.setEnabled(False)
        first_month = self.report.months()
        if first_month:
            _, label, items = first_month[0]
            self.rule_summary.setText(
                f"{len(items):,} 项 · {format_size(sum(item.size_bytes for item in items))}"
            )
        else:
            self.rule_summary.setText("0 项 · 0 B")
        if selected and self.demo:
            self.export_button.setEnabled(True)
        if selected:
            self._set_status(f"已选择 {len(selected)} 项，共 {format_size(size)}。")

    def select_all_visible(self) -> None:
        for card in self._card_by_path.values():
            card.set_selected(True, notify=False)
        self._refresh_selection()

    def clear_selection(self) -> None:
        for card in self._card_by_path.values():
            card.set_selected(False, notify=False)
        self._refresh_selection()

    def start_scan(self) -> None:
        if self._scan_running:
            return
        if self.demo:
            self.report = demo_report()
            self._refresh_all()
            self._set_status("已重新载入演示数据。")
            return

        self._scan_running = True
        self.scan_action.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.cancel_action.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_text.setText("0%")
        self.task_title.setText("正在扫描手机")
        self.task_detail.setText("正在检测 ADB 设备和微信媒体目录…")
        self._scan_worker = ScanWorker(self.project_root, self)
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.succeeded.connect(self._on_scan_complete)
        self._scan_worker.failed.connect(self._on_scan_failed)
        self._scan_worker.finished.connect(self._on_worker_finished)
        self._scan_worker.start()

    def _on_scan_progress(self, value: int, message: str) -> None:
        self.progress_bar.setValue(value)
        self.progress_text.setText(f"{value}%")
        self.task_detail.setText(message)

    def _on_scan_complete(self, report: object) -> None:
        if not isinstance(report, ScanReport):
            return
        self.report = report
        self._refresh_all()
        try:
            write_scan_reports(report, self.data_directory / "Reports")
        except OSError as exc:
            self._set_status(f"扫描完成，但报告写入失败：{exc}")
            return
        if report.items:
            self._set_status(
                f"扫描完成：发现 {len(report.items):,} 个媒体文件，用时 "
                f"{report.elapsed_seconds:.1f} 秒。"
            )
        else:
            self._set_status("扫描完成，但当前目录范围内未发现可访问媒体。")

    def _on_scan_failed(self, message: str) -> None:
        self._set_status(message)
        QMessageBox.warning(self, "无法扫描手机", message)

    def _on_worker_finished(self) -> None:
        self._scan_running = False
        self._export_running = False
        self.scan_action.setEnabled(True)
        self.scan_button.setEnabled(True)
        self.cancel_action.setEnabled(False)
        self._refresh_selection()

    @property
    def _scan_running(self) -> bool:
        return bool(getattr(self, "_scan_active", False))

    @_scan_running.setter
    def _scan_running(self, value: bool) -> None:
        self._scan_active = value

    @property
    def _export_running(self) -> bool:
        return bool(getattr(self, "_export_active", False))

    @_export_running.setter
    def _export_running(self, value: bool) -> None:
        self._export_active = value

    def start_export(self) -> None:
        if self._scan_running or self._export_running:
            return
        selected = [item for item in self.report.items if item.selected]
        if not selected:
            QMessageBox.information(self, "未选择文件", "请先勾选需要导出的图片或视频。")
            return
        if self.demo:
            self._set_status("当前是演示数据，连接真实手机后可执行导出。")
            return
        if not self.report.device:
            QMessageBox.warning(self, "设备不可用", "请先连接 Android 手机并完成扫描。")
            return

        destination = self.choose_export_directory(show_message=False)
        if destination is None:
            return
        self._export_running = True
        self.scan_action.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.cancel_action.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_text.setText("0%")
        self.task_title.setText("正在导出所选媒体")
        self.task_detail.setText("准备连接手机并创建本地文件…")
        self._export_worker = ExportWorker(
            self.project_root,
            self.report.device.serial,
            selected,
            destination,
            self.data_directory / "content-index.sqlite3",
            self,
        )
        self._export_worker.progress.connect(self._on_export_progress)
        self._export_worker.succeeded.connect(self._on_export_complete)
        self._export_worker.failed.connect(self._on_export_failed)
        self._export_worker.finished.connect(self._on_worker_finished)
        self._export_worker.start()

    def _on_export_progress(self, value: object) -> None:
        if not isinstance(value, ExportProgress):
            return
        self.progress_bar.setValue(value.percent)
        self.progress_text.setText(f"{value.percent}%")
        speed = format_size(int(value.bytes_per_second)) + "/s"
        remaining = (
            f"约剩 {value.remaining_seconds} 秒"
            if value.remaining_seconds is not None
            else "正在估算剩余时间"
        )
        self.task_title.setText(f"正在导出 {value.completed} / {value.total}")
        self.task_detail.setText(f"{value.current_name} · {speed} · {remaining}")

    def _on_export_complete(self, result: object) -> None:
        if not isinstance(result, ExportResult):
            return
        completed = len(result.exported) + len(result.duplicates)
        self._verified_export_count += len(result.exported)
        self.progress_bar.setValue(100)
        self.progress_text.setText("100%")
        self.task_title.setText("导出完成")
        self.task_detail.setText(
            f"已导出 {len(result.exported)} 项，跳过重复 {len(result.duplicates)} 项，"
            f"失败 {len(result.failed)} 项。报告已保存到导出目录。"
        )
        self._set_status(f"完成 {completed} 项；重复文件没有再次写入磁盘。")
        if result.failed:
            failures = "\n".join(f"{item.name}: {message}" for item, message in result.failed[:8])
            QMessageBox.warning(self, "部分文件导出失败", failures)
        elif completed:
            QMessageBox.information(
                self,
                "导出完成",
                "导出和 SHA-256 校验已完成。手机清理仍需用户在后续清理界面中手动确认。",
            )

    def _on_export_failed(self, message: str) -> None:
        self._set_status(message)
        QMessageBox.critical(self, "导出失败", message)

    def cancel_current_task(self) -> None:
        if self._scan_worker and self._scan_running:
            self._scan_worker.cancel()
            self._set_status("正在取消扫描…")
        if self._export_worker and self._export_running:
            self._export_worker.cancel()
            self._set_status("将在当前文件传输完成后取消导出…")

    def choose_export_directory(self, *, show_message: bool = True) -> Path | None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "选择微信媒体导出目录",
            str(self.export_directory.parent),
        )
        if not selected:
            return None
        path = Path(selected) / "WeChatBackup"
        self.settings.setValue("export_directory", str(path))
        if show_message:
            self._set_status(f"导出目录：{path}")
        return path

    def open_export_directory(self) -> None:
        path = self.export_directory
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def show_capability_report(self) -> None:
        CapabilityDialog(self.report, self).exec()

    def show_usb_help(self) -> None:
        QMessageBox.information(
            self,
            "USB 调试连接指南",
            "1. 在手机设置中连续点击版本号，开启开发者选项。\n"
            "2. 打开“USB 调试”。\n"
            "3. 用数据线连接电脑，并在手机上允许调试授权。\n"
            "4. 回到本软件点击“重新扫描”。\n\n"
            "软件只读取普通 ADB 权限可访问的文件，不需要 Root，也不会修改微信数据库。",
        )

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "关于微信媒体整理",
            "微信媒体整理 0.1.0\n\n"
            "本地运行，不上传媒体。\n"
            "通过 ADB 读取用户可访问的微信图片和视频。",
        )

    def manual_cleanup(self) -> None:
        QMessageBox.information(
            self,
            "安全清理尚未开放",
            "清理功能仍在安全验证阶段。只有完成导出、大小校验和 SHA-256 校验后，"
            "用户才能手动选择待清理文件，软件不会自动删除。",
        )

    def _set_status(self, message: str) -> None:
        self.task_detail.setText(message)

    def _info_row(self, parent: QWidget, label: str, value: str) -> QLabel:
        row = QWidget(parent)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(5)
        key = QLabel(label, row)
        key.setObjectName("Meta")
        row_layout.addWidget(key)
        val = QLabel(value, row)
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row_layout.addWidget(val, 1)
        return val

    def _rule_row(self, parent: QWidget, label: str, value: str) -> QWidget:
        row = QWidget(parent)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 3, 0, 3)
        key = QLabel(label, row)
        key.setObjectName("Meta")
        value_label = QLabel(value, row)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(key)
        layout.addWidget(value_label, 1)
        return row

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.cancel()
            self._scan_worker.wait(2000)
        if self._export_worker and self._export_worker.isRunning():
            self._export_worker.cancel()
            self._export_worker.wait(3000)
        super().closeEvent(event)
