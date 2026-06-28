from __future__ import annotations

from .gradium import GradiumTTSProvider


PROVIDER_REGISTRY = {
    "gradium": GradiumTTSProvider,
}


def create_provider(name: str, settings: dict[str, object]):
    provider_class = PROVIDER_REGISTRY.get(name)
    if not provider_class:
        supported = ", ".join(sorted(PROVIDER_REGISTRY))
        raise ValueError(f"Unsupported provider '{name}'. Use one of: {supported}")
    return provider_class(settings)
