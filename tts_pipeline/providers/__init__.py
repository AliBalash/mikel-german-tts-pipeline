from __future__ import annotations

from .azure_speech import AzureSpeechTTSProvider
from .gradium import GradiumTTSProvider
from .google_cloud import GoogleCloudTTSProvider
from .groq_proxy import GroqProxyTTSProvider
from .yourvoic import YourVoicTTSProvider


PROVIDER_REGISTRY = {
    "azure": AzureSpeechTTSProvider,
    "gradium": GradiumTTSProvider,
    "google": GoogleCloudTTSProvider,
    "groq_proxy": GroqProxyTTSProvider,
    "yourvoic": YourVoicTTSProvider,
}


def create_provider(name: str, settings: dict[str, object]):
    provider_class = PROVIDER_REGISTRY.get(name)
    if not provider_class:
        supported = ", ".join(sorted(PROVIDER_REGISTRY))
        raise ValueError(f"Unsupported provider '{name}'. Use one of: {supported}")
    return provider_class(settings)
