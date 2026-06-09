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
from tts_pipeline.section_audio import build_silence_mp3, concat_mp3_sequence, ensure_ffmpeg


DEFAULT_INPUT = "data/german_learning_sentences.md"
DEFAULT_CACHE_DIR = "artifacts/audio/yourvoic_entry_cache"
DEFAULT_OUTPUT_DIR = "artifacts/audio/yourvoic_sections"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build one YourVoic MP3 per section with repeated sentences and shadowing pauses."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Source text file.")
    parser.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR, help="Directory for cached entry MP3 files.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for final section MP3 files.")
    parser.add_argument("--section-index", type=int, default=1, help="Build only this section index.")
    parser.add_argument("--voice", default="Paul", help="YourVoic voice name.")
    parser.add_argument("--voice-gender", default="male", choices=["female", "male"], help="Voice gender fallback.")
    parser.add_argument("--repeat-count", type=int, default=2, help="How many times to repeat each sentence.")
    parser.add_argument("--pause-ms", type=int, default=5000, help="Silence after each sentence block in milliseconds.")
    parser.add_argument("--speech-speed", type=float, default=1.0, help="YourVoic speech speed.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite cached entry MP3 files and final section output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        load_dotenv(ROOT / ".env.local", override=False)
        load_dotenv(override=False)
        ensure_ffmpeg()

        entries = [e for e in parse_markdown_sentences(Path(args.input)) if e.section_index == args.section_index]
        if not entries:
            raise RuntimeError(f"No entries found for section_index={args.section_index}")

        cache_dir = Path(args.cache_dir)
        output_dir = Path(args.output_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        provider = create_provider(
            "yourvoic",
            {
                "voice_name": args.voice,
                "voice_gender": args.voice_gender,
                "audio_format": "mp3",
                "speech_speed": args.speech_speed,
            },
        )
        provider.synthesize_entries(
            entries,
            cache_dir,
            language_code="de-DE",
            requested_voice=args.voice,
            voice_gender=args.voice_gender,
            audio_format="mp3",
            overwrite=args.overwrite,
        )

        silence_path = output_dir / f"section_{args.section_index:02d}_pause.mp3"
        if args.overwrite or not silence_path.exists():
            build_silence_mp3(silence_path, args.pause_ms)

        sequence_paths: list[Path] = []
        for entry in entries:
            entry_path = cache_dir / f"{entry.stem}.mp3"
            for _ in range(args.repeat_count):
                sequence_paths.append(entry_path)
            sequence_paths.append(silence_path)

        section_slug = f"section_{args.section_index:02d}"
        output_path = output_dir / f"{section_slug}.mp3"
        concat_mp3_sequence(sequence_paths, output_path)

        manifest = {
            "provider": "yourvoic",
            "section_index": args.section_index,
            "section_title": entries[0].section,
            "entry_count": len(entries),
            "repeat_count": args.repeat_count,
            "pause_ms": args.pause_ms,
            "voice_name": args.voice,
            "speech_speed": args.speech_speed,
            "output_file": output_path.name,
            "entries": [asdict(entry) for entry in entries],
        }
        (output_dir / f"{section_slug}_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Built {output_path}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
