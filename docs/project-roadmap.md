# Roadmap

## Near term

- Add a unified `build-sections` CLI entrypoint so provider-specific builder scripts become optional.
- Add manifest validation and dataset linting before synthesis.
- Add smoke tests around provider configuration errors.

## Medium term

- Add resumable long-running section builds with progress checkpoints.
- Add configurable pause patterns for shadowing practice.
- Add optional bilingual cue tracks where Persian prompts are inserted before German playback.

## Research

- Revisit Kokoro once a reproducible German path is available locally.
- Compare section-level output quality across Gradium, YourVoic, Google, and Azure under the same pacing rules.
