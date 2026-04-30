from __future__ import annotations

from app.pipeline.ocr import LocalOCRAdapter


def main() -> None:
    adapter = LocalOCRAdapter()
    print("Optional local OCR baseline: standalone jpg/jpeg/png only.")
    print(f"Local OCR engine: {adapter.engine_name}")
    if adapter.is_available():
        version = adapter.probe_version()
        first_line = version.text.splitlines()[0] if version.text else "n/a"
        print(f"Available: yes")
        print(f"Version: {first_line}")
    else:
        print("Available: no")
        print("Tesseract is optional; the baseline still works in metadata-only mode.")


if __name__ == "__main__":
    main()
