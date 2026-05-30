from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent


def main() -> int:
    prepare_runtime()

    try:
        from gui_tabs import PyFFmpegStudioApp

        app = PyFFmpegStudioApp()
        app.mainloop()
        return 0
    except Exception as exc:
        log_path = write_startup_log(exc)
        show_startup_error(exc, log_path)
        return 1


def prepare_runtime() -> None:
    os.chdir(APP_DIR)
    app_dir_text = str(APP_DIR)
    if app_dir_text not in sys.path:
        sys.path.insert(0, app_dir_text)


def write_startup_log(exc: BaseException) -> Path:
    logs_dir = APP_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "startup_error.log"
    log_path.write_text(
        "PyFFmpeg-Studio startup error\n\n"
        f"{type(exc).__name__}: {exc}\n\n"
        f"{traceback.format_exc()}",
        encoding="utf-8",
    )
    return log_path


def show_startup_error(exc: BaseException, log_path: Path) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "PyFFmpeg-Studio",
            "Не вдалося запустити програму.\n\n"
            f"{type(exc).__name__}: {exc}\n\n"
            f"Лог: {log_path}",
        )
        root.destroy()
    except Exception:
        print(f"Failed to start PyFFmpeg-Studio: {exc}", file=sys.stderr)
        print(f"Log: {log_path}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
