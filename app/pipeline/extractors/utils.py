from __future__ import annotations

from pathlib import Path


def decode_text_file(path: Path) -> tuple[str, str, list[str]]:
    payload = path.read_bytes()
    warnings: list[str] = []
    encodings = ("utf-8-sig", "utf-8", "cp1251", "cp866")

    for encoding in encodings:
        try:
            text = payload.decode(encoding)
            if encoding != "utf-8":
                warnings.append(f"Decoded source using fallback encoding: {encoding}.")
            return normalize_decoded_text(text), encoding, warnings
        except UnicodeDecodeError:
            continue

    text = payload.decode("latin-1", errors="replace")
    warnings.append("Source encoding could not be determined reliably; used latin-1 fallback with replacement.")
    return normalize_decoded_text(text), "latin-1", warnings


def normalize_decoded_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()
