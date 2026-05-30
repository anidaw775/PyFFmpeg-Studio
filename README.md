# PyFFmpeg-Studio

The application is a graphical interface for the FFmpeg command-line utility. The purpose of the program is to allow users to convert video files, resize them, and trim them by time without using the command line.

## Features

* Select or drag & drop input media files.
* Video: conversion, compression, trimming, merging, audio removal or replacement.
* Audio: format conversion, trimming, volume adjustment, fade-in and fade-out.
* Images: image conversion, GIF creation from video, frame extraction to PNG.
* Manual CMD command execution directly from the application window.
* Interface language settings: Ukrainian / English.
* Error logging to the `logs` folder.

## Requirements

* Python 3.10+
* FFmpeg and FFprobe available in `PATH`
* Python dependencies from `requirements.txt`

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Check FFmpeg:

```powershell
ffmpeg -version
ffprobe -version
```

## Launch

```powershell
python main.py
```

## Interface Language

Click the `Settings` button at the top of the window, choose a language, and press `Save`.

Settings are stored in:

```text
settings.json
```

## Manual CMD Command

The `Manual Command` tab allows you to execute custom commands via:

```text
cmd.exe /d /s /c
```

In this tab, you can select a working directory, insert the path to the current input file, and view command output directly in the application.

## Structure

* `main.py` - application entry point and critical startup error handling.
* `gui_tabs.py` - UI, tabs, drag & drop, settings.
* `ffmpeg_worker.py` - FFmpeg/CMD command builder, execution, progress, logs.
* `requirements.txt` - Python dependencies.
