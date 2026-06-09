from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

from ..config import env_or_value
from ..models import SentenceEntry
from .base import TTSProvider


class YourVoicTTSProvider(TTSProvider):
    provider_name = "yourvoic"

    def __init__(self, settings: dict[str, object]):
        self.settings = settings
        self.base_url = (
            env_or_value(
                self.settings.get("base_url") if isinstance(self.settings.get("base_url"), str) else None,
                "YOURVOIC_BASE_URL",
            )
            or "https://yourvoic.com/api/v1"
        ).rstrip("/")

    def api_key(self) -> str:
        value = env_or_value(
            self.settings.get("api_key") if isinstance(self.settings.get("api_key"), str) else None,
            "YOURVOIC_API_KEY",
        )
        if not value:
            raise RuntimeError("YourVoic API key is missing. Set YOURVOIC_API_KEY or put api_key in config.")
        return value

    def model_name(self) -> str:
        configured = self.settings.get("model_name")
        if isinstance(configured, str) and configured.strip():
            return configured.strip()
        return "aura-prime"

    def speed(self) -> float:
        raw = self.settings.get("speech_speed", 1.0)
        if not isinstance(raw, (int, float)):
            return 1.0
        return min(2.0, max(0.5, float(raw)))

    def format_name(self, audio_format: str) -> str:
        if audio_format not in {"mp3", "wav"}:
            raise ValueError("YourVoic currently supports mp3 or wav in this provider.")
        return audio_format

    def language_value(self, language_code: str) -> str:
        if language_code.lower().startswith("de"):
            return "de"
        return language_code

    def list_voices(self, language_code: str) -> list[str]:
        params = {
            "language": self.language_value(language_code),
            "model": self.model_name(),
        }
        with httpx.Client(timeout=60.0) as client:
            response = client.get(
                f"{self.base_url}/voices",
                params=params,
                headers={"X-API-Key": self.api_key()},
            )
        if response.status_code >= 400:
            raise RuntimeError(f"YourVoic voices request failed: HTTP {response.status_code} {response.text[:300]}")
        payload = response.json()
        voices = payload.get("voices", []) if isinstance(payload, dict) else []
        return [str(item.get("name")) for item in voices if isinstance(item, dict) and item.get("name")]

    def usage_info(self) -> dict[str, object]:
        with httpx.Client(timeout=60.0) as client:
            response = client.get(f"{self.base_url}/usage", headers={"X-API-Key": self.api_key()})
        if response.status_code >= 400:
            raise RuntimeError(f"YourVoic usage request failed: HTTP {response.status_code} {response.text[:300]}")
        return response.json()

    def post_tts(self, payload: dict[str, object]) -> httpx.Response:
        attempts = 0
        while True:
            attempts += 1
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.base_url}/tts/generate",
                    headers={
                        "X-API-Key": self.api_key(),
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            if response.status_code != 429 or attempts >= 5:
                return response
            retry_after = response.headers.get("Retry-After")
            wait_seconds = 20.0
            if retry_after:
                try:
                    wait_seconds = max(1.0, float(retry_after))
                except ValueError:
                    wait_seconds = 20.0
            time.sleep(wait_seconds)

    def resolve_voice_name(self, requested_voice: str | None, voice_gender: str, language_code: str) -> str:
        available = self.list_voices(language_code)
        if requested_voice:
            if requested_voice not in available:
                raise RuntimeError(
                    f"Requested YourVoic voice '{requested_voice}' is not available. Known voices include: {', '.join(available[:20])}"
                )
            return requested_voice

        preferred_male = ["Paul", "Karl", "Felix", "Alexander", "Robert", "Elias", "Jonas", "Lukas", "Philipp"]
        preferred_female = ["Anna", "Clara", "Katharina", "Lena", "Sophie", "Nadine", "Elisa", "Anja"]
        preferred = preferred_male if voice_gender == "male" else preferred_female
        for candidate in preferred:
            if candidate in available:
                return candidate
        if not available:
            raise RuntimeError("No YourVoic voices were returned for the requested language/model.")
        return available[0]

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
        model_name = self.model_name()
        voice_name = self.resolve_voice_name(requested_voice, voice_gender, language_code)
        output_format = self.format_name(audio_format)
        output_dir.mkdir(parents=True, exist_ok=True)

        for entry in entries:
            output_file = output_dir / f"{entry.stem}.{output_format}"
            if output_file.exists() and not overwrite:
                continue

            response = self.post_tts(
                {
                    "text": entry.german_text,
                    "voice": voice_name,
                    "language": self.language_value(language_code),
                    "model": model_name,
                    "speed": self.speed(),
                    "format": output_format,
                }
            )

            if response.status_code >= 400 or response.headers.get("content-type", "").startswith("application/json"):
                try:
                    payload = response.json()
                    if isinstance(payload, dict) and payload.get("success") is False:
                        raise RuntimeError(
                            f"YourVoic TTS failed for item {entry.item_number}: "
                            f"{json.dumps(payload, ensure_ascii=False)}"
                        )
                except json.JSONDecodeError:
                    pass

            if response.status_code >= 400:
                raise RuntimeError(
                    f"YourVoic TTS failed for item {entry.item_number}: HTTP {response.status_code} {response.text[:500]}"
                )
            output_file.write_bytes(response.content)

        return voice_name, output_format
