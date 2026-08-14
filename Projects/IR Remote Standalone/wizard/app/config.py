"""Standalone configuration — reads from config.yaml in the project directory."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

# Project root is one level up from app/
PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_DIR / "config.yaml"
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "irdb.sqlite3"


@dataclass
class Config:
    esp32_host: str = ""
    esp32_port: int = 6053
    api_encryption_key: str = ""
    db_path: str = str(DB_PATH)
    data_dir: str = str(DATA_DIR)

    @classmethod
    def load(cls) -> Config:
        """Load configuration from config.yaml."""
        config = cls()

        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                options = yaml.safe_load(f) or {}
            config.esp32_host = options.get("esp32_host", "")
            config.esp32_port = options.get("esp32_port", 6053)
            config.api_encryption_key = options.get("api_encryption_key", "")

        return config
