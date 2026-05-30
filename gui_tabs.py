from __future__ import annotations

import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    DND_FILES = None
    BaseTk = tk.Tk
else:
    BaseTk = TkinterDnD.Tk

from ffmpeg_worker import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    CommandBuildError,
    CommandJob,
    FfmpegResult,
    build_command_job,
    format_duration,
    probe_media_info,
    run_cmd_command,
    run_ffmpeg,
)

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "settings.json"
ICON_PATH = APP_DIR / "icon_PyFFmpeg_Studio.png"

LANGUAGE_NAMES = {
    "uk": "Українська",
    "en": "English",
}

TRANSLATIONS = {
    "en": {
        "Файл не обрано": "No file selected",
        "Готово": "Ready",
        "Перетягніть медіафайл сюди або натисніть «Обрати файл»": "Drop a media file here or click \"Choose file\"",
        "Drag&Drop потребує tkinterdnd2. Поки скористайтесь кнопкою «Обрати файл»": "Drag & drop requires tkinterdnd2. Use the \"Choose file\" button for now",
        "Конвертація, обрізання, GIF, розкадровка та ручні CMD-команди в одному вікні": "Conversion, trimming, GIFs, screenshots, and manual CMD commands in one window",
        "Налаштування": "Settings",
        "Вхідний файл": "Input file",
        "Обрати файл": "Choose file",
        "Назва": "Name",
        "Формат": "Format",
        "Тривалість": "Duration",
        "Відпустіть файл, щоб завантажити його": "Release the file to load it",
        "Перетягніть саме файл, не папку.": "Drop a file, not a folder.",
        "Активний файл: {name}": "Active file: {name}",
        "Відео": "Video",
        "Аудіо": "Audio",
        "Фото": "Photo",
        "Ручна команда": "Manual command",
        "Конвертація та стиснення": "Conversion and compression",
        "Обрізання та Склеювання": "Trim and merge",
        "Аудіодоріжка відео": "Video audio track",
        "Відеокодек": "Video codec",
        "Якість / CRF": "Quality / CRF",
        "Роздільна здатність": "Resolution",
        "Оригінал": "Original",
        "Початок обрізання": "Trim start",
        "Кінець обрізання": "Trim end",
        "00:00:05 або 5": "00:00:05 or 5",
        "00:00:20 або 20": "00:00:20 or 20",
        "Додати файли до списку": "Add files to list",
        "Очистити список": "Clear list",
        "Вирізати звук повністю": "Remove audio completely",
        "Замінити аудіо": "Replace audio",
        "Скинути аудіо": "Reset audio",
        "Зміна формату": "Format change",
        "Обробка звуку": "Audio processing",
        "Бітрейт для MP3": "MP3 bitrate",
        "Старт": "Start",
        "Фініш": "Finish",
        "Гучність": "Volume",
        "Ефект плавного початку (Fade-in)": "Fade-in effect",
        "Плавного кінця (Fade-out)": "Fade-out",
        "Конвертація зображень": "Image conversion",
        "Створення GIF": "Create GIF",
        "Розкадровка": "Screenshots",
        "FFmpeg конвертує поодинокі фотографії так само, як і відео.": "FFmpeg converts single images the same way it converts video.",
        "Початок відрізку": "Clip start",
        "Кінець відрізку": "Clip end",
        "00:00:10 або 10": "00:00:10 or 10",
        "FPS для GIF": "GIF FPS",
        "Ширина GIF": "GIF width",
        "Кадрів в секунду": "Frames per second",
        "Обрати папку": "Choose folder",
        "Робоча папка": "Working folder",
        "CMD-команда": "CMD command",
        "Вставити шлях вхідного файлу": "Insert input file path",
        "Очистити команду": "Clear command",
        "Очистити вивід": "Clear output",
        "Вивід CMD": "CMD output",
        "ЗАПУСТИТИ ОБРОБКУ": "START PROCESSING",
        "Наприклад: {placeholder}": "Example: {placeholder}",
        "Оберіть медіафайл": "Choose media file",
        "Медіафайли": "Media files",
        "Усі файли": "All files",
        "Файл завантажено": "File loaded",
        "Додати відеофайли": "Add video files",
        "Відеофайли": "Video files",
        "Оберіть аудіофайл": "Choose audio file",
        "Аудіофайли": "Audio files",
        "Оберіть папку для скріншотів": "Choose screenshots folder",
        "Оберіть робочу папку для CMD": "Choose CMD working folder",
        "Помилка": "Error",
        "Спочатку оберіть вхідний файл.": "Choose an input file first.",
        "Помилка налаштувань": "Settings error",
        "Введіть CMD-команду.": "Enter a CMD command.",
        "Робоча папка для CMD-команди не існує.": "The working folder for the CMD command does not exist.",
        "Обробку завершено.\n\nРезультат:\n{output}": "Processing completed.\n\nResult:\n{output}",
        "Код завершення: {code}{log}\n\n{error}": "Exit code: {code}{log}\n\n{error}",
        "\n\nЛог: {log_path}": "\n\nLog: {log_path}",
        "FFmpeg завершився з помилкою": "FFmpeg finished with an error",
        "Помилка FFmpeg": "FFmpeg error",
        "CMD-команду виконано успішно.": "CMD command completed successfully.",
        "CMD-команда виконується...": "CMD command is running...",
        "CMD-команду виконано": "CMD command completed",
        "CMD-команда завершилась з помилкою": "CMD command finished with an error",
        "Помилка CMD": "CMD error",
        "Обробка триває...": "Processing...",
        "Завершення...": "Finishing...",
        "Обробка: {progress:.0f}%": "Processing: {progress:.0f}%",
        "Список порожній. Додайте файли для безшовного склеювання.\n": "The list is empty. Add files for seamless merging.\n",
        "Мова": "Language",
        "Зберегти": "Save",
        "Закрити": "Close",
        "Зміна мови": "Language change",
        "Мову змінено. Інтерфейс оновлено.": "Language changed. The interface has been updated.",
    }
}


class PyFFmpegStudioApp(BaseTk):
    def __init__(self) -> None:
        super().__init__()
        self.title('PyFFmpeg-Studio')
        self.geometry("1040x720")
        self.minsize(920, 640)
        self.configure(background="#f3f6fb")
        self.settings = self._load_settings()
        self.language_code = str(self.settings.get("language", "uk"))
        if self.language_code not in LANGUAGE_NAMES:
            self.language_code = "uk"
        self.language_name = tk.StringVar(value=LANGUAGE_NAMES[self.language_code])
        self._app_icon: tk.PhotoImage | None = None
        self._apply_window_icon()

        self.input_path = tk.StringVar()
        self.file_name = tk.StringVar(value=self._tr("Файл не обрано"))
        self.file_format = tk.StringVar(value="-")
        self.file_duration = tk.StringVar(value="-")
        self.drop_hint = tk.StringVar(value=self._drop_default_text())
        self.status_text = tk.StringVar(value=self._tr("Готово"))
        self.progress_value = tk.DoubleVar(value=0)
        self.media_duration: float | None = None
        self.processing = False
        self.concat_files: list[Path] = []
        self.manual_workdir = tk.StringVar(value=str(Path.cwd()))
        self._previous_widget_states: dict[tk.Widget, str] = {}

        self._configure_style()
        self._build_layout()

    def _load_settings(self) -> dict[str, object]:
        if not CONFIG_PATH.exists():
            return {}
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_settings(self) -> None:
        CONFIG_PATH.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf-8")

    def _tr(self, text: str, **kwargs) -> str:
        translated = TRANSLATIONS.get(self.language_code, {}).get(text, text)
        if kwargs:
            return translated.format(**kwargs)
        return translated

    def _drop_default_text(self) -> str:
        if DND_FILES:
            return self._tr("Перетягніть медіафайл сюди або натисніть «Обрати файл»")
        return self._tr("Drag&Drop потребує tkinterdnd2. Поки скористайтесь кнопкою «Обрати файл»")

    def _apply_window_icon(self) -> None:
        if not ICON_PATH.exists():
            return
        try:
            self._app_icon = tk.PhotoImage(file=str(ICON_PATH))
            self.iconphoto(True, self._app_icon)
        except tk.TclError:
            self._app_icon = None

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#f3f6fb")
        style.configure("Panel.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("InfoCard.TFrame", background="#f8fafc", relief="solid", borderwidth=1)
        style.configure("TLabel", background="#f3f6fb", foreground="#1f2933", font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background="#ffffff", foreground="#1f2933", font=("Segoe UI", 10))
        style.configure("InfoCard.TLabel", background="#f8fafc", foreground="#334155", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#ffffff", foreground="#0f172a", font=("Segoe UI", 18, "bold"))
        style.configure("Muted.TLabel", background="#ffffff", foreground="#64748b", font=("Segoe UI", 9))
        style.configure("Title.TLabel", background="#ffffff", foreground="#111827", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 6))
        style.configure("Accent.TButton", background="#2563eb", foreground="#ffffff", font=("Segoe UI", 10, "bold"), padding=(12, 7))
        style.map("Accent.TButton", background=[("active", "#1d4ed8"), ("disabled", "#93c5fd")])
        style.configure("Run.TButton", background="#16a34a", foreground="#ffffff", font=("Segoe UI", 11, "bold"), padding=(14, 8))
        style.map("Run.TButton", background=[("active", "#15803d"), ("disabled", "#86efac")])
        style.configure("TNotebook", background="#f3f6fb", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(14, 8), font=("Segoe UI", 10))
        style.configure("Horizontal.TProgressbar", thickness=16)

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_top_panel()
        self._build_tabs()
        self._build_bottom_panel()

    def _build_top_panel(self) -> None:
        panel = ttk.Frame(self, style="Panel.TFrame", padding=14)
        panel.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        panel.columnconfigure(1, weight=1)

        header = ttk.Frame(panel, style="Panel.TFrame")
        header.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="PyFFmpeg-Studio", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text=self._tr("Конвертація, обрізання, GIF, розкадровка та ручні CMD-команди в одному вікні"),
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Button(header, text=self._tr("Налаштування"), command=self.open_settings_dialog).grid(row=0, column=1, rowspan=2, sticky="e")

        self.drop_zone = tk.Label(
            panel,
            textvariable=self.drop_hint,
            bg="#eff6ff",
            fg="#1d4ed8" if DND_FILES else "#64748b",
            activebackground="#dbeafe",
            activeforeground="#1d4ed8",
            font=("Segoe UI", 11, "bold"),
            height=3,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#93c5fd" if DND_FILES else "#cbd5e1",
            highlightcolor="#2563eb",
            cursor="hand2",
        )
        self.drop_zone.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        self.drop_zone.bind("<Button-1>", lambda _event: self.choose_input_file())
        self._setup_drag_and_drop()

        ttk.Label(panel, text=self._tr("Вхідний файл"), style="Title.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 10))
        self.input_entry = ttk.Entry(panel, textvariable=self.input_path, state="readonly")
        self.input_entry.grid(row=2, column=1, sticky="ew", padx=(0, 10))
        ttk.Button(panel, text=self._tr("Обрати файл"), style="Accent.TButton", command=self.choose_input_file).grid(row=2, column=2, sticky="e")

        info_frame = ttk.Frame(panel, style="Panel.TFrame")
        info_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        info_frame.columnconfigure((0, 1, 2), weight=1)
        self._add_info_card(info_frame, 0, self._tr("Назва"), self.file_name)
        self._add_info_card(info_frame, 1, self._tr("Формат"), self.file_format)
        self._add_info_card(info_frame, 2, self._tr("Тривалість"), self.file_duration)

    def _add_info_card(self, parent: ttk.Frame, column: int, title: str, variable: tk.StringVar) -> None:
        card = ttk.Frame(parent, style="InfoCard.TFrame", padding=(10, 8))
        card.grid(row=0, column=column, sticky="ew", padx=(0, 8) if column < 2 else 0)
        card.columnconfigure(0, weight=1)
        ttk.Label(card, text=title, style="InfoCard.TLabel", font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(card, textvariable=variable, style="InfoCard.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 0))

    def open_settings_dialog(self) -> None:
        if self.processing:
            return

        dialog = tk.Toplevel(self)
        dialog.title(self._tr("Налаштування"))
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.configure(background="#ffffff")

        body = ttk.Frame(dialog, style="Panel.TFrame", padding=16)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)

        language_var = tk.StringVar(value=LANGUAGE_NAMES[self.language_code])
        ttk.Label(body, text=self._tr("Мова"), style="Panel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 12))
        language_combo = ttk.Combobox(
            body,
            textvariable=language_var,
            values=list(LANGUAGE_NAMES.values()),
            state="readonly",
            width=24,
        )
        language_combo.grid(row=0, column=1, sticky="ew", pady=(0, 12))

        button_row = ttk.Frame(body, style="Panel.TFrame")
        button_row.grid(row=1, column=0, columnspan=2, sticky="e")
        ttk.Button(button_row, text=self._tr("Закрити"), command=dialog.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(
            button_row,
            text=self._tr("Зберегти"),
            style="Accent.TButton",
            command=lambda: self._save_settings_dialog(dialog, language_var.get()),
        ).pack(side="right")

        language_combo.focus_set()
        dialog.grab_set()

    def _save_settings_dialog(self, dialog: tk.Toplevel, language_name: str) -> None:
        language_code = next((code for code, name in LANGUAGE_NAMES.items() if name == language_name), "uk")
        if language_code != self.language_code:
            state = self._snapshot_ui_state()
            self.language_code = language_code
            self.language_name.set(LANGUAGE_NAMES[language_code])
            self.settings["language"] = language_code
            self._save_settings()
            dialog.destroy()
            self._rebuild_layout(state)
            messagebox.showinfo(self._tr("Зміна мови"), self._tr("Мову змінено. Інтерфейс оновлено."))
            return

        self.settings["language"] = language_code
        self._save_settings()
        dialog.destroy()

    def _setup_drag_and_drop(self) -> None:
        if not DND_FILES or not hasattr(self.drop_zone, "drop_target_register"):
            return

        self.drop_zone.drop_target_register(DND_FILES)
        self.drop_zone.dnd_bind("<<Drop>>", self._handle_input_drop)
        self.drop_zone.dnd_bind("<<DragEnter>>", self._handle_drag_enter)
        self.drop_zone.dnd_bind("<<DragLeave>>", self._handle_drag_leave)

    def _handle_drag_enter(self, event) -> str:
        if self.processing:
            return "break"
        self.drop_zone.configure(bg="#dbeafe", highlightbackground="#2563eb")
        self.drop_hint.set(self._tr("Відпустіть файл, щоб завантажити його"))
        return getattr(event, "action", "copy")

    def _handle_drag_leave(self, event) -> str:
        self._restore_drop_zone()
        return getattr(event, "action", "copy")

    def _handle_input_drop(self, event) -> str:
        if self.processing:
            return "break"

        paths = self.tk.splitlist(event.data)
        if not paths:
            return "break"

        selected_path = Path(paths[0])
        if not selected_path.is_file():
            messagebox.showerror(self._tr("Помилка"), self._tr("Перетягніть саме файл, не папку."))
            self._restore_drop_zone()
            return "break"

        self._load_input_file(selected_path)
        self._restore_drop_zone()
        return getattr(event, "action", "copy")

    def _restore_drop_zone(self) -> None:
        self.drop_zone.configure(
            bg="#eff6ff",
            fg="#1d4ed8" if DND_FILES else "#64748b",
            highlightbackground="#93c5fd" if DND_FILES else "#cbd5e1",
        )
        if self.input_path.get():
            self.drop_hint.set(self._tr("Активний файл: {name}", name=Path(self.input_path.get()).name))
        else:
            self.drop_hint.set(self._drop_default_text())

    def _build_tabs(self) -> None:
        container = ttk.Frame(self, padding=(12, 0, 12, 0))
        container.grid(row=1, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        self.main_tabs = ttk.Notebook(container)
        self.main_tabs.grid(row=0, column=0, sticky="nsew")

        self.tab_video = ttk.Frame(self.main_tabs, padding=12)
        self.tab_audio = ttk.Frame(self.main_tabs, padding=12)
        self.tab_photo = ttk.Frame(self.main_tabs, padding=12)
        self.tab_manual = ttk.Frame(self.main_tabs, padding=12)
        self.main_tabs.add(self.tab_video, text=self._tr("Відео"))
        self.main_tabs.add(self.tab_audio, text=self._tr("Аудіо"))
        self.main_tabs.add(self.tab_photo, text=self._tr("Фото"))
        self.main_tabs.add(self.tab_manual, text=self._tr("Ручна команда"))

        self._build_video_tabs()
        self._build_audio_tabs()
        self._build_photo_tabs()
        self._build_manual_tab()

    def _build_video_tabs(self) -> None:
        self.tab_video.columnconfigure(0, weight=1)
        self.tab_video.rowconfigure(0, weight=1)
        self.video_subtabs = ttk.Notebook(self.tab_video)
        self.video_subtabs.grid(row=0, column=0, sticky="nsew")

        convert = ttk.Frame(self.video_subtabs, padding=18)
        trim = ttk.Frame(self.video_subtabs, padding=18)
        audio = ttk.Frame(self.video_subtabs, padding=18)
        self.video_subtabs.add(convert, text=self._tr("Конвертація та стиснення"))
        self.video_subtabs.add(trim, text=self._tr("Обрізання та Склеювання"))
        self.video_subtabs.add(audio, text=self._tr("Аудіодоріжка відео"))

        self.video_format = tk.StringVar(value="MP4")
        self.video_codec = tk.StringVar(value="libx264")
        self.video_crf = tk.DoubleVar(value=23)
        self.video_crf_label = tk.StringVar(value="23")
        self.video_resolution = tk.StringVar(value=self._tr("Оригінал"))

        self._add_combo(convert, 0, self._tr("Формат"), self.video_format, ["MP4", "MKV", "MOV", "WebM"])
        self._add_combo(convert, 1, self._tr("Відеокодек"), self.video_codec, ["libx264", "libx265", "AV1"])
        self._add_scale(
            convert,
            2,
            self._tr("Якість / CRF"),
            self.video_crf,
            0,
            51,
            self.video_crf_label,
            lambda value: str(int(round(float(value)))),
        )
        self._add_combo(
            convert,
            3,
            self._tr("Роздільна здатність"),
            self.video_resolution,
            [self._tr("Оригінал"), "1920x1080 (1080p)", "1280x720 (720p)", "640x480 (480p)"],
        )

        self.trim_start = tk.StringVar()
        self.trim_end = tk.StringVar()
        self._add_entry(trim, 0, self._tr("Початок обрізання"), self.trim_start, self._tr("00:00:05 або 5"))
        self._add_entry(trim, 1, self._tr("Кінець обрізання"), self.trim_end, self._tr("00:00:20 або 20"))

        queue_buttons = ttk.Frame(trim)
        queue_buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(14, 8))
        ttk.Button(queue_buttons, text=self._tr("Додати файли до списку"), command=self.add_concat_files).pack(side="left")
        ttk.Button(queue_buttons, text=self._tr("Очистити список"), command=self.clear_concat_files).pack(side="left", padx=(8, 0))

        self.concat_text = tk.Text(
            trim,
            height=8,
            wrap="none",
            state="disabled",
            font=("Consolas", 9),
            bg="#f8fafc",
            fg="#0f172a",
            relief="flat",
            padx=10,
            pady=8,
        )
        self.concat_text.grid(row=3, column=0, columnspan=2, sticky="nsew")
        trim.columnconfigure(1, weight=1)
        trim.rowconfigure(3, weight=1)

        self.remove_audio = tk.BooleanVar(value=False)
        self.replacement_audio = tk.StringVar(value="")
        ttk.Checkbutton(
            audio,
            text=self._tr("Вирізати звук повністю"),
            variable=self.remove_audio,
            command=self._sync_audio_controls,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Button(audio, text=self._tr("Замінити аудіо"), command=self.choose_replacement_audio).grid(row=1, column=0, sticky="w")
        self.replace_audio_label = ttk.Label(audio, textvariable=self.replacement_audio)
        self.replace_audio_label.grid(row=1, column=1, sticky="ew", padx=(10, 0))
        ttk.Button(audio, text=self._tr("Скинути аудіо"), command=self.clear_replacement_audio).grid(row=2, column=0, sticky="w", pady=(10, 0))
        audio.columnconfigure(1, weight=1)

    def _build_audio_tabs(self) -> None:
        self.tab_audio.columnconfigure(0, weight=1)
        self.tab_audio.rowconfigure(0, weight=1)
        self.audio_subtabs = ttk.Notebook(self.tab_audio)
        self.audio_subtabs.grid(row=0, column=0, sticky="nsew")

        convert = ttk.Frame(self.audio_subtabs, padding=18)
        process = ttk.Frame(self.audio_subtabs, padding=18)
        self.audio_subtabs.add(convert, text=self._tr("Зміна формату"))
        self.audio_subtabs.add(process, text=self._tr("Обробка звуку"))

        self.audio_format = tk.StringVar(value="MP3")
        self.audio_bitrate = tk.StringVar(value="192 kbps")
        self._add_combo(convert, 0, self._tr("Формат"), self.audio_format, ["MP3", "WAV", "FLAC", "AAC", "OGG"])
        self._add_combo(convert, 1, self._tr("Бітрейт для MP3"), self.audio_bitrate, ["128 kbps", "192 kbps", "320 kbps"])

        self.audio_start = tk.StringVar()
        self.audio_end = tk.StringVar()
        self.audio_volume = tk.DoubleVar(value=100)
        self.audio_volume_label = tk.StringVar(value="100%")
        self.fade_in = tk.BooleanVar(value=False)
        self.fade_out = tk.BooleanVar(value=False)

        self._add_entry(process, 0, self._tr("Старт"), self.audio_start, self._tr("00:00:05 або 5"))
        self._add_entry(process, 1, self._tr("Фініш"), self.audio_end, self._tr("00:00:20 або 20"))
        self._add_scale(
            process,
            2,
            self._tr("Гучність"),
            self.audio_volume,
            0,
            200,
            self.audio_volume_label,
            lambda value: f"{int(round(float(value)))}%",
        )
        ttk.Checkbutton(process, text=self._tr("Ефект плавного початку (Fade-in)"), variable=self.fade_in).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )
        ttk.Checkbutton(process, text=self._tr("Плавного кінця (Fade-out)"), variable=self.fade_out).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

    def _build_photo_tabs(self) -> None:
        self.tab_photo.columnconfigure(0, weight=1)
        self.tab_photo.rowconfigure(0, weight=1)
        self.photo_subtabs = ttk.Notebook(self.tab_photo)
        self.photo_subtabs.grid(row=0, column=0, sticky="nsew")

        convert = ttk.Frame(self.photo_subtabs, padding=18)
        gif = ttk.Frame(self.photo_subtabs, padding=18)
        frames = ttk.Frame(self.photo_subtabs, padding=18)
        self.photo_subtabs.add(convert, text=self._tr("Конвертація зображень"))
        self.photo_subtabs.add(gif, text=self._tr("Створення GIF"))
        self.photo_subtabs.add(frames, text=self._tr("Розкадровка"))

        self.photo_format = tk.StringVar(value="PNG")
        self._add_combo(convert, 0, self._tr("Формат"), self.photo_format, ["PNG", "JPEG", "WebP", "BMP"])
        ttk.Label(
            convert,
            text=self._tr("FFmpeg конвертує поодинокі фотографії так само, як і відео."),
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))

        self.gif_start = tk.StringVar()
        self.gif_end = tk.StringVar()
        self.gif_fps = tk.StringVar(value="15")
        self.gif_width = tk.DoubleVar(value=480)
        self.gif_width_label = tk.StringVar(value="480 px")
        self._add_entry(gif, 0, self._tr("Початок відрізку"), self.gif_start, self._tr("00:00:05 або 5"))
        self._add_entry(gif, 1, self._tr("Кінець відрізку"), self.gif_end, self._tr("00:00:10 або 10"))
        self._add_combo(gif, 2, self._tr("FPS для GIF"), self.gif_fps, ["10", "15", "24", "30"])
        self._add_scale(
            gif,
            3,
            self._tr("Ширина GIF"),
            self.gif_width,
            160,
            1080,
            self.gif_width_label,
            lambda value: f"{int(round(float(value)))} px",
        )

        self.frames_fps = tk.StringVar(value="1")
        self.frames_dir = tk.StringVar(value="")
        self._add_entry(frames, 0, self._tr("Кадрів в секунду"), self.frames_fps, "1")
        ttk.Button(frames, text=self._tr("Обрати папку"), command=self.choose_frames_directory).grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Label(frames, textvariable=self.frames_dir).grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(8, 0))
        frames.columnconfigure(1, weight=1)

    def _build_manual_tab(self) -> None:
        self.tab_manual.columnconfigure(0, weight=1)
        self.tab_manual.rowconfigure(2, weight=1)
        self.tab_manual.rowconfigure(5, weight=1)

        workdir_frame = ttk.Frame(self.tab_manual)
        workdir_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        workdir_frame.columnconfigure(1, weight=1)
        ttk.Label(workdir_frame, text=self._tr("Робоча папка")).grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Entry(workdir_frame, textvariable=self.manual_workdir).grid(row=0, column=1, sticky="ew", padx=(0, 10))
        ttk.Button(workdir_frame, text=self._tr("Обрати папку"), command=self.choose_manual_workdir).grid(row=0, column=2, sticky="e")

        ttk.Label(self.tab_manual, text=self._tr("CMD-команда")).grid(row=1, column=0, sticky="w", pady=(0, 6))
        self.manual_command_text = tk.Text(
            self.tab_manual,
            height=7,
            wrap="word",
            font=("Consolas", 10),
            bg="#111827",
            fg="#e5e7eb",
            insertbackground="#ffffff",
            relief="flat",
            padx=10,
            pady=8,
        )
        self.manual_command_text.grid(row=2, column=0, sticky="nsew")
        self.manual_command_text.insert("1.0", 'ffmpeg -i "input.mp4" "output.mp4"')

        command_buttons = ttk.Frame(self.tab_manual)
        command_buttons.grid(row=3, column=0, sticky="ew", pady=10)
        ttk.Button(command_buttons, text=self._tr("Вставити шлях вхідного файлу"), command=self.insert_input_path_into_command).pack(side="left")
        ttk.Button(command_buttons, text=self._tr("Очистити команду"), command=self.clear_manual_command).pack(side="left", padx=(8, 0))
        ttk.Button(command_buttons, text=self._tr("Очистити вивід"), command=self.clear_manual_output).pack(side="left", padx=(8, 0))

        ttk.Label(self.tab_manual, text=self._tr("Вивід CMD")).grid(row=4, column=0, sticky="w", pady=(4, 6))
        self.manual_output_text = tk.Text(
            self.tab_manual,
            height=9,
            wrap="word",
            state="disabled",
            font=("Consolas", 9),
            bg="#0f172a",
            fg="#d1d5db",
            relief="flat",
            padx=10,
            pady=8,
        )
        self.manual_output_text.grid(row=5, column=0, sticky="nsew")

    def _build_bottom_panel(self) -> None:
        panel = ttk.Frame(self, style="Panel.TFrame", padding=12)
        panel.grid(row=2, column=0, sticky="ew", padx=12, pady=(8, 12))
        panel.columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(panel, variable=self.progress_value, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.run_button = ttk.Button(panel, text=self._tr("ЗАПУСТИТИ ОБРОБКУ"), style="Run.TButton", command=self.run_processing)
        self.run_button.grid(row=0, column=1, sticky="e")
        ttk.Label(panel, textvariable=self.status_text, style="Panel.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def _add_combo(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        values: list[str],
    ) -> ttk.Combobox:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=7, padx=(0, 10))
        combo = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", width=28)
        combo.grid(row=row, column=1, sticky="ew", pady=7)
        parent.columnconfigure(1, weight=1)
        return combo

    def _add_entry(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        placeholder: str,
    ) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=7, padx=(0, 10))
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", pady=7)
        entry.insert(0, "")
        entry.configure()
        ttk.Label(parent, text=self._tr("Наприклад: {placeholder}", placeholder=placeholder)).grid(row=row, column=2, sticky="w", padx=(10, 0))
        parent.columnconfigure(1, weight=1)
        return entry

    def _add_scale(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.DoubleVar,
        start: int,
        end: int,
        value_label: tk.StringVar,
        formatter,
    ) -> ttk.Scale:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=7, padx=(0, 10))
        scale = ttk.Scale(parent, from_=start, to=end, variable=variable)
        scale.grid(row=row, column=1, sticky="ew", pady=7)
        ttk.Label(parent, textvariable=value_label, width=10).grid(row=row, column=2, sticky="w", padx=(10, 0))

        def update_label(value: str) -> None:
            value_label.set(formatter(value))

        scale.configure(command=update_label)
        parent.columnconfigure(1, weight=1)
        return scale

    def choose_input_file(self) -> None:
        path = filedialog.askopenfilename(
            title=self._tr("Оберіть медіафайл"),
            filetypes=[
                (self._tr("Медіафайли"), _file_pattern(VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | IMAGE_EXTENSIONS)),
                (self._tr("Усі файли"), "*.*"),
            ],
        )
        if not path:
            return

        self._load_input_file(Path(path))

    def _load_input_file(self, path: Path) -> None:
        self.input_path.set(str(path))
        media_info = probe_media_info(path)
        self.media_duration = media_info.duration
        self.file_name.set(media_info.name)
        self.file_format.set(media_info.format_name)
        self.file_duration.set(format_duration(media_info.duration))
        self.drop_hint.set(self._tr("Активний файл: {name}", name=media_info.name))
        self.status_text.set(self._tr("Файл завантажено"))

    def add_concat_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title=self._tr("Додати відеофайли"),
            filetypes=[(self._tr("Відеофайли"), _file_pattern(VIDEO_EXTENSIONS)), (self._tr("Усі файли"), "*.*")],
        )
        if not paths:
            return
        self.concat_files.extend(Path(path) for path in paths)
        self._refresh_concat_text()

    def clear_concat_files(self) -> None:
        self.concat_files.clear()
        self._refresh_concat_text()

    def choose_replacement_audio(self) -> None:
        if self.remove_audio.get():
            return
        path = filedialog.askopenfilename(
            title=self._tr("Оберіть аудіофайл"),
            filetypes=[(self._tr("Аудіофайли"), _file_pattern(AUDIO_EXTENSIONS)), (self._tr("Усі файли"), "*.*")],
        )
        if path:
            self.replacement_audio.set(path)

    def clear_replacement_audio(self) -> None:
        self.replacement_audio.set("")

    def choose_frames_directory(self) -> None:
        path = filedialog.askdirectory(title=self._tr("Оберіть папку для скріншотів"))
        if path:
            self.frames_dir.set(path)

    def choose_manual_workdir(self) -> None:
        path = filedialog.askdirectory(title=self._tr("Оберіть робочу папку для CMD"))
        if path:
            self.manual_workdir.set(path)

    def insert_input_path_into_command(self) -> None:
        path = self.input_path.get().strip()
        if not path:
            messagebox.showerror(self._tr("Помилка"), self._tr("Спочатку оберіть вхідний файл."))
            return
        self.manual_command_text.insert("insert", f'"{path}"')
        self.manual_command_text.focus_set()

    def clear_manual_command(self) -> None:
        self.manual_command_text.delete("1.0", "end")

    def clear_manual_output(self) -> None:
        self.manual_output_text.configure(state="normal")
        self.manual_output_text.delete("1.0", "end")
        self.manual_output_text.configure(state="disabled")

    def run_processing(self) -> None:
        if self.processing:
            return
        if self._active_main_tab_key() == "manual":
            self.run_manual_command()
            return
        if not self.input_path.get():
            messagebox.showerror(self._tr("Помилка"), self._tr("Спочатку оберіть вхідний файл."))
            return

        try:
            job = build_command_job(
                input_path=self.input_path.get(),
                main_tab=self._active_backend_main_tab(),
                sub_tab=self._active_backend_subtab(),
                settings=self._collect_settings(),
                duration=self.media_duration,
            )
        except CommandBuildError as exc:
            messagebox.showerror(self._tr("Помилка налаштувань"), str(exc))
            return

        self._set_processing_state(True, job)
        worker = threading.Thread(target=self._run_worker, args=(job,), daemon=True)
        worker.start()

    def run_manual_command(self) -> None:
        command_text = self.manual_command_text.get("1.0", "end").strip()
        if not command_text:
            messagebox.showerror(self._tr("Помилка"), self._tr("Введіть CMD-команду."))
            return

        working_dir = self.manual_workdir.get().strip() or str(Path.cwd())
        if not Path(working_dir).is_dir():
            messagebox.showerror(self._tr("Помилка"), self._tr("Робоча папка для CMD-команди не існує."))
            return

        self.clear_manual_output()
        self._append_manual_output(f"> {command_text}\n\n")
        self._set_processing_state(True, None)
        worker = threading.Thread(target=self._run_cmd_worker, args=(command_text, working_dir), daemon=True)
        worker.start()

    def _run_worker(self, job: CommandJob) -> None:
        result = run_ffmpeg(
            job,
            progress_callback=lambda value: self.after(0, self._set_progress, value),
            status_callback=lambda text: self.after(0, self.status_text.set, self._tr(text)),
        )
        self.after(0, self._finish_processing, result)

    def _run_cmd_worker(self, command_text: str, working_dir: str) -> None:
        try:
            result = run_cmd_command(
                command_text,
                working_dir=working_dir,
                output_callback=lambda text: self.after(0, self._append_manual_output, text),
                status_callback=lambda text: self.after(0, self.status_text.set, self._tr(text)),
            )
        except CommandBuildError as exc:
            result = FfmpegResult(False, -1, ["cmd.exe"], None, None, str(exc))
        self.after(0, self._finish_manual_command, result)

    def _finish_processing(self, result: FfmpegResult) -> None:
        self._set_processing_state(False, None)
        if result.success:
            output = str(result.output_path) if result.output_path else self._tr("Готово")
            self.status_text.set(f"{self._tr('Готово')}: {output}")
            messagebox.showinfo(self._tr("Готово"), self._tr("Обробку завершено.\n\nРезультат:\n{output}", output=output))
            return

        log_info = self._tr("\n\nЛог: {log_path}", log_path=result.log_path) if result.log_path else ""
        self.status_text.set(self._tr("FFmpeg завершився з помилкою"))
        messagebox.showerror(
            self._tr("Помилка FFmpeg"),
            self._tr("Код завершення: {code}{log}\n\n{error}", code=result.returncode, log=log_info, error=result.error_text[-1200:]),
        )

    def _finish_manual_command(self, result: FfmpegResult) -> None:
        self._set_processing_state(False, None)
        if result.success:
            self.progress_value.set(100)
            self.status_text.set(self._tr("CMD-команду виконано успішно."))
            messagebox.showinfo(self._tr("Готово"), self._tr("CMD-команду виконано успішно."))
            return

        log_info = self._tr("\n\nЛог: {log_path}", log_path=result.log_path) if result.log_path else ""
        self.status_text.set(self._tr("CMD-команда завершилась з помилкою"))
        messagebox.showerror(
            self._tr("Помилка CMD"),
            self._tr("Код завершення: {code}{log}\n\n{error}", code=result.returncode, log=log_info, error=result.error_text[-1200:]),
        )

    def _set_processing_state(self, active: bool, job: CommandJob | None) -> None:
        self.processing = active
        self.run_button.configure(state="disabled" if active else "normal")
        self._set_notebook_state(self.main_tabs, "disabled" if active else "normal")
        self._set_notebook_state(self.video_subtabs, "disabled" if active else "normal")
        self._set_notebook_state(self.audio_subtabs, "disabled" if active else "normal")
        self._set_notebook_state(self.photo_subtabs, "disabled" if active else "normal")
        self._set_interactive_widgets_state(active)

        if active:
            self.progress_value.set(0)
            if not job or not job.progress_duration:
                self.progress_bar.configure(mode="indeterminate")
                self.progress_bar.start(12)
            else:
                self.progress_bar.configure(mode="determinate")
            self.status_text.set(self._tr("Обробка триває..."))
        else:
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")

    def _set_progress(self, value: float) -> None:
        self.progress_value.set(value)
        self.status_text.set(self._tr("Обробка: {progress:.0f}%", progress=value))

    def _append_manual_output(self, text: str) -> None:
        self.manual_output_text.configure(state="normal")
        self.manual_output_text.insert("end", text)
        self.manual_output_text.see("end")
        self.manual_output_text.configure(state="disabled")

    def _snapshot_ui_state(self) -> dict[str, object]:
        state: dict[str, object] = {
            "input_path": self.input_path.get(),
            "media_duration": self.media_duration,
            "concat_files": [str(path) for path in self.concat_files],
            "manual_workdir": self.manual_workdir.get(),
        }

        for attr in (
            "video_format",
            "video_codec",
            "video_crf",
            "video_resolution",
            "trim_start",
            "trim_end",
            "remove_audio",
            "replacement_audio",
            "audio_format",
            "audio_bitrate",
            "audio_start",
            "audio_end",
            "audio_volume",
            "fade_in",
            "fade_out",
            "photo_format",
            "gif_start",
            "gif_end",
            "gif_fps",
            "gif_width",
            "frames_fps",
            "frames_dir",
        ):
            if hasattr(self, attr):
                state[attr] = getattr(self, attr).get()

        if hasattr(self, "main_tabs"):
            state["main_tab"] = self.main_tabs.index(self.main_tabs.select())
        if hasattr(self, "video_subtabs"):
            state["video_subtab"] = self.video_subtabs.index(self.video_subtabs.select())
        if hasattr(self, "audio_subtabs"):
            state["audio_subtab"] = self.audio_subtabs.index(self.audio_subtabs.select())
        if hasattr(self, "photo_subtabs"):
            state["photo_subtab"] = self.photo_subtabs.index(self.photo_subtabs.select())
        if hasattr(self, "manual_command_text"):
            state["manual_command"] = self.manual_command_text.get("1.0", "end-1c")
        if hasattr(self, "manual_output_text"):
            state["manual_output"] = self.manual_output_text.get("1.0", "end-1c")

        return state

    def _rebuild_layout(self, state: dict[str, object]) -> None:
        for child in self.winfo_children():
            child.destroy()
        self._previous_widget_states.clear()
        self.drop_hint.set(self._drop_default_text())
        self.status_text.set(self._tr("Готово"))
        self.file_name.set(self._tr("Файл не обрано"))
        self.file_format.set("-")
        self.file_duration.set("-")
        self._build_layout()
        self._restore_ui_state(state)

    def _restore_ui_state(self, state: dict[str, object]) -> None:
        self.manual_workdir.set(str(state.get("manual_workdir") or Path.cwd()))

        for attr in (
            "video_format",
            "video_codec",
            "video_crf",
            "video_resolution",
            "trim_start",
            "trim_end",
            "remove_audio",
            "replacement_audio",
            "audio_format",
            "audio_bitrate",
            "audio_start",
            "audio_end",
            "audio_volume",
            "fade_in",
            "fade_out",
            "photo_format",
            "gif_start",
            "gif_end",
            "gif_fps",
            "gif_width",
            "frames_fps",
            "frames_dir",
        ):
            if hasattr(self, attr) and attr in state:
                value = state[attr]
                if attr == "video_resolution":
                    value = self._localized_resolution_value(str(value))
                getattr(self, attr).set(value)

        self.video_crf_label.set(str(int(round(float(self.video_crf.get())))))
        self.audio_volume_label.set(f"{int(round(float(self.audio_volume.get())))}%")
        self.gif_width_label.set(f"{int(round(float(self.gif_width.get())))} px")

        self.concat_files = [Path(path) for path in state.get("concat_files", [])]
        self._refresh_concat_text()

        self.manual_command_text.delete("1.0", "end")
        self.manual_command_text.insert("1.0", str(state.get("manual_command") or ""))
        self.manual_output_text.configure(state="normal")
        self.manual_output_text.delete("1.0", "end")
        self.manual_output_text.insert("1.0", str(state.get("manual_output") or ""))
        self.manual_output_text.configure(state="disabled")

        self._select_notebook_index(self.main_tabs, int(state.get("main_tab", 0)))
        self._select_notebook_index(self.video_subtabs, int(state.get("video_subtab", 0)))
        self._select_notebook_index(self.audio_subtabs, int(state.get("audio_subtab", 0)))
        self._select_notebook_index(self.photo_subtabs, int(state.get("photo_subtab", 0)))

        input_path = str(state.get("input_path") or "")
        if input_path:
            self._load_input_file(Path(input_path))
        else:
            self._restore_drop_zone()

    def _select_notebook_index(self, notebook: ttk.Notebook, index: int) -> None:
        tabs = notebook.tabs()
        if not tabs:
            return
        index = max(0, min(index, len(tabs) - 1))
        notebook.select(index)

    def _localized_resolution_value(self, value: str) -> str:
        if value in {"Оригінал", "Original"}:
            return self._tr("Оригінал")
        return value

    def _collect_settings(self) -> dict[str, object]:
        main_tab = self._active_main_tab_key()
        if main_tab == "video":
            return self._collect_video_settings()
        if main_tab == "audio":
            return self._collect_audio_settings()
        return self._collect_photo_settings()

    def _collect_video_settings(self) -> dict[str, object]:
        sub_tab = self.video_subtabs.index(self.video_subtabs.select())
        if sub_tab == 0:
            resolution = self.video_resolution.get()
            if resolution in {"Оригінал", "Original"}:
                resolution = "Оригінал"
            return {
                "format": self.video_format.get(),
                "codec": self.video_codec.get(),
                "crf": int(round(self.video_crf.get())),
                "resolution": resolution,
            }
        if sub_tab == 1:
            return {
                "trim_start": self.trim_start.get(),
                "trim_end": self.trim_end.get(),
                "concat_files": [str(path) for path in self.concat_files],
            }
        return {
            "remove_audio": self.remove_audio.get(),
            "replacement_audio": self.replacement_audio.get(),
        }

    def _collect_audio_settings(self) -> dict[str, object]:
        sub_tab = self.audio_subtabs.index(self.audio_subtabs.select())
        if sub_tab == 0:
            return {
                "format": self.audio_format.get(),
                "bitrate": self.audio_bitrate.get(),
            }
        return {
            "audio_start": self.audio_start.get(),
            "audio_end": self.audio_end.get(),
            "volume": int(round(self.audio_volume.get())),
            "fade_in": self.fade_in.get(),
            "fade_out": self.fade_out.get(),
        }

    def _collect_photo_settings(self) -> dict[str, object]:
        sub_tab = self.photo_subtabs.index(self.photo_subtabs.select())
        if sub_tab == 0:
            return {"format": self.photo_format.get()}
        if sub_tab == 1:
            return {
                "gif_start": self.gif_start.get(),
                "gif_end": self.gif_end.get(),
                "fps": self.gif_fps.get(),
                "width": int(round(self.gif_width.get())),
            }
        return {
            "frames_fps": self.frames_fps.get(),
            "frames_dir": self.frames_dir.get(),
        }

    def _active_main_tab_key(self) -> str:
        keys = ["video", "audio", "photo", "manual"]
        return keys[self.main_tabs.index(self.main_tabs.select())]

    def _active_backend_main_tab(self) -> str:
        return {"video": "Відео", "audio": "Аудіо", "photo": "Фото"}[self._active_main_tab_key()]

    def _active_backend_subtab(self) -> str:
        main_tab = self._active_main_tab_key()
        if main_tab == "video":
            return ["Конвертація та стиснення", "Обрізання та Склеювання", "Аудіодоріжка відео"][
                self.video_subtabs.index(self.video_subtabs.select())
            ]
        if main_tab == "audio":
            return ["Зміна формату", "Обробка звуку"][self.audio_subtabs.index(self.audio_subtabs.select())]
        return ["Конвертація зображень", "Створення GIF", "Розкадровка"][self.photo_subtabs.index(self.photo_subtabs.select())]

    def _set_notebook_state(self, notebook: ttk.Notebook, state: str) -> None:
        for tab_id in notebook.tabs():
            notebook.tab(tab_id, state=state)

    def _set_interactive_widgets_state(self, active: bool) -> None:
        if active:
            self._previous_widget_states.clear()
            for widget in self._iter_widgets(self):
                if widget in {self.run_button, self.progress_bar}:
                    continue
                try:
                    current_state = str(widget.cget("state"))
                except tk.TclError:
                    continue
                if current_state == "disabled":
                    continue
                self._previous_widget_states[widget] = current_state
                try:
                    widget.configure(state="disabled")
                except tk.TclError:
                    pass
            return

        for widget, previous_state in list(self._previous_widget_states.items()):
            try:
                widget.configure(state=previous_state)
            except tk.TclError:
                pass
        self._previous_widget_states.clear()

    def _iter_widgets(self, widget: tk.Widget):
        for child in widget.winfo_children():
            yield child
            yield from self._iter_widgets(child)

    def _refresh_concat_text(self) -> None:
        self.concat_text.configure(state="normal")
        self.concat_text.delete("1.0", "end")
        if self.concat_files:
            for index, path in enumerate(self.concat_files, start=1):
                self.concat_text.insert("end", f"{index}. {path}\n")
        else:
            self.concat_text.insert("end", self._tr("Список порожній. Додайте файли для безшовного склеювання.\n"))
        self.concat_text.configure(state="disabled")

    def _sync_audio_controls(self) -> None:
        if self.remove_audio.get():
            self.replacement_audio.set("")


def _file_pattern(extensions: set[str]) -> str:
    return " ".join(f"*{extension}" for extension in sorted(extensions))
