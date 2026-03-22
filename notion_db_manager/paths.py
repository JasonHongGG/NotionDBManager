from __future__ import annotations

from pathlib import Path


OUTPUT_DIR_NAME = "output"


def get_output_dir() -> Path:
    return Path.cwd() / OUTPUT_DIR_NAME


def resolve_output_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        resolved = path
    elif _is_output_relative(path):
        resolved = Path.cwd() / path
    else:
        resolved = get_output_dir() / path
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def resolve_input_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path
    if _is_output_relative(path):
        return Path.cwd() / path

    output_candidate = get_output_dir() / path
    if output_candidate.is_file():
        return output_candidate
    return Path.cwd() / path


def _is_output_relative(path: Path) -> bool:
    return bool(path.parts) and path.parts[0] == OUTPUT_DIR_NAME