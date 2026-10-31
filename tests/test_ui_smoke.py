import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from wechat_media_exporter.ui.main_window import MainWindow


def test_demo_window_filters_media() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(demo=True)
    assert window.report.device is not None
    assert len(window.report.items) == 9
    assert window.nav_buttons["all"].text().endswith("9")

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
