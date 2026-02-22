# Python
import json
from pathlib import Path
from typing import Any

from src.protocols.chunker import chunk_text


def load_and_chunk_protocols(
    jsonl_path: str | Path,
    chunk_size: int = 900,
    overlap: int = 150,
) -> list[dict[str, Any]]:
    """
    Читает protocols_corpus.jsonl (1 JSON на строку),
    режет text на чанки и возвращает список чанков:
    {
      "protocol_id": "...",
      "title": "...",
      "chunk_text": "..."
    }

    ВАЖНО: НЕ используем поле icd_codes из корпуса.
    """
    path = Path(jsonl_path)
    if not path.exists():
        raise FileNotFoundError(f"Protocols file not found: {path}")

    chunks: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            text = obj.get("text") or ""
            if not text.strip():
                continue

            protocol_id = obj.get("protocol_id", f"unknown_{line_no}")
            title = obj.get("title") or obj.get("source_file") or "Unknown"

            for piece in chunk_text(text, size=chunk_size, overlap=overlap):
                chunks.append(
                    {
                        "protocol_id": protocol_id,
                        "title": title,
                        "chunk_text": piece,
                    }
                )

    if not chunks:
        raise RuntimeError("No chunks created. Check corpus jsonl format or path.")
    return chunks