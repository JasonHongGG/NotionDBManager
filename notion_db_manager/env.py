from __future__ import annotations

import os
from pathlib import Path


ENV_KEYS = {
    "token": ("NOTION_DB_MANAGER_TOKEN", "NOTION_TOKEN"),
    "database_name": ("NOTION_DB_MANAGER_DATABASE_NAME", "NOTION_DATABASE_NAME"),
}


def load_env_file(path: Path | None = None) -> Path | None:
    env_path = path or (Path.cwd() / ".env")
    if not env_path.is_file():
        return None

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = _normalize_env_value(value.strip())
        if key and key not in os.environ:
            os.environ[key] = value
    return env_path


def get_env_value(setting_name: str) -> str | None:
    for key in ENV_KEYS[setting_name]:
        value = os.getenv(key)
        if value:
            return value
    return None


def _normalize_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    if " #" in value:
        return value.split(" #", 1)[0].rstrip()
    return value