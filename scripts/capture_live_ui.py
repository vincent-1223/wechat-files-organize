from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from wechat_media_exporter.ui.main_window import MainWindow
from wechat_media_exporter.ui.theme import APP_STYLESHEET


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描已连接手机并截取真实数据界面")
    parser.add_argument("output", type=Path)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)
    window = MainWindow()
    window.show()
    window.start_scan()

    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    def wait_for_scan() -> None:
        if window._scan_running:
            QTimer.singleShot(200, wait_for_scan)
            return
        QTimer.singleShot(
            300,
            lambda: (
                window.grab().save(str(output), "PNG"),
                app.quit(),
            ),
        )

    QTimer.singleShot(args.timeout * 1000, app.quit)
    QTimer.singleShot(250, wait_for_scan)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
