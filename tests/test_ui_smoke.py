import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from wechat_media_exporter.demo import demo_report
from wechat_media_exporter.ui.main_window import MainWindow
from wechat_media_exporter.ui.widgets import MediaCard


def test_demo_window_filters_media() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(demo=True)
    assert window.report.device is not None
    assert len(window.report.items) == 9
    assert window.nav_buttons["all"].text().endswith("9")
    assert "安全清理" in window.cleanup_nav_button.text()
    assert window.cleanup_button.isEnabled()

    window.set_filter("video")
    app.processEvents()
    video_cards = sum(len(section.cards) for section in window._month_sections.values())
    assert video_cards == 3

    window.search_edit.setText("IMG_20261028")
    app.processEvents()
    window._refresh_media_view()
    visible_cards = sum(len(section.cards) for section in window._month_sections.values())
    assert visible_cards == 0

    window.close()


def test_media_card_click_opens_and_checkbox_toggles() -> None:
    app = QApplication.instance() or QApplication([])
    item = demo_report().images[0]
    card = MediaCard(item)
    opened: list[str] = []
    card.open_requested.connect(lambda selected: opened.append(selected.remote_path))

    QTest.mouseClick(
        card,
        Qt.MouseButton.LeftButton,
        pos=QPoint(20, 20),
    )
    assert opened == [item.remote_path]

    before = card.selected
    QTest.mouseClick(
        card,
        Qt.MouseButton.LeftButton,
        pos=QPoint(card.width() - 10, 10),
    )
    app.processEvents()
    assert card.selected is not before
