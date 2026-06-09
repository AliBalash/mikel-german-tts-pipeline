from __future__ import annotations

import json
from pathlib import Path

import httpx

from ..config import env_or_value
from ..models import SentenceEntry
from .base import TTSProvider


GRADIUM_GERMAN_VOICES = {
    "Mia": {
        "voice_id": "-uP9MuGtBqAvEyxI",
        "gender": "female",
        "description": "Flagship German feminine voice from the official Gradium docs.",
    },
    "Maximilian": {
        "voice_id": "0y1VZjPabOBU3rWy",
        "gender": "male",
        "description": "Flagship German masculine voice from the official Gradium docs.",
    },
}


class GradiumTTSProvider(TTSProvider):
    provider_name = "gradium"

    def __init__(self, settings: dict[str, object]):
        self.settings = settings
        self.base_url = (
            env_or_value(
                self.settings.get("base_url") if isinstance(self.settings.get("base_url"), str) else None,
                "GRADIUM_BASE_URL",
            )
            or "https://api.gradium.ai/api"
        ).rstrip("/")

    def api_key(self) -> str:
        value = env_or_value(
            self.settings.get("api_key") if isinstance(self.settings.get("api_key"), str) else None,
            "GRADIUM_API_KEY",
        )
        if not value:
            raise RuntimeError("Gradium API key is missing. Set GRADIUM_API_KEY or put api_key in config.")
        return value

    def timeout_sec(self) -> float:
        raw = self.settings.get("timeout_sec")
        if isinstance(raw, (int, float)):
            return float(raw)
        return 120.0

    def speed(self) -> float:
        raw = self.settings.get("speech_speed", 0.9)
        if not isinstance(raw, (int, float)):
            return 0.9
        return min(1.5, max(0.6, float(raw)))

    def list_voices(self, language_code: str) -> list[str]:
        if not language_code.lower().startswith("de"):
            return []
        return list(GRADIUM_GERMAN_VOICES)

    def resolve_voice(self, requested_voice: str | None, voice_gender: str) -> tuple[str, str]:
        if requested_voice:
            voice = GRADIUM_GERMAN_VOICES.get(requested_voice)
            if not voice:
                raise RuntimeError(
                    f"Unknown Gradium voice '{requested_voice}'. Known voices: {', '.join(GRADIUM_GERMAN_VOICES)}"
                )
            return requested_voice, voice["voice_id"]

        for name, voice in GRADIUM_GERMAN_VOICES.items():
            if voice["gender"] == voice_gender:
                return name, voice["voice_id"]
        fallback_name = "Maximilian"
        return fallback_name, GRADIUM_GERMAN_VOICES[fallback_name]["voice_id"]

    def credits_info(self) -> dict[str, object]:
        with httpx.Client(timeout=self.timeout_sec()) as client:
            response = client.get(
                f"{self.base_url}/metering/credits",
                headers={"x-api-key": self.api_key()},
            )
        if response.status_code >= 400:
            raise RuntimeError(f"Gradium credits check failed: HTTP {response.status_code} {response.text[:300]}")
        return response.json()

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
        if audio_format not in {"wav", "opus"}:
            raise ValueError("Gradium currently supports wav or opus in this provider.")
        if not language_code.lower().startswith("de"):
            raise RuntimeError("This Gradium provider is currently configured only for German voices.")

        voice_name, voice_id = self.resolve_voice(requested_voice, voice_gender)
        output_dir.mkdir(parents=True, exist_ok=True)

        with httpx.Client(timeout=self.timeout_sec()) as client:
            for entry in entries:
                output_file = output_dir / f"{entry.stem}.{audio_format}"
                if output_file.exists() and not overwrite:
                    continue

                response = client.post(
                    f"{self.base_url}/post/speech/tts",
                    headers={
                        "x-api-key": self.api_key(),
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": entry.german_text,
                        "voice_id": voice_id,
                        "output_format": audio_format,
                        "only_audio": True,
                        "json_config": json.dumps({"speed": self.speed()}),
                    },
                )
                if response.status_code >= 400:
                    try:
                        payload = response.json()
                        message = json.dumps(payload, ensure_ascii=False)
                    except Exception:
                        message = response.text[:500]
                    if "Insufficient credits" in message:
                        credits = self.credits_info()
                        raise RuntimeError(
                            f"Gradium refused synthesis with an insufficient-credits session error. "
                            f"Metering currently reports: {json.dumps(credits, ensure_ascii=False)}"
                        )
                    raise RuntimeError(
                        f"Gradium TTS failed for item {entry.item_number}: HTTP {response.status_code} {message}"
                    )
                output_file.write_bytes(response.content)

        return voice_name, audio_format
