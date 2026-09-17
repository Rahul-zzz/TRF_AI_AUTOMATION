"""Helpers for saving uploads and producing export file paths. Keeps
filesystem concerns out of the Streamlit pages and the processing logic."""

from __future__ import annotations

import datetime as dt
import os

from config.settings import SETTINGS


def ensure_data_dirs():
    for path in (SETTINGS.uploads_dir, SETTINGS.processed_dir, SETTINGS.exports_dir, SETTINGS.demo_dir):
        os.makedirs(path, exist_ok=True)


def save_upload_bytes(filename: str, content: bytes) -> str:
    ensure_data_dirs()
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{timestamp}_{os.path.basename(filename)}"
    path = os.path.join(SETTINGS.uploads_dir, safe_name)
    with open(path, "wb") as f:
        f.write(content)
    return path


def export_path(filename: str) -> str:
    ensure_data_dirs()
    return os.path.join(SETTINGS.exports_dir, filename)


def demo_file_path(filename: str = "synthetic_tracking_demo.xlsx") -> str:
    ensure_data_dirs()
    return os.path.join(SETTINGS.demo_dir, filename)
