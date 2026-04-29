from __future__ import annotations

from pathlib import Path

from app.pipeline.extractors.txt import TxtExtractor


def test_txt_extractor_uses_fallback_encoding(tmp_path: Path) -> None:
    payload = "\u041f\u0440\u0438\u043c\u0435\u0440 \u0442\u0435\u043a\u0441\u0442\u0430 \u0432 cp1251".encode(
        "cp1251"
    )
    path = tmp_path / "encoded.txt"
    path.write_bytes(payload)

    extracted = TxtExtractor().extract(path)

    assert "\u041f\u0440\u0438\u043c\u0435\u0440 \u0442\u0435\u043a\u0441\u0442\u0430" in extracted.text
    assert extracted.metadata["source_encoding"] == "cp1251"
    assert extracted.warnings
