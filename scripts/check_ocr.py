from __future__ import annotations

import subprocess

from app.pipeline.ocr import LocalOCRAdapter


def list_tesseract_languages(adapter: LocalOCRAdapter) -> tuple[list[str], str | None]:
    if not adapter.is_available():
        return [], "ocr_engine_unavailable"

    try:
        completed = subprocess.run(
            [adapter.engine_command, "--list-langs"],
            capture_output=True,
            text=True,
            check=False,
            timeout=adapter.timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return [], f"ocr_language_list_timeout: {exc}"
    except FileNotFoundError as exc:
        return [], f"ocr_engine_unavailable: {exc}"
    except OSError as exc:
        return [], f"ocr_language_list_failed: {exc}"

    output = completed.stdout or completed.stderr or ""
    if completed.returncode != 0:
        return [], f"ocr_language_list_failed: {output.strip() or f'exit_code_{completed.returncode}'}"

    languages = [
        line.strip()
        for line in output.splitlines()
        if line.strip() and not line.lower().startswith("list of available languages")
    ]
    return languages, None


def main() -> None:
    adapter = LocalOCRAdapter()
    print("Optional local OCR baseline: standalone jpg/jpeg/png only.")
    print(f"Local OCR engine: {adapter.engine_name}")
    if adapter.is_available():
        version = adapter.probe_version()
        first_line = version.text.splitlines()[0] if version.text else "n/a"
        print(f"Available: yes")
        print(f"Version: {first_line}")
        languages, warning = list_tesseract_languages(adapter)
        if languages:
            print(f"Available languages: {', '.join(languages)}")
        else:
            print("Available languages: n/a")
        if warning:
            print(f"Warning: {warning}")
    else:
        print("Available: no")
        print("Tesseract is optional; the baseline still works in metadata-only mode.")
        print("Available languages: n/a")


if __name__ == "__main__":
    main()
