from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SentenceEntry:
    section_index: int
    item_number: int
    variant_number: int
    section: str
    register: str
    german_text: str
    persian_text: str

    @property
    def stem(self) -> str:
        return f"{self.item_number:03d}_s{self.section_index:02d}_{self.register}_{self.variant_number:02d}"
