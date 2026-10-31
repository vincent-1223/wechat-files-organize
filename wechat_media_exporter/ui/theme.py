from __future__ import annotations

APP_STYLESHEET = """
QWidget {
    color: #1B231D;
    font-family: "Microsoft YaHei UI", "Segoe UI";
    font-size: 12px;
}

QMainWindow, QWidget#Root {
    background: #F7F8F6;
}

QMenuBar {
    background: #FFFFFF;
    border-bottom: 1px solid #E6EAE5;
    padding: 2px 6px;
    spacing: 2px;
}

QMenuBar::item {
    padding: 5px 9px;
    border-radius: 4px;
    color: #4E5A51;
    background: transparent;
}

QMenuBar::item:selected {
    background: #F1F4F0;
    color: #1B231D;
}

QMenu {
    background: #FFFFFF;
    border: 1px solid #DDE3DC;
    padding: 5px;
}

QMenu::item {
    padding: 7px 28px 7px 10px;
    border-radius: 4px;
}

QMenu::item:selected {
    background: #E9F5EE;
    color: #087B46;
}

QFrame#Sidebar {
    background: #F4F6F3;
    border-right: 1px solid #E3E7E2;
}

QFrame#DeviceCard, QFrame#Panel, QFrame#StatCard, QFrame#StatusBar {
    background: #FFFFFF;
    border: 1px solid #E4E8E3;
    border-radius: 9px;
}

QFrame#SafetyPanel {
    background: #FFFFFF;
    border: 1px solid #D5E8DC;
    border-radius: 9px;
}

QLabel#AppTitle {
    color: #1B231D;
    font-size: 14px;
    font-weight: 600;
}

QLabel#PageTitle {
    color: #18201B;
    font-size: 23px;
    font-weight: 600;
}

QLabel#PageSubtitle, QLabel#Muted, QLabel#Meta, QLabel#SectionMeta {
    color: #69736B;
}

QLabel#SectionTitle {
    color: #1B231D;
    font-size: 14px;
    font-weight: 600;
}

QLabel#SmallPill {
    color: #69736B;
    background: #F1F4F0;
    border-radius: 9px;
    padding: 2px 7px;
}

QLabel#GreenPill {
    color: #087B46;
    background: #E5F5EC;
    border-radius: 9px;
    padding: 2px 7px;
}

QLabel#WarnPill {
    color: #9A5B00;
    background: #FFF1D8;
    border-radius: 9px;
    padding: 2px 7px;
}

QPushButton {
    min-height: 31px;
    padding: 0 11px;
    color: #273129;
    background: #FFFFFF;
    border: 1px solid #DDE3DC;
    border-radius: 7px;
}

QPushButton:hover {
    background: #F5F7F4;
    border-color: #C8D1C9;
}

QPushButton:pressed {
    background: #EEF2ED;
}

QPushButton:disabled {
    color: #97A099;
    background: #F6F7F5;
    border-color: #E7EAE5;
}

QPushButton#PrimaryButton {
    color: #FFFFFF;
    background: #07894B;
    border-color: #07894B;
    font-weight: 600;
}

QPushButton#PrimaryButton:hover {
    background: #067B44;
    border-color: #067B44;
}

QPushButton#PrimaryButton:disabled {
    color: #E8F2EC;
    background: #9BC7AD;
    border-color: #9BC7AD;
}

QPushButton#SoftButton {
    color: #087B46;
    background: #E8F5EE;
    border-color: #E8F5EE;
}

QPushButton#SoftButton:hover {
    background: #DDF1E5;
    border-color: #DDF1E5;
}

QToolButton#SidebarButton {
    min-height: 34px;
    padding: 0 8px;
    color: #667168;
    background: transparent;
    border: 0;
    border-radius: 7px;
    text-align: left;
}

QToolButton#SidebarButton:hover {
    background: #EAEEE9;
    color: #273129;
}

QToolButton#SidebarButton:checked {
    color: #087B46;
    background: #E4F3EA;
    font-weight: 600;
}

QPushButton#MonthButton {
    min-width: 86px;
    min-height: 44px;
    padding: 4px 9px;
    color: #667168;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 7px;
    text-align: left;
}

QPushButton#MonthButton:hover {
    background: #F2F5F1;
}

QPushButton#MonthButton:checked {
    color: #087B46;
    background: #E8F5EE;
    border-color: #BFE3CD;
}

QLineEdit, QComboBox {
    min-height: 31px;
    padding: 0 9px;
    color: #1B231D;
    background: #FFFFFF;
    border: 1px solid #DDE3DC;
    border-radius: 7px;
    selection-background-color: #CFEEDC;
}

QLineEdit:focus, QComboBox:focus {
    border-color: #61B884;
}

QComboBox::drop-down {
    width: 24px;
    border: 0;
}

QFrame#MediaCard {
    background: #FFFFFF;
    border: 1px solid #E4E8E3;
    border-radius: 8px;
}

QFrame#MediaCard:hover {
    border-color: #8BCAA4;
}

QFrame#MediaCard[selected="true"] {
    border: 1px solid #07894B;
}

QLabel#MediaName {
    color: #1B231D;
    font-size: 11px;
    font-weight: 600;
}

QLabel#MediaMeta {
    color: #707A72;
    font-size: 10px;
}

QLabel#DuplicateMeta {
    color: #A86600;
    font-size: 10px;
}

QScrollArea {
    background: transparent;
    border: 0;
}

QScrollArea > QWidget > QWidget {
    background: transparent;
}

QScrollBar:vertical {
    width: 10px;
    background: transparent;
    margin: 2px;
}

QScrollBar::handle:vertical {
    min-height: 28px;
    background: #CAD2CA;
    border-radius: 3px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QProgressBar {
    min-height: 6px;
    max-height: 6px;
    background: #E9EDE8;
    border: 0;
    border-radius: 3px;
    text-align: center;
}

QProgressBar::chunk {
    background: #07894B;
    border-radius: 3px;
}

QStatusBar {
    background: #FFFFFF;
    border-top: 1px solid #E5E9E4;
}

QDialog {
    background: #F7F8F6;
}

QTreeWidget {
    background: #FFFFFF;
    border: 1px solid #DFE4DE;
    border-radius: 7px;
    alternate-background-color: #F8FAF7;
}

QHeaderView::section {
    padding: 7px;
    color: #5F6A61;
    background: #F3F6F2;
    border: 0;
    border-bottom: 1px solid #E2E7E1;
}
"""
