#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tts_pipeline.parser import parse_markdown_sentences
from tts_pipeline.providers import create_provider
from tts_pipeline.config import derive_dataset_slug
from tts_pipeline.section_audio import (
    STUDY_LOUD_AUDIO_FILTER,
    convert_wav_to_mp3,
    ensure_ffmpeg,
    group_entries_by_section,
    write_wave_bundle,
)


DEFAULT_INPUT = "data/parts/part_01/sentences.md"
DEFAULT_OUTPUT_ROOT = "artifacts/audio"
DEFAULT_AUDIO_FILTER = STUDY_LOUD_AUDIO_FILTER


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build one Gradium MP3 per section with repeated sentences and shadowing pauses."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Source text file.")
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT, help="Base output root for provider and part folders.")
    parser.add_argument("--cache-dir", help="Directory for cached entry WAV files.")
    parser.add_argument("--output-dir", help="Directory for final section MP3 files.")
    parser.add_argument("--section-index", type=int, help="Build only a single section.")
    parser.add_argument("--voice", default="Mia", help="Gradium voice name.")
    parser.add_argument("--voice-gender", default="female", choices=["female", "male"], help="Voice gender fallback.")
    parser.add_argument("--repeat-count", type=int, default=3, help="How many times to repeat each sentence.")
    parser.add_argument("--pause-ms", type=int, default=5000, help="Silence after each sentence block in milliseconds.")
    parser.add_argument("--speech-speed", type=float, default=0.9, help="Gradium speech speed.")
    parser.add_argument(
        "--audio-filter",
        default=DEFAULT_AUDIO_FILTER,
        help="ffmpeg audio filter chain for the final MP3 export.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite cached WAVs and final section outputs.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        load_dotenv(ROOT / ".env.local", override=False)
        load_dotenv(override=False)
        ensure_ffmpeg()
        entries = parse_markdown_sentences(Path(args.input))
        if args.section_index is not None:
            entries = [entry for entry in entries if entry.section_index == args.section_index]
            if not entries:
                raise RuntimeError(f"No entries found for section_index={args.section_index}")
        grouped = group_entries_by_section(entries)

        dataset_slug = derive_dataset_slug(Path(args.input))
        base_dir = Path(args.output_root) / "gradium" / dataset_slug
        cache_dir = Path(args.cache_dir) if args.cache_dir else base_dir / "entry_cache"
        output_dir = Path(args.output_dir) if args.output_dir else base_dir / "sections"

        provider = create_provider(
            "gradium",
            {
                "voice_name": args.voice,
                "voice_gender": args.voice_gender,
                "audio_format": "wav",
                "speech_speed": args.speech_speed,
            },
        )
        provider.synthesize_entries(
            entries,
            cache_dir,
            language_code="de-DE",
            requested_voice=args.voice,
            voice_gender=args.voice_gender,
            audio_format="wav",
            overwrite=args.overwrite,
        )

        manifest = []
        for section_index in sorted(grouped):
            section_entries = grouped[section_index]
            section_slug = f"section_{section_index:02d}"
            wav_path = output_dir / f"{section_slug}.wav"
            mp3_path = output_dir / f"{section_slug}.mp3"
            write_wave_bundle(
                section_entries=section_entries,
                cache_dir=cache_dir,
                wav_path=wav_path,
                repeat_count=args.repeat_count,
                pause_ms=args.pause_ms,
            )
            convert_wav_to_mp3(wav_path, mp3_path, audio_filter=args.audio_filter)
            manifest.append(
                {
                    "dataset_slug": dataset_slug,
                    "section_index": section_index,
                    "section_title": section_entries[0].section,
                    "entry_count": len(section_entries),
                    "repeat_count": args.repeat_count,
                    "pause_ms": args.pause_ms,
                    "voice_name": args.voice,
                    "speech_speed": args.speech_speed,
                    "audio_filter": args.audio_filter,
                    "mp3_file": mp3_path.name,
                    "wav_file": wav_path.name,
                    "entries": [asdict(entry) for entry in section_entries],
                }
            )

        (output_dir / "sections_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Built {len(manifest)} section MP3 files in {output_dir}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
