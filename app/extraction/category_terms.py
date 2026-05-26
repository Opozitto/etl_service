from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import TypeVar

from app.core.config import get_settings


Category = TypeVar("Category", bound=str)


def configured_category_terms(
    section: str,
    defaults: dict[Category, tuple[str, ...]],
) -> dict[Category, tuple[str, ...]]:
    """Return default category terms with optional read-only JSON overrides."""
    settings = get_settings()
    config_path = settings.rules_config_path
    if config_path is None:
        return defaults

    if not config_path.is_absolute():
        config_path = (settings.project_root / config_path).resolve()

    config = _read_config(config_path)
    if config is None:
        return defaults

    section_config = config.get(section)
    if not isinstance(section_config, dict):
        return defaults

    terms = dict(defaults)
    replacements = section_config.get("category_terms")
    additions = section_config.get("additional_category_terms")
    if isinstance(replacements, dict):
        for category, values in replacements.items():
            if category in defaults:
                parsed = _parse_terms(values, config_path, section, category)
                if parsed is not None:
                    terms[category] = parsed
    elif replacements is not None:
        _warn(config_path, f"{section}.category_terms must be an object; using defaults")

    if isinstance(additions, dict):
        for category, values in additions.items():
            if category in defaults:
                parsed = _parse_terms(values, config_path, section, category)
                if parsed is not None:
                    terms[category] = tuple(dict.fromkeys((*terms[category], *parsed)))
    elif additions is not None:
        _warn(config_path, f"{section}.additional_category_terms must be an object; using defaults")

    return terms


def _read_config(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _warn(path, "rules config path does not exist; using built-in category terms")
        return None
    except (OSError, json.JSONDecodeError) as exc:
        _warn(path, f"rules config could not be read: {exc}; using built-in category terms")
        return None
    if not isinstance(payload, dict):
        _warn(path, "rules config root must be an object; using built-in category terms")
        return None
    return payload


def _parse_terms(values: object, path: Path, section: str, category: str) -> tuple[str, ...] | None:
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        _warn(path, f"{section}.{category} terms must be a list of strings; using defaults")
        return None
    return tuple(term.strip().lower() for term in values if term.strip())


def _warn(path: Path, message: str) -> None:
    warnings.warn(f"{path}: {message}", RuntimeWarning, stacklevel=3)
