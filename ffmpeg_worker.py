from __future__ import annotations

import json
import locale
import re
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable


VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".mov",
    ".webm",
    ".avi",
    ".wmv",
    ".flv",
    ".m4v",
    ".mpeg",
    ".mpg",
}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}

FORMAT_EXTENSIONS = {
    "MP4": ".mp4",
    "MKV": ".mkv",
    "MOV": ".mov",
    "WebM": ".webm",
    "MP3": ".mp3",
    "WAV": ".wav",
    "FLAC": ".flac",
    "AAC": ".aac",
    "OGG": ".ogg",
    "PNG": ".png",
    "JPEG": ".jpg",
    "WebP": ".webp",
    "BMP": ".bmp",
    "GIF": ".gif",
}


@dataclass(frozen=True)
class MediaInfo:
    name: str
    format_name: str
    duration: float | None
    video_codec: str | None = None
    audio_codec: str | None = None
    bitrate: int | None = None
    fps: float | None = None
    resolution: str | None = None


@dataclass
class CommandJob:
    command: list[str]
    output_path: Path | None
    progress_duration: float | None
    cleanup_paths: list[Path] = field(default_factory=list)
    title: str = ""


@dataclass
class FfmpegResult:
    success: bool
    returncode: int
    command: list[str]
    output_path: Path | None
    log_path: Path | None
    error_text: str


class CommandBuildError(ValueError):
    pass


def probe_media_info(input_path: str | Path) -> MediaInfo:
    path = Path(input_path)
    if not path.exists():
        return MediaInfo(path.name, path.suffix.lstrip(".").upper() or "невідомо", None)

    if not shutil.which("ffprobe"):
        return MediaInfo(path.name, path.suffix.lstrip(".").upper() or "невідомо", None)

    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=12,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return MediaInfo(path.name, path.suffix.lstrip(".").upper() or "невідомо", None)

    if completed.returncode != 0:
        return MediaInfo(path.name, path.suffix.lstrip(".").upper() or "невідомо", None)

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return MediaInfo(path.name, path.suffix.lstrip(".").upper() or "невідомо", None)

    media_format = payload.get("format", {})
    streams = payload.get("streams", [])
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
    duration = _safe_float(media_format.get("duration"))
    format_name = media_format.get("format_name") or path.suffix.lstrip(".").upper() or "невідомо"
    fps = _parse_fps(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate"))
    width = video_stream.get("width")
    height = video_stream.get("height")
    resolution = f"{width}x{height}" if width and height else None
    bitrate = _safe_int(media_format.get("bit_rate"))
    return MediaInfo(
        path.name,
        str(format_name),
        duration,
        video_codec=video_stream.get("codec_name"),
        audio_codec=audio_stream.get("codec_name"),
        bitrate=bitrate,
        fps=fps,
        resolution=resolution,
    )


def probe_media_details(input_path: str | Path) -> str:
    path = Path(input_path)
    info = probe_media_info(path)
    lines = [
        f"Файл: {info.name}",
        f"Формат: {info.format_name}",
        f"Тривалість: {format_duration(info.duration)}",
        f"Відеокодек: {info.video_codec or '-'}",
        f"Аудіокодек: {info.audio_codec or '-'}",
        f"Бітрейт: {_format_bitrate(info.bitrate)}",
        f"FPS: {_format_number(info.fps)}",
        f"Роздільна здатність: {info.resolution or '-'}",
    ]
    return "\n".join(lines)


def build_command_job(
    *,
    input_path: str | Path,
    main_tab: str,
    sub_tab: str,
    settings: dict[str, object],
    duration: float | None,
) -> CommandJob:
    source = Path(input_path)
    if not source.exists():
        raise CommandBuildError("Вхідний файл не знайдено.")

    if main_tab == "Відео":
        return _build_video_job(source, sub_tab, settings, duration)
    if main_tab == "Аудіо":
        return _build_audio_job(source, sub_tab, settings, duration)
    if main_tab == "Фото":
        return _build_photo_job(source, sub_tab, settings, duration)

    raise CommandBuildError("Не вдалося визначити активну головну вкладку.")


def run_ffmpeg(
    job: CommandJob,
    *,
    progress_callback: Callable[[float], None] | None = None,
    status_callback: Callable[[str], None] | None = None,
    output_callback: Callable[[str], None] | None = None,
) -> FfmpegResult:
    executable = Path(job.command[0]).name.lower()
    is_ffmpeg = executable in {"ffmpeg", "ffmpeg.exe"}
    if is_ffmpeg and not shutil.which("ffmpeg"):
        text = "FFmpeg не знайдено в PATH. Встановіть FFmpeg або додайте його до змінної PATH."
        log_path = _write_error_log(job.command, text)
        _cleanup(job.cleanup_paths)
        return FfmpegResult(False, -1, job.command, job.output_path, log_path, text)
    if not is_ffmpeg and not shutil.which(job.command[0]):
        text = f"Команду не знайдено в PATH: {job.command[0]}"
        log_path = _write_error_log(job.command, text, prefix="process_error")
        _cleanup(job.cleanup_paths)
        return FfmpegResult(False, -1, job.command, job.output_path, log_path, text)

    if is_ffmpeg:
        runtime_command = [
            job.command[0],
            "-hide_banner",
            "-nostdin",
            "-progress",
            "pipe:1",
            "-nostats",
            *job.command[1:],
        ]
    else:
        runtime_command = job.command[:]

    output_lines: list[str] = []
    returncode = -1

    try:
        process = subprocess.Popen(
            runtime_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except OSError as exc:
        text = str(exc)
        log_path = _write_error_log(runtime_command, text)
        _cleanup(job.cleanup_paths)
        return FfmpegResult(False, -1, runtime_command, job.output_path, log_path, text)

    assert process.stdout is not None
    for raw_line in process.stdout:
        line = raw_line.strip()
        if not line:
            continue
        output_lines.append(line)
        if output_callback:
            output_callback(raw_line)
        _handle_progress_line(line, job.progress_duration, progress_callback, status_callback)

    returncode = process.wait()
    if returncode == 0:
        if progress_callback:
            progress_callback(100.0)
        if status_callback:
            status_callback("Готово")
        _cleanup(job.cleanup_paths)
        return FfmpegResult(True, returncode, runtime_command, job.output_path, None, "")

    error_text = "\n".join(output_lines[-120:]).strip() or "FFmpeg завершився з помилкою."
    log_path = _write_error_log(runtime_command, "\n".join(output_lines))
    _cleanup(job.cleanup_paths)
    return FfmpegResult(False, returncode, runtime_command, job.output_path, log_path, error_text)


def run_cmd_command(
    command_text: str,
    *,
    working_dir: str | Path | None = None,
    output_callback: Callable[[str], None] | None = None,
    status_callback: Callable[[str], None] | None = None,
) -> FfmpegResult:
    command_text = command_text.strip()
    if not command_text:
        raise CommandBuildError("Введіть команду для виконання.")

    cwd = Path(working_dir) if working_dir else Path.cwd()
    if not cwd.exists() or not cwd.is_dir():
        raise CommandBuildError("Робоча папка для CMD-команди не існує.")

    runtime_command = ["cmd.exe", "/d", "/s", "/c", command_text]
    output_lines: list[str] = []

    if status_callback:
        status_callback("CMD-команда виконується...")

    try:
        process = subprocess.Popen(
            runtime_command,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding=locale.getpreferredencoding(False),
            errors="replace",
            bufsize=1,
        )
    except OSError as exc:
        text = str(exc)
        log_path = _write_error_log(runtime_command, text, prefix="cmd_error")
        return FfmpegResult(False, -1, runtime_command, None, log_path, text)

    assert process.stdout is not None
    for raw_line in process.stdout:
        output_lines.append(raw_line.rstrip("\n"))
        if output_callback:
            output_callback(raw_line)

    returncode = process.wait()
    full_output = "\n".join(output_lines)
    if returncode == 0:
        if status_callback:
            status_callback("CMD-команду виконано")
        return FfmpegResult(True, returncode, runtime_command, None, None, "")

    error_text = "\n".join(output_lines[-120:]).strip() or "CMD-команда завершилась з помилкою."
    log_path = _write_error_log(runtime_command, full_output, prefix="cmd_error")
    return FfmpegResult(False, returncode, runtime_command, None, log_path, error_text)


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "невідомо"
    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def parse_time_to_seconds(value: object) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return float(text)

    match = re.fullmatch(r"(\d{1,2}):(\d{1,2}):(\d{1,2}(?:\.\d+)?)", text)
    if not match:
        raise CommandBuildError("Час має бути у форматі ГГ:ХХ:СС або в секундах.")

    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))
    if minutes > 59 or seconds >= 60:
        raise CommandBuildError("У полі часу хвилини та секунди мають бути в межах 0-59.")
    return hours * 3600 + minutes * 60 + seconds


def _build_video_job(
    source: Path,
    sub_tab: str,
    settings: dict[str, object],
    duration: float | None,
) -> CommandJob:
    _ensure_not_image(source, "Для вкладки відео оберіть відеофайл.")

    if sub_tab == "Конвертація та стиснення":
        output_format = str(settings["format"])
        codec_label = str(settings["codec"])
        output_path = _unique_output_path(source, FORMAT_EXTENSIONS[output_format])
        codec = _video_codec_arg(codec_label, settings)
        command = ["ffmpeg", "-i", str(source)]

        filters: list[str] = []
        resolution = str(settings["resolution"])
        if resolution != "Оригінал":
            width, height = resolution.split(" ")[0].split("x")
            filters.append(f"scale={width}:{height}")
        filters.extend(_video_common_filters(settings))
        if filters:
            command.extend(["-vf", ",".join(filters)])

        audio_filters = _video_audio_filters(settings)
        if audio_filters:
            command.extend(["-af", ",".join(audio_filters)])

        command.extend(["-c:v", codec])
        if _uses_crf(codec):
            command.extend(["-crf", str(int(settings["crf"]))])
        command.extend(_audio_codec_for_video_container(output_format))
        command.extend(_custom_args(settings))
        command.append(str(output_path))
        return CommandJob(command, output_path, duration)

    if sub_tab == "Пакетна обробка":
        batch_files = [Path(path) for path in settings.get("batch_files", [])]
        if not batch_files:
            raise CommandBuildError("Додайте файли для пакетної обробки.")
        first = batch_files[0]
        output_format = str(settings.get("format", "MP4"))
        output_path = _unique_output_path(first, FORMAT_EXTENSIONS[output_format])
        codec = _video_codec_arg(str(settings.get("codec", "H.264")), settings)
        command = ["ffmpeg", "-i", str(first), "-c:v", codec, "-crf", str(int(settings.get("crf", 23)))]
        command.extend(_audio_codec_for_video_container(output_format))
        command.extend(_custom_args(settings))
        command.append(str(output_path))
        return CommandJob(command, output_path, duration, title=f"Пакет: {first.name}")

    if sub_tab == "Відео ефекти":
        output_path = _unique_output_path(source, source.suffix or ".mp4", "_effects")
        filters = _video_common_filters(settings)
        audio_filters = _video_audio_filters(settings)
        if not filters and not audio_filters:
            raise CommandBuildError("Оберіть хоча б один відео або аудіо ефект.")
        command = ["ffmpeg", "-i", str(source)]
        if filters:
            command.extend(["-vf", ",".join(filters)])
        if audio_filters:
            command.extend(["-af", ",".join(audio_filters)])
        command.extend(["-c:v", _video_codec_arg(str(settings.get("codec", "H.264")), settings), "-c:a", "aac"])
        command.extend(_custom_args(settings))
        command.append(str(output_path))
        return CommandJob(command, output_path, duration)

    if sub_tab == "Водяний знак і субтитри":
        return _build_watermark_subtitle_job(source, settings, duration)

    if sub_tab == "Кадри GIF мініатюра":
        return _build_video_extract_job(source, settings, duration)

    if sub_tab == "YouTube таймлапс стискання":
        return _build_video_extra_job(source, settings, duration)

    if sub_tab == "Обрізання та Склеювання":
        concat_files = [Path(path) for path in settings.get("concat_files", [])]
        if concat_files:
            for concat_file in concat_files:
                if not concat_file.exists():
                    raise CommandBuildError(f"Файл зі списку не знайдено: {concat_file}")
            output_path = _unique_output_path(concat_files[0], concat_files[0].suffix or ".mp4", "_merged")
            list_file = _create_concat_list(concat_files)
            command = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                str(output_path),
            ]
            return CommandJob(command, output_path, None, [list_file])

        start = parse_time_to_seconds(settings.get("trim_start"))
        end = parse_time_to_seconds(settings.get("trim_end"))
        if start is None and end is None:
            raise CommandBuildError("Вкажіть час обрізання або додайте файли для склеювання.")
        if start is not None and end is not None and end <= start:
            raise CommandBuildError("Кінцевий час має бути більшим за початковий.")

        output_path = _unique_output_path(source, source.suffix or ".mp4", "_trimmed")
        command = ["ffmpeg"]
        if start is not None:
            command.extend(["-ss", _format_seconds(start)])
        if start is not None and end is not None:
            command.extend(["-t", _format_seconds(end - start)])
        elif end is not None:
            command.extend(["-to", _format_seconds(end)])
        command.extend(["-i", str(source), "-c", "copy", str(output_path)])
        progress_duration = (end - start) if start is not None and end is not None else duration
        return CommandJob(command, output_path, progress_duration)

    if sub_tab == "Аудіодоріжка відео":
        remove_audio = bool(settings.get("remove_audio"))
        replacement_audio = str(settings.get("replacement_audio") or "").strip()
        output_path = _unique_output_path(source, source.suffix or ".mp4", "_audio")

        if remove_audio:
            command = ["ffmpeg", "-i", str(source), "-an", "-c:v", "copy", str(output_path)]
            return CommandJob(command, output_path, duration)

        if not replacement_audio:
            raise CommandBuildError("Оберіть аудіофайл для заміни або увімкніть вирізання звуку.")

        audio_path = Path(replacement_audio)
        if not audio_path.exists():
            raise CommandBuildError("Обраний аудіофайл не знайдено.")
        command = [
            "ffmpeg",
            "-i",
            str(source),
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
        return CommandJob(command, output_path, duration)

    raise CommandBuildError("Не вдалося визначити активну підвкладку відео.")


def _build_watermark_subtitle_job(source: Path, settings: dict[str, object], duration: float | None) -> CommandJob:
    output_path = _unique_output_path(source, source.suffix or ".mp4", "_marked")
    watermark_mode = str(settings.get("watermark_mode", "Текст"))
    watermark_text = str(settings.get("watermark_text") or "").strip()
    watermark_image = str(settings.get("watermark_image") or "").strip()
    subtitles = str(settings.get("subtitles") or "").strip()

    command = ["ffmpeg", "-i", str(source)]
    filters: list[str] = []

    if watermark_mode == "Текст" and watermark_text:
        safe_text = watermark_text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        filters.append(
            "drawtext="
            f"text='{safe_text}':x=20:y=20:fontsize=28:fontcolor=white:"
            "box=1:boxcolor=black@0.45:boxborderw=8"
        )
    elif watermark_mode == "Зображення":
        if not watermark_image:
            raise CommandBuildError("Оберіть зображення водяного знака.")
        image_path = Path(watermark_image)
        if not image_path.exists():
            raise CommandBuildError("Файл водяного знака не знайдено.")
        command.extend(["-i", str(image_path)])
        filter_complex = "[0:v][1:v]overlay=20:20"
        if subtitles:
            subtitle_path = _ffmpeg_filter_path(Path(subtitles))
            filter_complex += f",subtitles='{subtitle_path}'"
        command.extend(["-filter_complex", filter_complex, "-c:a", "copy"])
        command.extend(_custom_args(settings))
        command.append(str(output_path))
        return CommandJob(command, output_path, duration)

    if subtitles:
        subtitle_path = Path(subtitles)
        if not subtitle_path.exists():
            raise CommandBuildError("Файл субтитрів не знайдено.")
        filters.append(f"subtitles='{_ffmpeg_filter_path(subtitle_path)}'")

    if not filters:
        raise CommandBuildError("Додайте текст/зображення водяного знака або файл субтитрів.")

    command.extend(["-vf", ",".join(filters), "-c:a", "copy"])
    command.extend(_custom_args(settings))
    command.append(str(output_path))
    return CommandJob(command, output_path, duration)


def _build_video_extract_job(source: Path, settings: dict[str, object], duration: float | None) -> CommandJob:
    operation = str(settings.get("operation", "Витягнути кадри"))
    if operation == "Витягнути кадри":
        fps = str(settings.get("frames_fps") or "1").strip()
        image_format = str(settings.get("image_format") or "PNG")
        if not re.fullmatch(r"\d+(\.\d+)?", fps) or float(fps) <= 0:
            raise CommandBuildError("FPS для витягування кадрів має бути додатним числом.")
        parent = _output_directory(settings, source.parent)
        frames_dir = _unique_directory(parent / f"{source.stem}_frames")
        frames_dir.mkdir(parents=True, exist_ok=False)
        extension = ".jpg" if image_format == "JPG" else ".png"
        pattern = frames_dir / f"frame_%05d{extension}"
        command = ["ffmpeg", "-i", str(source), "-vf", f"fps={fps}", str(pattern)]
        return CommandJob(command, frames_dir, duration)

    if operation == "Створити GIF":
        start = parse_time_to_seconds(settings.get("gif_start"))
        end = parse_time_to_seconds(settings.get("gif_end"))
        if start is not None and end is not None and end <= start:
            raise CommandBuildError("Кінцевий час GIF має бути більшим за початковий.")
        output_path = _unique_output_path(source, ".gif", "_gif")
        fps = int(settings.get("gif_fps", 15))
        width = int(settings.get("gif_width", 480))
        filter_graph = (
            f"[0:v]fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];"
            "[s0]palettegen[p];[s1][p]paletteuse"
        )
        command = ["ffmpeg"]
        if start is not None:
            command.extend(["-ss", _format_seconds(start)])
        if start is not None and end is not None:
            command.extend(["-t", _format_seconds(end - start)])
        elif end is not None:
            command.extend(["-to", _format_seconds(end)])
        command.extend(["-i", str(source), "-filter_complex", filter_graph, "-loop", "0", str(output_path)])
        return CommandJob(command, output_path, _effective_duration(start, end, duration))

    thumb_time = parse_time_to_seconds(settings.get("thumbnail_time")) or 1
    image_format = str(settings.get("image_format") or "PNG")
    extension = ".jpg" if image_format == "JPG" else ".png"
    output_path = _unique_output_path(source, extension, "_thumbnail")
    command = ["ffmpeg", "-ss", _format_seconds(thumb_time), "-i", str(source), "-frames:v", "1", str(output_path)]
    return CommandJob(command, output_path, None)


def _build_video_extra_job(source: Path, settings: dict[str, object], duration: float | None) -> CommandJob:
    operation = str(settings.get("operation", "Таймлапс"))
    if operation == "Завантажити YouTube":
        url = str(settings.get("youtube_url") or "").strip()
        if not url:
            raise CommandBuildError("Вставте URL YouTube.")
        output_dir = _output_directory(settings, source.parent)
        output_template = output_dir / "%(title)s.%(ext)s"
        return CommandJob(["yt-dlp", "-o", str(output_template), url], output_dir, None, title="YouTube")

    if operation == "Автостискання":
        target_mb = _safe_float(settings.get("target_mb")) or 25
        if duration is None or duration <= 0:
            raise CommandBuildError("Для автостискання потрібна відома тривалість відео.")
        output_path = _unique_output_path(source, ".mp4", "_target_size")
        total_kbits = target_mb * 8192
        audio_kbps = 128
        video_kbps = max(150, int(total_kbits / duration - audio_kbps))
        command = [
            "ffmpeg",
            "-i",
            str(source),
            "-c:v",
            _video_codec_arg(str(settings.get("codec", "H.264")), settings),
            "-b:v",
            f"{video_kbps}k",
            "-maxrate",
            f"{int(video_kbps * 1.25)}k",
            "-bufsize",
            f"{int(video_kbps * 2)}k",
            "-c:a",
            "aac",
            "-b:a",
            f"{audio_kbps}k",
            str(output_path),
        ]
        return CommandJob(command, output_path, duration)

    speed = _safe_float(settings.get("timelapse_speed")) or 8
    if speed <= 0:
        raise CommandBuildError("Швидкість таймлапсу має бути більшою за 0.")
    output_path = _unique_output_path(source, source.suffix or ".mp4", "_timelapse")
    command = [
        "ffmpeg",
        "-i",
        str(source),
        "-vf",
        f"setpts=PTS/{speed:.3f}",
        "-an",
        str(output_path),
    ]
    return CommandJob(command, output_path, duration / speed if duration else None)


def _build_audio_job(
    source: Path,
    sub_tab: str,
    settings: dict[str, object],
    duration: float | None,
) -> CommandJob:
    if source.suffix.lower() in IMAGE_EXTENSIONS:
        raise CommandBuildError("Для вкладки аудіо оберіть аудіо або відеофайл.")

    if sub_tab == "Зміна формату":
        output_format = str(settings["format"])
        output_path = _unique_output_path(source, FORMAT_EXTENSIONS[output_format])
        command = ["ffmpeg", "-i", str(source), "-vn"]
        command.extend(_audio_encoder_args(output_format, str(settings["bitrate"])))
        command.append(str(output_path))
        return CommandJob(command, output_path, duration)

    if sub_tab == "Обробка звуку":
        start = parse_time_to_seconds(settings.get("audio_start"))
        end = parse_time_to_seconds(settings.get("audio_end"))
        if start is not None and end is not None and end <= start:
            raise CommandBuildError("Кінцевий час має бути більшим за початковий.")

        output_extension = source.suffix if source.suffix.lower() in AUDIO_EXTENSIONS else ".mp3"
        output_path = _unique_output_path(source, output_extension, "_audio_processed")
        output_duration = _effective_duration(start, end, duration)
        filters = _audio_filters(settings, output_duration)

        command = ["ffmpeg"]
        if start is not None:
            command.extend(["-ss", _format_seconds(start)])
        if start is not None and end is not None:
            command.extend(["-t", _format_seconds(end - start)])
        elif end is not None:
            command.extend(["-to", _format_seconds(end)])
        command.extend(["-i", str(source), "-vn"])
        if filters:
            command.extend(["-af", ",".join(filters)])
        command.extend(_audio_encoder_args_for_extension(output_extension))
        command.append(str(output_path))
        return CommandJob(command, output_path, output_duration)

    if sub_tab == "Об'єднання та витягування":
        operation = str(settings.get("operation", "Об'єднати аудіо"))
        if operation == "Витягнути аудіо з відео":
            output_format = str(settings.get("format", "MP3"))
            output_path = _unique_output_path(source, FORMAT_EXTENSIONS[output_format], "_extracted_audio")
            command = ["ffmpeg", "-i", str(source), "-vn"]
            command.extend(_audio_encoder_args(output_format, str(settings.get("bitrate", "192 kbps"))))
            command.append(str(output_path))
            return CommandJob(command, output_path, duration)

        audio_files = [Path(path) for path in settings.get("audio_files", [])]
        if not audio_files:
            raise CommandBuildError("Додайте аудіофайли для об'єднання.")
        for audio_file in audio_files:
            if not audio_file.exists():
                raise CommandBuildError(f"Аудіофайл не знайдено: {audio_file}")
        output_format = str(settings.get("format", "MP3"))
        output_path = _unique_output_path(audio_files[0], FORMAT_EXTENSIONS[output_format], "_merged_audio")
        list_file = _create_concat_list(audio_files)
        command = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(list_file)]
        command.extend(_audio_encoder_args(output_format, str(settings.get("bitrate", "192 kbps"))))
        command.append(str(output_path))
        return CommandJob(command, output_path, None, [list_file])

    raise CommandBuildError("Не вдалося визначити активну підвкладку аудіо.")


def _build_photo_job(
    source: Path,
    sub_tab: str,
    settings: dict[str, object],
    duration: float | None,
) -> CommandJob:
    if sub_tab == "Конвертація зображень":
        if source.suffix.lower() not in IMAGE_EXTENSIONS:
            raise CommandBuildError("Для конвертації зображень оберіть фотофайл.")
        output_format = str(settings["format"])
        output_path = _unique_output_path(source, FORMAT_EXTENSIONS[output_format])
        command = ["ffmpeg", "-i", str(source), str(output_path)]
        return CommandJob(command, output_path, None)

    if sub_tab == "Створення GIF":
        _ensure_video(source, "Для створення GIF оберіть відеофайл.")
        start = parse_time_to_seconds(settings.get("gif_start"))
        end = parse_time_to_seconds(settings.get("gif_end"))
        if start is not None and end is not None and end <= start:
            raise CommandBuildError("Кінцевий час GIF має бути більшим за початковий.")

        output_path = _unique_output_path(source, ".gif", "_gif")
        fps = int(settings["fps"])
        width = int(settings["width"])
        filter_graph = (
            f"[0:v]fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];"
            "[s0]palettegen[p];[s1][p]paletteuse"
        )
        command = ["ffmpeg"]
        if start is not None:
            command.extend(["-ss", _format_seconds(start)])
        if start is not None and end is not None:
            command.extend(["-t", _format_seconds(end - start)])
        elif end is not None:
            command.extend(["-to", _format_seconds(end)])
        command.extend(["-i", str(source), "-filter_complex", filter_graph, "-loop", "0", str(output_path)])
        return CommandJob(command, output_path, _effective_duration(start, end, duration))

    if sub_tab == "Розкадровка":
        _ensure_video(source, "Для розкадровки оберіть відеофайл.")
        fps = str(settings.get("frames_fps") or "").strip()
        if not re.fullmatch(r"\d+(\.\d+)?", fps) or float(fps) <= 0:
            raise CommandBuildError("Кадрів в секунду має бути додатним числом.")

        target_parent_text = str(settings.get("frames_dir") or "").strip()
        if not target_parent_text:
            raise CommandBuildError("Оберіть папку для збереження скріншотів.")
        target_parent = Path(target_parent_text)
        target_parent.mkdir(parents=True, exist_ok=True)
        frames_dir = _unique_directory(target_parent / f"{source.stem}_screenshots")
        frames_dir.mkdir(parents=True, exist_ok=False)
        pattern = frames_dir / "frame_%05d.png"
        command = ["ffmpeg", "-i", str(source), "-vf", f"fps={fps}", str(pattern)]
        return CommandJob(command, frames_dir, duration)

    raise CommandBuildError("Не вдалося визначити активну підвкладку фото.")


def _video_codec_arg(label: str, settings: dict[str, object] | None = None) -> str:
    settings = settings or {}
    hw = str(settings.get("hwaccel") or "Без прискорення")
    normalized = label.strip()

    if hw == "NVIDIA NVENC":
        return {
            "H.264": "h264_nvenc",
            "libx264": "h264_nvenc",
            "H.265": "hevc_nvenc",
            "libx265": "hevc_nvenc",
            "AV1": "av1_nvenc",
        }.get(normalized, "h264_nvenc")
    if hw == "Intel Quick Sync":
        return {
            "H.264": "h264_qsv",
            "libx264": "h264_qsv",
            "H.265": "hevc_qsv",
            "libx265": "hevc_qsv",
            "AV1": "av1_qsv",
            "VP9": "vp9_qsv",
        }.get(normalized, "h264_qsv")
    if hw == "AMD AMF":
        return {
            "H.264": "h264_amf",
            "libx264": "h264_amf",
            "H.265": "hevc_amf",
            "libx265": "hevc_amf",
            "AV1": "av1_amf",
        }.get(normalized, "h264_amf")

    return {
        "H.264": "libx264",
        "libx264": "libx264",
        "H.265": "libx265",
        "libx265": "libx265",
        "AV1": "libaom-av1",
        "VP9": "libvpx-vp9",
    }.get(normalized, normalized)


def _uses_crf(codec: str) -> bool:
    return codec not in {"h264_nvenc", "hevc_nvenc", "av1_nvenc", "h264_amf", "hevc_amf", "av1_amf"}


def _video_common_filters(settings: dict[str, object]) -> list[str]:
    filters: list[str] = []
    rotate = str(settings.get("rotate") or "Без повороту")
    if rotate == "90° вправо":
        filters.append("transpose=1")
    elif rotate == "90° вліво":
        filters.append("transpose=2")
    elif rotate == "180°":
        filters.append("transpose=1,transpose=1")

    fps = str(settings.get("fps") or "Оригінал")
    if fps != "Оригінал":
        filters.append(f"fps={fps}")

    speed = _safe_float(settings.get("speed")) or 1.0
    if abs(speed - 1.0) > 0.001:
        filters.append(f"setpts=PTS/{speed:.3f}")
    return filters


def _video_audio_filters(settings: dict[str, object]) -> list[str]:
    filters: list[str] = []
    if bool(settings.get("normalize_audio")):
        filters.append("loudnorm")
    speed = _safe_float(settings.get("speed")) or 1.0
    if abs(speed - 1.0) > 0.001:
        filters.extend(_atempo_filters(speed))
    return filters


def _atempo_filters(speed: float) -> list[str]:
    values: list[float] = []
    remaining = speed
    while remaining > 2.0:
        values.append(2.0)
        remaining /= 2.0
    while remaining < 0.5:
        values.append(0.5)
        remaining /= 0.5
    values.append(remaining)
    return [f"atempo={value:.3f}" for value in values if value > 0]


def _custom_args(settings: dict[str, object]) -> list[str]:
    custom = str(settings.get("custom_args") or "").strip()
    if not custom:
        return []
    try:
        return shlex.split(custom, posix=False)
    except ValueError as exc:
        raise CommandBuildError(f"Власні параметри FFmpeg некоректні: {exc}") from exc


def _output_directory(settings: dict[str, object], fallback: Path) -> Path:
    text = str(settings.get("output_dir") or "").strip()
    path = Path(text) if text else fallback
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ffmpeg_filter_path(path: Path) -> str:
    return path.resolve().as_posix().replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _audio_codec_for_video_container(output_format: str) -> list[str]:
    if output_format in {"MP4", "MOV"}:
        return ["-c:a", "aac"]
    if output_format == "WebM":
        return ["-c:a", "libopus"]
    return ["-c:a", "copy"]


def _audio_encoder_args(output_format: str, bitrate: str) -> list[str]:
    if output_format == "MP3":
        return ["-c:a", "libmp3lame", "-b:a", _bitrate_arg(bitrate)]
    if output_format == "WAV":
        return ["-c:a", "pcm_s16le"]
    if output_format == "FLAC":
        return ["-c:a", "flac"]
    if output_format == "AAC":
        return ["-c:a", "aac"]
    if output_format == "OGG":
        return ["-c:a", "libvorbis"]
    return []


def _audio_encoder_args_for_extension(extension: str) -> list[str]:
    extension = extension.lower()
    if extension == ".mp3":
        return ["-c:a", "libmp3lame"]
    if extension == ".wav":
        return ["-c:a", "pcm_s16le"]
    if extension == ".flac":
        return ["-c:a", "flac"]
    if extension in {".aac", ".m4a"}:
        return ["-c:a", "aac"]
    if extension == ".ogg":
        return ["-c:a", "libvorbis"]
    return []


def _bitrate_arg(label: str) -> str:
    match = re.search(r"\d+", label)
    if not match:
        return "192k"
    return f"{match.group(0)}k"


def _audio_filters(settings: dict[str, object], duration: float | None) -> list[str]:
    filters: list[str] = []
    volume_percent = int(settings.get("volume", 100))
    if volume_percent != 100:
        filters.append(f"volume={volume_percent / 100:.2f}")
    if bool(settings.get("fade_in")):
        filters.append("afade=t=in:st=0:d=3")
    if bool(settings.get("fade_out")):
        if duration is None:
            raise CommandBuildError("Для Fade-out не вдалося визначити тривалість аудіо.")
        fade_start = max(0.0, duration - 3.0)
        filters.append(f"afade=t=out:st={_format_seconds(fade_start)}:d=3")
    return filters


def _effective_duration(start: float | None, end: float | None, duration: float | None) -> float | None:
    if start is not None and end is not None:
        return end - start
    if end is not None:
        return end
    if start is not None and duration is not None:
        return max(0.0, duration - start)
    return duration


def _ensure_video(source: Path, message: str) -> None:
    if source.suffix.lower() not in VIDEO_EXTENSIONS:
        raise CommandBuildError(message)


def _ensure_not_image(source: Path, message: str) -> None:
    if source.suffix.lower() in IMAGE_EXTENSIONS:
        raise CommandBuildError(message)


def _unique_output_path(source: Path, extension: str, suffix: str = "_processed") -> Path:
    extension = extension if extension.startswith(".") else f".{extension}"
    directory = source.parent
    candidate = directory / f"{source.stem}{suffix}{extension}"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{source.stem}{suffix}_{counter}{extension}"
        counter += 1
    return candidate


def _unique_directory(path: Path) -> Path:
    candidate = path
    counter = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.name}_{counter}")
        counter += 1
    return candidate


def _create_concat_list(paths: list[Path]) -> Path:
    temp = tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8")
    try:
        with temp:
            for path in paths:
                normalized = path.resolve().as_posix().replace("'", r"'\''")
                temp.write(f"file '{normalized}'\n")
    except Exception:
        Path(temp.name).unlink(missing_ok=True)
        raise
    return Path(temp.name)


def _handle_progress_line(
    line: str,
    duration: float | None,
    progress_callback: Callable[[float], None] | None,
    status_callback: Callable[[str], None] | None,
) -> None:
    if line.startswith("out_time_ms=") and duration and progress_callback:
        try:
            out_time = int(line.split("=", 1)[1]) / 1_000_000
        except ValueError:
            return
        progress_callback(max(0.0, min(100.0, (out_time / duration) * 100)))
    elif line.startswith("out_time=") and duration and progress_callback:
        try:
            out_time = parse_time_to_seconds(line.split("=", 1)[1])
        except CommandBuildError:
            return
        if out_time is not None:
            progress_callback(max(0.0, min(100.0, (out_time / duration) * 100)))
    elif line == "progress=continue" and status_callback:
        status_callback("Обробка триває...")
    elif line == "progress=end" and status_callback:
        status_callback("Завершення...")


def _write_error_log(command: list[str], content: str, prefix: str = "ffmpeg_error") -> Path:
    logs_dir = Path.cwd() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"{prefix}_{stamp}.log"
    log_path.write_text(
        "Command:\n"
        + " ".join(f'"{part}"' if " " in part else part for part in command)
        + "\n\nOutput:\n"
        + content,
        encoding="utf-8",
    )
    return log_path


def _cleanup(paths: list[Path]) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def _format_seconds(seconds: float) -> str:
    if seconds.is_integer():
        return str(int(seconds))
    return f"{seconds:.3f}".rstrip("0").rstrip(".")


def _safe_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: object) -> int | None:
    try:
        if value is None:
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _parse_fps(value: object) -> float | None:
    text = str(value or "")
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        try:
            denominator_value = float(denominator)
            if denominator_value == 0:
                return None
            return float(numerator) / denominator_value
        except ValueError:
            return None
    return _safe_float(text)


def _format_bitrate(value: int | None) -> str:
    if not value:
        return "-"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f} Mbps"
    return f"{value / 1000:.0f} kbps"


def _format_number(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}".rstrip("0").rstrip(".")
