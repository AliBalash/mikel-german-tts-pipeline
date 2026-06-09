from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ..config import env_or_value
from ..models import SentenceEntry
from .base import TTSProvider


AZURE_AUDIO_FORMAT_PRESETS = {
    "mp3": ("Audio24Khz160KBitRateMonoMp3", "mp3"),
    "wav": ("Riff24Khz16BitMonoPcm", "wav"),
    "ogg": ("Ogg24Khz16BitMonoOpus", "ogg"),
}

AZURE_GERMAN_VOICE_CANDIDATES = {
    "female": [
        "de-de-Seraphina:DragonHDLatestNeural",
        "de-DE-SeraphinaMultilingualNeural",
        "de-DE-KatjaNeural",
    ],
    "male": [
        "de-de-Florian:DragonHDLatestNeural",
        "de-DE-FlorianMultilingualNeural",
        "de-DE-ConradNeural",
    ],
}


class AzureSpeechTTSProvider(TTSProvider):
    provider_name = "azure"

    def __init__(self, settings: dict[str, object]):
        self.settings = settings

    def speech_key(self) -> str:
        value = env_or_value(
            self.settings.get("speech_key") if isinstance(self.settings.get("speech_key"), str) else None,
            "AZURE_SPEECH_KEY",
            "SPEECH_KEY",
        )
        if not value:
            raise RuntimeError(
                "Azure Speech key is missing. Set AZURE_SPEECH_KEY or SPEECH_KEY, or put speech_key in config."
            )
        return value

    def speech_endpoint(self) -> str | None:
        return env_or_value(
            self.settings.get("endpoint") if isinstance(self.settings.get("endpoint"), str) else None,
            "AZURE_SPEECH_ENDPOINT",
            "ENDPOINT",
        )

    def speech_region(self) -> str | None:
        explicit_region = env_or_value(
            self.settings.get("speech_region") if isinstance(self.settings.get("speech_region"), str) else None,
            "AZURE_SPEECH_REGION",
            "SPEECH_REGION",
        )
        if explicit_region:
            return explicit_region

        endpoint = self.speech_endpoint()
        if not endpoint:
            return None

        match = re.match(r"^https://([a-z0-9-]+)\.(?:tts\.speech\.microsoft\.com|api\.cognitive\.microsoft\.com)", endpoint)
        if match:
            return match.group(1)
        return None

    def ensure_credentials_present(self) -> None:
        self.speech_key()
        if not self.speech_endpoint() and not self.speech_region():
            raise RuntimeError(
                "Azure Speech needs endpoint or region. Set AZURE_SPEECH_ENDPOINT / ENDPOINT or AZURE_SPEECH_REGION / SPEECH_REGION."
            )

    def resolve_voice_name(self, available: list[str], requested_voice: str | None, voice_gender: str) -> str:
        if requested_voice:
            if requested_voice not in available:
                raise RuntimeError(
                    f"Requested Azure voice '{requested_voice}' was not returned by the voices list endpoint."
                )
            return requested_voice

        for candidate in AZURE_GERMAN_VOICE_CANDIDATES[voice_gender]:
            if candidate in available:
                return candidate

        raise RuntimeError(
            f"No preferred Azure German {voice_gender} voice was found. Use list-voices to inspect the region."
        )

    def resolve_output_format(self, speechsdk, audio_format: str) -> tuple[object, str]:
        preset = AZURE_AUDIO_FORMAT_PRESETS.get(audio_format)
        if preset:
            enum_name, file_extension = preset
            return getattr(speechsdk.SpeechSynthesisOutputFormat, enum_name), file_extension

        if hasattr(speechsdk.SpeechSynthesisOutputFormat, audio_format):
            file_extension = "wav" if "Riff" in audio_format else "ogg" if "Ogg" in audio_format else "mp3"
            return getattr(speechsdk.SpeechSynthesisOutputFormat, audio_format), file_extension

        supported = ", ".join(sorted(AZURE_AUDIO_FORMAT_PRESETS))
        raise ValueError(f"Unsupported Azure audio format '{audio_format}'. Use one of: {supported}")

    def list_voices(self, language_code: str) -> list[str]:
        self.ensure_credentials_present()
        region = self.speech_region()
        if not region:
            raise RuntimeError(
                "Azure voice listing needs a region. Set AZURE_SPEECH_REGION or speech_region in config."
            )

        request = Request(
            url=f"https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list",
            headers={
                "Ocp-Apim-Subscription-Key": self.speech_key(),
            },
            method="GET",
        )

        try:
            with urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Azure voices/list failed: HTTP {exc.code} {detail}") from exc

        return sorted(
            {
                voice["ShortName"]
                for voice in payload
                if voice.get("Locale", "").lower() == language_code.lower()
            }
        )

    def build_speech_config(self, speechsdk):
        subscription = self.speech_key()
        endpoint = self.speech_endpoint()
        region = self.speech_region()
        if endpoint:
            return speechsdk.SpeechConfig(subscription=subscription, endpoint=endpoint)
        return speechsdk.SpeechConfig(subscription=subscription, region=region)

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
        import azure.cognitiveservices.speech as speechsdk

        available = self.list_voices(language_code)
        voice_name = self.resolve_voice_name(available, requested_voice, voice_gender)
        output_format, file_extension = self.resolve_output_format(speechsdk, audio_format)
        output_dir.mkdir(parents=True, exist_ok=True)

        speech_config = self.build_speech_config(speechsdk)
        speech_config.speech_synthesis_voice_name = voice_name
        speech_config.set_speech_synthesis_output_format(output_format)

        for entry in entries:
            output_file = output_dir / f"{entry.stem}.{file_extension}"
            if output_file.exists() and not overwrite:
                continue

            audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_file))
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=audio_config,
            )
            result = synthesizer.speak_text_async(entry.german_text).get()
            if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
                cancellation = getattr(result, "cancellation_details", None)
                if cancellation and cancellation.error_details:
                    raise RuntimeError(
                        f"Azure synthesis failed for item {entry.item_number}: {cancellation.error_details}"
                    )
                raise RuntimeError(
                    f"Azure synthesis failed for item {entry.item_number} with reason {result.reason}"
                )

        return voice_name, file_extension
