from __future__ import annotations

import json
from pathlib import Path

import httpx

from ..config import env_or_value
from ..models import SentenceEntry
from .base import TTSProvider


ORPHEUS_VOICE_CATALOG = {
    "canopylabs/orpheus-v1-english": {
        "language": "en",
        "voices": {
            "female": ["autumn", "diana", "hannah"],
            "male": ["austin", "daniel", "troy"],
        },
    },
    "canopylabs/orpheus-arabic-saudi": {
        "language": "ar",
        "voices": {
            "female": ["lulwa", "noura", "aisha"],
            "male": ["abdullah", "fahad", "sultan"],
        },
    },
}


class GroqProxyTTSProvider(TTSProvider):
    provider_name = "groq_proxy"

    def __init__(self, settings: dict[str, object]):
        self.settings = settings
        self.base_url = (
            env_or_value(
                self.settings.get("base_url") if isinstance(self.settings.get("base_url"), str) else None,
                "GROQ_PROXY_BASE_URL",
            )
            or "http://127.0.0.1:18010"
        ).rstrip("/")

    def timeout_sec(self) -> float:
        raw = self.settings.get("timeout_sec")
        if isinstance(raw, (int, float)):
            return float(raw)
        return 120.0

    def default_model(self, language_code: str) -> str:
        configured = self.settings.get("model_name")
        if isinstance(configured, str) and configured.strip():
            return configured.strip()
        if language_code.lower().startswith("ar"):
            return "canopylabs/orpheus-arabic-saudi"
        return "canopylabs/orpheus-v1-english"

    def speech_speed(self) -> float:
        raw = self.settings.get("speech_speed", 0.86)
        if not isinstance(raw, (int, float)):
            return 0.86
        speed = float(raw)
        return min(5.0, max(0.5, speed))

    def speech_directions(self) -> str:
        raw = self.settings.get("speech_directions", "[calm] [clear]")
        if not isinstance(raw, str):
            return "[calm] [clear]"
        return raw.strip()

    def build_input_text(self, text: str, model_name: str) -> str:
        directions = self.speech_directions()
        if not directions or model_name != "canopylabs/orpheus-v1-english":
            return text
        candidate = f"{directions} {text}".strip()
        # Orpheus currently limits input to 200 chars; prefer the original text over truncation.
        if len(candidate) > 200:
            return text
        return candidate

    def list_voices(self, language_code: str) -> list[str]:
        model_name = self.default_model(language_code)
        available_models = self.available_models()
        if model_name not in available_models:
            raise RuntimeError(
                f"Groq proxy is reachable, but model '{model_name}' is not available for the configured key. "
                f"Available models: {', '.join(available_models)}"
            )
        model_catalog = ORPHEUS_VOICE_CATALOG.get(model_name)
        if not model_catalog:
            return []
        return model_catalog["voices"]["female"] + model_catalog["voices"]["male"]

    def available_models(self) -> list[str]:
        with httpx.Client(timeout=self.timeout_sec()) as client:
            response = client.get(f"{self.base_url}/proxy/groq/models")
        if response.status_code >= 400:
            raise RuntimeError(f"Groq proxy models request failed: HTTP {response.status_code} {response.text[:300]}")
        payload = response.json()
        data = payload.get("data", []) if isinstance(payload, dict) else []
        return sorted(str(item.get("id")) for item in data if isinstance(item, dict) and item.get("id"))

    def resolve_voice_name(self, *, model_name: str, requested_voice: str | None, voice_gender: str) -> str:
        catalog = ORPHEUS_VOICE_CATALOG.get(model_name)
        if not catalog:
            raise RuntimeError(f"No local voice catalog is defined for Groq model '{model_name}'.")
        all_voices = catalog["voices"]["female"] + catalog["voices"]["male"]
        if requested_voice:
            if requested_voice not in all_voices:
                raise RuntimeError(
                    f"Requested Groq voice '{requested_voice}' is not in the local Orpheus catalog for {model_name}."
                )
            return requested_voice
        return catalog["voices"][voice_gender][0]

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
        model_name = self.default_model(language_code)
        available_models = self.available_models()
        if model_name not in available_models:
            raise RuntimeError(
                f"Groq model '{model_name}' is not available for this key. Available: {', '.join(available_models)}"
            )

        voice_name = self.resolve_voice_name(
            model_name=model_name,
            requested_voice=requested_voice,
            voice_gender=voice_gender,
        )
        if audio_format != "wav":
            raise ValueError("Groq Orpheus currently supports only wav output.")

        output_dir.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=self.timeout_sec()) as client:
            for entry in entries:
                output_file = output_dir / f"{entry.stem}.{audio_format}"
                if output_file.exists() and not overwrite:
                    continue

                response = client.post(
                    f"{self.base_url}/proxy/groq/audio/speech",
                    json={
                        "model": model_name,
                        "voice": voice_name,
                        "input": self.build_input_text(entry.german_text, model_name),
                        "response_format": audio_format,
                        "speed": self.speech_speed(),
                    },
                    headers={"accept": "audio/wav, audio/*, application/octet-stream"},
                )
                if response.status_code >= 400:
                    message = response.text[:500]
                    try:
                        payload = response.json()
                        if (
                            isinstance(payload, dict)
                            and isinstance(payload.get("error"), dict)
                            and payload["error"].get("code") == "model_terms_required"
                        ):
                            raise RuntimeError(
                                "Groq model terms must be accepted first. Open "
                                "https://console.groq.com/playground?model=canopylabs%2Forpheus-v1-english "
                                "while signed into the same Groq account and accept the model terms."
                            )
                        message = json.dumps(payload, ensure_ascii=False)
                    except json.JSONDecodeError:
                        pass
                    raise RuntimeError(
                        f"Groq proxy TTS failed for item {entry.item_number}: HTTP {response.status_code} {message}"
                    )
                output_file.write_bytes(response.content)

        return voice_name, audio_format
