import json
from pathlib import Path

from wechat_media_exporter.demo import demo_report
from wechat_media_exporter.reports import write_scan_reports


def test_scan_reports_are_written(tmp_path: Path) -> None:
    report = demo_report()
    json_path, markdown_path = write_scan_reports(report, tmp_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert payload["summary"]["images"] == 6
    assert payload["summary"]["videos"] == 3
    assert payload["device"]["model"] == "Xiaomi 14"
    assert "微信媒体扫描报告" in markdown_path.read_text(encoding="utf-8")
    assert "Android/data" in markdown_path.read_text(encoding="utf-8")
