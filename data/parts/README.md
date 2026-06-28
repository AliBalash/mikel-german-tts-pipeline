# Partitioned Datasets

Each learning batch lives in its own part folder so audio, manifests, and section builds do not overwrite each other.

## Structure

- `part_01/`
  - First 100-sentence batch
- `part_02/`
  - Second batch built from the new 100-sentence source plus 20 extra conversation sentences

## Rule

When you synthesize a part, the pipeline now writes output under:

```text
artifacts/audio/<provider>/<part_slug>/
```

Examples:

- `artifacts/audio/gradium/part_01/`
- `artifacts/audio/gradium/part_02/`

This keeps `part_01` and `part_02` fully isolated.
