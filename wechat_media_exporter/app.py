from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from wechat_media_exporter.adb import AdbClient, AdbError, find_adb
from wechat_media_exporter.ui.main_window import MainWindow
from wechat_media_exporter.ui.theme import APP_STYLESHEET


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="微信图片视频整理工具")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="使用演示数据预览界面，不读取手机",
    )
    parser.add_argument(
        "--screenshot",
        type=Path,
        help="启动后将窗口保存为 PNG 并退出，用于界面检查",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("微信媒体整理")
    app.setApplicationDisplayName("微信媒体整理")
    app.setOrganizationName("WeChatFilesOrganize")
    app.setApplicationVersion("0.2.1")
    project_root = Path(__file__).resolve().parent.parent
    app.setWindowIcon(
        QIcon(str(project_root / "wechat_media_exporter" / "assets" / "app-icon.svg"))
    )
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow(demo=arguments.demo)
    window.show()

    if not arguments.demo:
        try:
            adb_path = find_adb(project_root)
            if adb_path and any(
                device.state == "device" for device in AdbClient(adb_path).list_devices()
            ):
                QTimer.singleShot(250, window.start_scan)
        except AdbError:
            pass

    if arguments.screenshot:
        output = arguments.screenshot.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)

        def capture() -> None:
            app.processEvents()
            window.grab().save(str(output), "PNG")
            app.quit()

        QTimer.singleShot(700, capture)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
