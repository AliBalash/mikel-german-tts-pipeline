# Mikel German TTS Pipeline

A modular text-to-speech pipeline for German learning workflows. It parses bilingual sentence datasets, synthesizes sentence-level audio with multiple providers, and can build section-based shadowing tracks with repeated playback and timed pauses.

## Features

- Modular provider architecture for `Gradium`, `YourVoic`, `Google Cloud TTS`, `Azure Speech`, and `Groq Proxy`
- Sentence parser for bilingual German/Persian learning datasets
- Manifest generation for every synthesis run
- Section builders for shadowing practice with repeat and pause control
- Local configuration through `.env.local` and `tts_config.json`
- Git submodules for external provider dependencies

## Repository layout

```text
.
├── data/
│   ├── german_learning_sentences.md
│   └── custom_sentences.template.md
├── docs/
│   ├── google-cloud-setup-fa.md
│   ├── learning-method-fa.md
│   ├── project-roadmap.md
│   └── provider-status-notes.md
├── scripts/
│   ├── build_gradium_shadow_sections.py
│   ├── build_yourvoic_shadow_sections.py
│   └── run_groq_proxy.py
├── submodules/
│   ├── Groq_API_Proxy_Service/
│   └── kokoro/
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

4. List voices for a provider.

```bash
python synthesize_german_audio.py list-voices --provider gradium --language-code de-DE
```

5. Generate sentence-level audio.

```bash
python synthesize_german_audio.py synthesize --provider gradium --limit 10 --overwrite
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

Use `data/custom_sentences.template.md` as the starting template for new datasets.

## CLI usage

The main entrypoints are:

- `python synthesize_german_audio.py ...`
- `python -m tts_pipeline ...`
- `mikel-tts ...` after package install

Useful commands:

```bash
python synthesize_german_audio.py parse --provider gradium
python synthesize_german_audio.py list-voices --provider yourvoic --language-code de-DE
python synthesize_german_audio.py synthesize --provider google --limit 10 --overwrite
```

## Section builders

Gradium:

```bash
python scripts/build_gradium_shadow_sections.py --voice Maximilian --repeat-count 2 --pause-ms 5000
```

YourVoic:

```bash
python scripts/build_yourvoic_shadow_sections.py --section-index 1 --voice Paul --repeat-count 2 --pause-ms 5000
```

These builders create study tracks where each sentence is repeated and followed by silence for shadowing.

## Provider notes

- `Gradium`
  - Best current German quality in this repo.
  - Good fit for section-level shadowing tracks.
- `YourVoic`
  - Free tier is useful for quick tests, but credits are limited.
- `Google Cloud TTS`
  - Strong official option, but requires project setup and billing.
  - Persian setup guide: `docs/google-cloud-setup-fa.md`
- `Azure Speech`
  - High-quality neural voices, but requires Azure billing.
- `Groq Proxy`
  - Works through the included submodule, but current exposed Orpheus voices are not native German.
- `Kokoro`
  - Included as a research submodule only; not integrated as a production provider yet.

Full notes: `docs/provider-status-notes.md`

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
