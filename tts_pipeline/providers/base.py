from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import SentenceEntry


class TTSProvider(ABC):
    provider_name: str

    @abstractmethod
    def list_voices(self, language_code: str) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def synthesize_entries(
        self,
        entries: list[SentenceEntry],
        output_dir: Path,
        *,
        language_code: str,
        requested_voice: str | None,
        voice_gender: str,
        audio_format: str,
        overwrite: bool,
    ) -> tuple[str, str]:
        """Return (voice_name, file_extension)."""
