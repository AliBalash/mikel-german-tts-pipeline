from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .models import SentenceEntry


REGISTER_LABELS = {
    "دوستانه": "informal",
    "رسمی": "formal",
}


def normalize_line(line: str) -> str:
    return line.strip().replace("\u200c", " ")


def is_separator(line: str) -> bool:
    return not line or line == "---"


def extract_german_entry(line: str) -> tuple[str, str] | None:
    clean = normalize_line(line)
    match = re.match(r"^(?:(دوستانه|رسمی)\s*:\s*)?\*\*(.+?)\*\*$", clean)
    if not match:
        return None
    label, sentence = match.groups()
    register = REGISTER_LABELS.get(label, "neutral")
    return register, sentence.strip()


def parse_markdown_sentences(path: Path) -> list[SentenceEntry]:
    entries: list[SentenceEntry] = []
    current_section = "general"
    section_index = 0
    pending_variants: list[dict[str, str]] = []
    item_number = 0

    lines = path.read_text(encoding="utf-8").splitlines()
    for raw_line in lines:
        line = normalize_line(raw_line)
        if line.startswith("#"):
            if pending_variants:
                raise ValueError(
                    "A German sentence block was found without a following Persian line."
                )
            current_section = line.lstrip("#").strip()
            section_index += 1
            continue

        extracted = extract_german_entry(line)
        if extracted:
            register, german_text = extracted
            if not pending_variants:
                item_number += 1
            pending_variants.append(
                {
                    "register": register,
                    "german_text": german_text,
                }
            )
            continue

        if pending_variants and not is_separator(line):
            for variant_number, pending in enumerate(pending_variants, start=1):
                entries.append(
                    SentenceEntry(
                        section_index=section_index,
                        item_number=item_number,
                        variant_number=variant_number,
                        section=current_section,
                        register=pending["register"],
                        german_text=pending["german_text"],
                        persian_text=line,
                    )
                )
            pending_variants = []

    if pending_variants:
        raise ValueError("The file ended before the Persian translation line was found.")

    if not entries:
        raise ValueError(f"No German sentences were found in {path}.")

    return entries


def write_manifest(
    entries: Iterable[SentenceEntry],
    manifest_path: Path,
    *,
    dataset_slug: str | None = None,
    provider_name: str | None = None,
    voice_name: str | None = None,
    file_extension: str | None = None,
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for entry in entries:
        record = asdict(entry)
        record["file_stem"] = entry.stem
        if dataset_slug:
            record["dataset_slug"] = dataset_slug
        if provider_name:
            record["provider"] = provider_name
        if voice_name:
            record["voice_name"] = voice_name
        if file_extension:
            record["output_file"] = f"{entry.stem}.{file_extension}"
        payload.append(record)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
