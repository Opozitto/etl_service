from __future__ import annotations

import importlib
import subprocess
from types import SimpleNamespace


def _load_module():
    module = importlib.import_module("scripts.check_ocr")
    return importlib.reload(module)


def test_check_ocr_lists_languages_without_real_tesseract(monkeypatch) -> None:
    module = _load_module()
    adapter = SimpleNamespace(
        engine_command="tesseract",
        timeout_seconds=30.0,
        is_available=lambda: True,
    )

    class _CompletedProcess:
        returncode = 0
        stdout = "List of available languages in ./tessdata/ (3):\neng\nosd\nrus\n"
        stderr = ""

    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: _CompletedProcess())

    languages, warning = module.list_tesseract_languages(adapter)

    assert languages == ["eng", "osd", "rus"]
    assert warning is None


def test_check_ocr_language_listing_failure_is_warning(monkeypatch) -> None:
    module = _load_module()
    adapter = SimpleNamespace(
        engine_command="tesseract",
        timeout_seconds=0.1,
        is_available=lambda: True,
    )

    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="tesseract --list-langs", timeout=0.1)

    monkeypatch.setattr(module.subprocess, "run", _raise_timeout)

    languages, warning = module.list_tesseract_languages(adapter)

    assert languages == []
    assert warning is not None
    assert warning.startswith("ocr_language_list_timeout")
