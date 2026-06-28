from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import DEFAULT_CONFIG_PATH, resolve_config
from .parser import parse_markdown_sentences, write_manifest
from .providers import create_provider


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to JSON config file.")
    parser.add_argument("--provider", choices=["gradium"], help="TTS provider.")
    parser.add_argument("--input", help="Source markdown/text file.")
    parser.add_argument("--output-root", help="Base output directory. Provider subfolders are created under this path.")
    parser.add_argument("--output-dir", help="Explicit output directory override.")
    parser.add_argument("--manifest", help="Explicit manifest path override.")
    parser.add_argument("--manifest-name", help="Manifest filename inside the provider output dir.")
    parser.add_argument("--language-code", help="Language code, for example de-DE.")
    parser.add_argument("--voice", help="Explicit provider voice name.")
    parser.add_argument("--voice-gender", choices=["female", "male"], help="Fallback gender for auto voice selection.")
    parser.add_argument("--audio-format", help="Friendly format name: mp3, wav, or ogg.")
    parser.add_argument("--limit", type=int, help="Limit synthesis/manifest to the first N sentence items.")
    parser.add_argument("--section-index", type=int, help="Keep only one parsed section index.")
    parser.add_argument("--item-number", type=int, help="Keep only one item number within the dataset.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing audio files.")


def build_subcommand_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse German learning sentences and synthesize audio via modular TTS providers."
    )
    subparsers = parser.add_subparsers(dest="command")

    parse_parser = subparsers.add_parser("parse", help="Parse the text file and write only the manifest.")
    add_common_arguments(parse_parser)

    voices_parser = subparsers.add_parser("list-voices", help="List voices available for the selected provider.")
    add_common_arguments(voices_parser)

    synth_parser = subparsers.add_parser("synthesize", help="Generate audio files and manifest.")
    add_common_arguments(synth_parser)

    return parser


def build_legacy_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backwards-compatible wrapper around the modular TTS pipeline."
    )
    add_common_arguments(parser)
    parser.add_argument("--dry-run", action="store_true", help="Parse the file and write only the manifest.")
    parser.add_argument("--list-voices", action="store_true", help="List voices for the selected provider.")
    return parser


def command_from_legacy_args(args) -> str:
    if args.list_voices:
        return "list-voices"
    if args.dry_run:
        return "parse"
    return "synthesize"


def filter_entries(entries, args):
    if args.section_index is not None:
        entries = [entry for entry in entries if entry.section_index == args.section_index]
    if args.item_number is not None:
        entries = [entry for entry in entries if entry.item_number == args.item_number]
    if args.limit:
        entries = entries[: args.limit]
    if not entries:
        raise ValueError("No sentence entries matched the selected filters.")
    return entries


def run_parse(args) -> int:
    resolved = resolve_config(args)
    entries = parse_markdown_sentences(resolved.input_path)
    entries = filter_entries(entries, args)
    write_manifest(
        entries,
        resolved.manifest_path,
        dataset_slug=resolved.dataset_slug,
        provider_name=resolved.provider_name,
    )
    print(f"Parsed {len(entries)} entries from {resolved.input_path} and wrote {resolved.manifest_path}")
    return 0


def run_list_voices(args) -> int:
    resolved = resolve_config(args)
    provider = create_provider(resolved.provider_name, resolved.provider_settings)
    for voice_name in provider.list_voices(resolved.language_code):
        print(voice_name)
    return 0


def run_synthesize(args) -> int:
    resolved = resolve_config(args)
    entries = parse_markdown_sentences(resolved.input_path)
    entries = filter_entries(entries, args)
    provider = create_provider(resolved.provider_name, resolved.provider_settings)
    voice_name, file_extension = provider.synthesize_entries(
        entries,
        resolved.output_dir,
        language_code=resolved.language_code,
        requested_voice=resolved.voice_name,
        voice_gender=resolved.voice_gender,
        audio_format=resolved.audio_format,
        overwrite=args.overwrite,
    )
    write_manifest(
        entries,
        resolved.manifest_path,
        dataset_slug=resolved.dataset_slug,
        provider_name=resolved.provider_name,
        voice_name=voice_name,
        file_extension=file_extension,
    )
    print(
        f"Generated {len(entries)} audio files in {resolved.output_dir} "
        f"with provider {resolved.provider_name} and voice {voice_name}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if argv and argv[0] in {"parse", "list-voices", "synthesize"}:
            parser = build_subcommand_parser()
            args = parser.parse_args(argv)
            command = args.command
        else:
            parser = build_legacy_parser()
            args = parser.parse_args(argv)
            command = command_from_legacy_args(args)

        if command == "parse":
            return run_parse(args)
        if command == "list-voices":
            return run_list_voices(args)
        return run_synthesize(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
