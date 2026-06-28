# Mikel German TTS Pipeline

A Gradium-focused German learning TTS pipeline. It keeps each sentence batch in its own part folder, generates sentence audio, and builds section-based shadowing tracks with repeated playback and fixed pauses.

## Features

- Gradium-only workflow, trimmed to the provider that is actually in use
- Partitioned datasets: `part_01`, `part_02`, and future parts
- Manifest generation for every parse and synthesis run
- Section builder for shadowing practice
- Stronger final MP3 loudness profile for study playback

## Repository layout

```text
.
├── data/
│   ├── parts/
│   │   ├── part_01/
│   │   └── part_02/
│   └── custom_sentences.template.md
├── docs/
│   └── learning-method-fa.md
├── scripts/
│   └── build_gradium_shadow_sections.py
├── tests/
├── tts_pipeline/
├── .env.local.example
├── pyproject.toml
├── requirements.txt
├── synthesize_german_audio.py
└── tts_config.example.json
```

## Quick start

1. Create a virtual environment and install dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

2. Create your local environment file.

```bash
cp .env.local.example .env.local
```

3. Create a local config file.

```bash
cp tts_config.example.json tts_config.json
```

4. List available Gradium voices.

```bash
python synthesize_german_audio.py list-voices --provider gradium --language-code de-DE
```

5. Generate sentence-level audio.

```bash
python synthesize_german_audio.py synthesize --provider gradium --input data/parts/part_01/sentences.md --limit 10 --overwrite
```

## Dataset format

The parser expects a Markdown-like structure:

```md
# Section title

**Neutral German sentence.**
جمله فارسی

دوستانه: **Informal German sentence.**
رسمی: **Formal German sentence.**
جمله فارسی
```

Use `data/custom_sentences.template.md` as the starting template for new datasets, then place each batch under its own `data/parts/part_xx/` folder.

## CLI usage

Useful commands:

```bash
python synthesize_german_audio.py parse --provider gradium --input data/parts/part_02/sentences.md
python synthesize_german_audio.py list-voices --provider gradium --language-code de-DE
python synthesize_german_audio.py synthesize --provider gradium --input data/parts/part_02/sentences.md --section-index 1 --item-number 1 --overwrite
```

By default, outputs are now isolated by provider and part:

```text
artifacts/audio/<provider>/<part_slug>/
```

Examples:

- `artifacts/audio/gradium/part_01/`
- `artifacts/audio/gradium/part_02/`

## Section builder

```bash
python scripts/build_gradium_shadow_sections.py --input data/parts/part_02/sentences.md --voice Mia --repeat-count 3 --pause-ms 5000 --overwrite
```

This builder creates study tracks where each sentence is repeated three times and followed by a five-second pause.

## Configuration

Runtime configuration comes from three places:

1. CLI flags
2. `tts_config.json`
3. `.env.local`

Defaults are defined in `tts_config.example.json`.

## Development

Run tests:

```bash
source .venv/bin/activate
pytest
```

Check that the package imports cleanly:

```bash
python -m compileall tts_pipeline scripts
```

## Notes

- Generated audio is intentionally ignored by git.
- Secrets stay in `.env.local` and must never be committed.
- The old `output_audio/` path is still ignored for backward compatibility, but new runs default to `artifacts/audio/`.
- Partitioned datasets live under `data/parts/`, and each part writes to its own output subtree automatically.
