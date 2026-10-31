from __future__ import annotations

import os
import traceback
from pathlib import Path

from wechat_media_exporter.app import main

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        local_app_data = os.environ.get("LOCALAPPDATA")
        log_root = Path(local_app_data or ".") / "WeChatFilesOrganize"
        log_root.mkdir(parents=True, exist_ok=True)
        (log_root / "startup-error.log").write_text(traceback.format_exc(), encoding="utf-8")
        raise
