from wechat_media_exporter.demo import demo_report


def test_demo_report_groups_by_month() -> None:
    report = demo_report()
    assert report.device is not None
    assert len(report.images) == 6
    assert len(report.videos) == 3
    assert len(report.file_items) == 3
    assert len(report.duplicates) == 2
    assert [label for _, label, _ in report.months()] == ["2026 年 10 月", "2026 年 9 月"]
    assert report.months()[0][2][0].modified_at >= report.months()[0][2][-1].modified_at
    assert report.readable_sources == 3
