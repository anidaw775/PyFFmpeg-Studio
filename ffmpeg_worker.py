from __future__ import annotations

import json
import locale
import re
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


@dataclass
class CommandJob:
    command: list[str]
    output_path: Path | None
    progress_duration: float | None
    cleanup_paths: list[Path] = field(default_factory=list)


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
    duration = _safe_float(media_format.get("duration"))
    format_name = media_format.get("format_name") or path.suffix.lstrip(".").upper() or "невідомо"
    return MediaInfo(path.name, str(format_name), duration)


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
) -> FfmpegResult:
    if not shutil.which("ffmpeg"):
        text = "FFmpeg не знайдено в PATH. Встановіть FFmpeg або додайте його до змінної PATH."
        log_path = _write_error_log(job.command, text)
        _cleanup(job.cleanup_paths)
        return FfmpegResult(False, -1, job.command, job.output_path, log_path, text)

    runtime_command = [
        job.command[0],
        "-hide_banner",
        "-nostdin",
        "-progress",
        "pipe:1",
        "-nostats",
        *job.command[1:],
    ]

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
        if output_format == "WebM" and codec_label != "AV1":
            raise CommandBuildError("Для WebM оберіть кодек AV1 або змініть контейнер на MP4/MKV/MOV.")
        output_path = _unique_output_path(source, FORMAT_EXTENSIONS[output_format])
        codec = _video_codec_arg(codec_label)
        command = ["ffmpeg", "-i", str(source), "-c:v", codec, "-crf", str(int(settings["crf"]))]

        resolution = str(settings["resolution"])
        if resolution != "Оригінал":
            width, height = resolution.split(" ")[0].split("x")
            command.extend(["-vf", f"scale={width}:{height}"])

        command.extend(_audio_codec_for_video_container(output_format))
        command.append(str(output_path))
        return CommandJob(command, output_path, duration)

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


def _video_codec_arg(label: str) -> str:
    if label == "AV1":
        return "libaom-av1"
    return label


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
