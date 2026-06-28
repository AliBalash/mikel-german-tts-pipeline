from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


DEFAULT_INPUT = "data/parts/part_01/sentences.md"
DEFAULT_OUTPUT_ROOT = "artifacts/audio"
DEFAULT_MANIFEST_NAME = "manifest.json"
DEFAULT_CONFIG_PATH = "tts_config.json"
DEFAULT_PROVIDER = "gradium"


@dataclass
class ResolvedConfig:
    config_path: Path
    provider_name: str
    input_path: Path
    dataset_slug: str
    output_dir: Path
    manifest_path: Path
    language_code: str
    voice_name: str | None
    voice_gender: str
    audio_format: str
    provider_settings: dict[str, Any]


def load_config_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def sanitize_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip()).strip("_").lower()
    return slug or "dataset"


def derive_dataset_slug(input_path: Path) -> str:
    for parent in input_path.parents:
        parent_name = parent.name.strip()
        if re.fullmatch(r"part[_-]?\d+", parent_name, flags=re.IGNORECASE):
            return sanitize_slug(parent_name)
    return sanitize_slug(input_path.stem)


def default_output_dir(output_root: Path, provider_name: str, dataset_slug: str) -> Path:
    return output_root / provider_name / dataset_slug


def resolve_config(args) -> ResolvedConfig:
    load_dotenv(".env.local", override=False)
    load_dotenv(override=False)
    config_path = Path(args.config or DEFAULT_CONFIG_PATH)
    raw_config = load_config_file(config_path)
    defaults = raw_config.get("defaults", {})
    providers = raw_config.get("providers", {})

    provider_name = args.provider or defaults.get("provider") or DEFAULT_PROVIDER
    provider_settings = dict(providers.get(provider_name, {}))

    input_path = Path(args.input or defaults.get("input") or DEFAULT_INPUT)
    dataset_slug = derive_dataset_slug(input_path)
    output_root = Path(args.output_root or defaults.get("output_root") or DEFAULT_OUTPUT_ROOT)
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else default_output_dir(output_root, provider_name, dataset_slug)
    )
    manifest_name = args.manifest_name or defaults.get("manifest_name") or DEFAULT_MANIFEST_NAME
    manifest_path = Path(args.manifest) if args.manifest else output_dir / manifest_name

    return ResolvedConfig(
        config_path=config_path,
        provider_name=provider_name,
        input_path=input_path,
        dataset_slug=dataset_slug,
        output_dir=output_dir,
        manifest_path=manifest_path,
        language_code=args.language_code or defaults.get("language_code") or "de-DE",
        voice_name=args.voice or provider_settings.get("voice_name"),
        voice_gender=args.voice_gender or provider_settings.get("voice_gender") or "female",
        audio_format=(args.audio_format or provider_settings.get("audio_format") or "mp3").lower(),
        provider_settings=provider_settings,
    )


def env_or_value(value: str | None, *env_names: str) -> str | None:
    if value:
        return value
    for env_name in env_names:
        env_value = os.environ.get(env_name)
        if env_value:
            return env_value
    return None
