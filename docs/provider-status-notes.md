# Provider Notes

This document tracks the current implementation status and practical caveats for each supported provider.

## Implemented providers

- `gradium`
  - Native provider integration is implemented.
  - German voices `Maximilian` and `Mia` are wired in from the official voice catalog.
  - Section bundling workflow is implemented through `scripts/build_gradium_shadow_sections.py`.

- `yourvoic`
  - Native provider integration is implemented.
  - German voice listing and synthesis are supported.
  - Section bundling workflow is implemented through `scripts/build_yourvoic_shadow_sections.py`.

- `google`
  - Native Google Cloud Text-to-Speech integration is implemented.
  - Requires either Application Default Credentials or a service-account JSON file.

- `azure`
  - Native Azure Speech integration is implemented.
  - Requires a speech key plus region or endpoint.

- `groq_proxy`
  - Uses the `AliBalash/Groq_API_Proxy_Service` submodule as the local proxy layer.
  - Current public Orpheus models are not native German voices, so this path is weaker for German pronunciation.

## Not wired into the CLI

- `kokoro`
  - The upstream project is included as a submodule for future experimentation.
  - The current official Kokoro release does not document German as a first-class language in the Python pipeline.
  - The local machine currently uses Python `3.13`, while the easiest Kokoro installation path is more stable on Python `3.12`.
  - Because of that, Kokoro is kept as a research dependency for now, not as a production provider in this repository.
