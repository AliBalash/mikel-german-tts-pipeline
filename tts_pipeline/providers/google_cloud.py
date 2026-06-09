from __future__ import annotations

import os
from pathlib import Path

from ..config import env_or_value
from ..models import SentenceEntry
from .base import TTSProvider


GOOGLE_AUDIO_ENCODING_MAP = {
    "mp3": ("MP3", "mp3"),
    "wav": ("LINEAR16", "wav"),
    "ogg": ("OGG_OPUS", "ogg"),
}

GERMAN_VOICE_CANDIDATES = {
    "female": [
        "de-DE-Chirp-HD-O",
        "de-DE-Chirp-HD-F",
        "de-DE-Studio-C",
        "de-DE-Neural2-G",
        "de-DE-Wavenet-G",
        "de-DE-Standard-G",
    ],
    "male": [
        "de-DE-Chirp3-HD-Charon",
        "de-DE-Chirp3-HD-Schedar",
        "de-DE-Studio-B",
        "de-DE-Neural2-H",
        "de-DE-Wavenet-H",
        "de-DE-Standard-H",
    ],
}


class GoogleCloudTTSProvider(TTSProvider):
    provider_name = "google"

    def __init__(self, settings: dict[str, object]):
        self.settings = settings

    def ensure_credentials_present(self) -> None:
        credentials_path = env_or_value(
            self.settings.get("credentials_path") if isinstance(self.settings.get("credentials_path"), str) else None,
            "GOOGLE_APPLICATION_CREDENTIALS",
        )
        if credentials_path:
            credentials_file = Path(credentials_path).expanduser()
            if not credentials_file.exists():
                raise RuntimeError(
                    f"Configured GOOGLE_APPLICATION_CREDENTIALS path does not exist: {credentials_file}"
                )
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_file)
            return

        adc_path = Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
        if adc_path.exists():
            return

        raise RuntimeError(
            "Google credentials were not found. Use a service-account JSON file in "
            "GOOGLE_APPLICATION_CREDENTIALS or run gcloud application-default login later."
        )

    def build_audio_config(self, texttospeech, audio_format: str):
        encoding_name, _ = GOOGLE_AUDIO_ENCODING_MAP.get(audio_format, ("", ""))
        if not encoding_name:
            supported = ", ".join(sorted(GOOGLE_AUDIO_ENCODING_MAP))
            raise ValueError(f"Unsupported Google audio format '{audio_format}'. Use one of: {supported}")
        return texttospeech.AudioConfig(
            audio_encoding=getattr(texttospeech.AudioEncoding, encoding_name)
        )

    def list_available_voices(self, client, language_code: str) -> list[str]:
        response = client.list_voices(language_code=language_code)
        return sorted({voice.name for voice in response.voices if voice.name.startswith(language_code)})

    def resolve_voice_name(
        self,
        client,
        language_code: str,
        requested_voice: str | None,
        voice_gender: str,
    ) -> str:
        available = self.list_available_voices(client, language_code)
        if requested_voice:
            if requested_voice not in available:
                raise RuntimeError(
                    f"Requested voice '{requested_voice}' was not returned by Google for {language_code}."
                )
            return requested_voice

        for candidate in GERMAN_VOICE_CANDIDATES[voice_gender]:
            if candidate in available:
                return candidate

        raise RuntimeError(
            f"No preferred Google German {voice_gender} voice was found. Use list-voices to inspect the project."
        )

    def list_voices(self, language_code: str) -> list[str]:
        self.ensure_credentials_present()
        from google.cloud import texttospeech

        client = texttospeech.TextToSpeechClient()
        return self.list_available_voices(client, language_code)

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
        self.ensure_credentials_present()
        from google.cloud import texttospeech

        client = texttospeech.TextToSpeechClient()
        voice_name = self.resolve_voice_name(client, language_code, requested_voice, voice_gender)
        audio_config = self.build_audio_config(texttospeech, audio_format)
        _, file_extension = GOOGLE_AUDIO_ENCODING_MAP[audio_format]
        output_dir.mkdir(parents=True, exist_ok=True)

        for entry in entries:
            output_file = output_dir / f"{entry.stem}.{file_extension}"
            if output_file.exists() and not overwrite:
                continue

            response = client.synthesize_speech(
                input=texttospeech.SynthesisInput(text=entry.german_text),
                voice=texttospeech.VoiceSelectionParams(
                    language_code=language_code,
                    name=voice_name,
                ),
                audio_config=audio_config,
            )
            output_file.write_bytes(response.audio_content)

        return voice_name, file_extension
