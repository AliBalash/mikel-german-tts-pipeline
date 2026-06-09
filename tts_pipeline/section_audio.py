from __future__ import annotations

import subprocess
import wave
from collections import defaultdict
from pathlib import Path

from .models import SentenceEntry


def ensure_ffmpeg() -> None:
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, text=True)
    except Exception as exc:
        raise RuntimeError("ffmpeg is required for section audio bundling.") from exc


def group_entries_by_section(entries: list[SentenceEntry]) -> dict[int, list[SentenceEntry]]:
    grouped: dict[int, list[SentenceEntry]] = defaultdict(list)
    for entry in entries:
        grouped[entry.section_index].append(entry)
    return dict(grouped)


def write_wave_bundle(
    *,
    section_entries: list[SentenceEntry],
    cache_dir: Path,
    wav_path: Path,
    repeat_count: int,
    pause_ms: int,
) -> None:
    if not section_entries:
        raise ValueError("Section has no entries.")

    first_path = cache_dir / f"{section_entries[0].stem}.wav"
    with wave.open(str(first_path), "rb") as first_wav:
        params = first_wav.getparams()
        silence_frames = int(params.framerate * pause_ms / 1000)
        silence_bytes = b"\x00" * silence_frames * params.sampwidth * params.nchannels

    wav_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(wav_path), "wb") as out_wav:
        out_wav.setnchannels(params.nchannels)
        out_wav.setsampwidth(params.sampwidth)
        out_wav.setframerate(params.framerate)
        out_wav.setcomptype(params.comptype, params.compname)
        for entry in section_entries:
            entry_path = cache_dir / f"{entry.stem}.wav"
            with wave.open(str(entry_path), "rb") as entry_wav:
                entry_params = entry_wav.getparams()
                if (
                    entry_params.nchannels != params.nchannels
                    or entry_params.sampwidth != params.sampwidth
                    or entry_params.framerate != params.framerate
                    or entry_params.comptype != params.comptype
                ):
                    raise RuntimeError(
                        f"Audio format mismatch for {entry_path.name}: expected "
                        f"{(params.nchannels, params.sampwidth, params.framerate, params.comptype)}, got "
                        f"{(entry_params.nchannels, entry_params.sampwidth, entry_params.framerate, entry_params.comptype)}"
                    )
                audio_frames = entry_wav.readframes(entry_wav.getnframes())
            for _ in range(repeat_count):
                out_wav.writeframes(audio_frames)
            out_wav.writeframes(silence_bytes)


def convert_wav_to_mp3(wav_path: Path, mp3_path: Path) -> None:
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(wav_path),
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(mp3_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed for {wav_path.name}: {result.stderr[:500]}")


def build_silence_mp3(path: Path, pause_ms: int) -> None:
    duration_sec = max(0.1, pause_ms / 1000)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=24000:cl=mono",
        "-t",
        f"{duration_sec:.3f}",
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg silence generation failed: {result.stderr[:500]}")


def concat_mp3_sequence(sequence_paths: list[Path], output_path: Path) -> None:
    concat_file = output_path.with_suffix(".concat.txt")
    concat_file.write_text(
        "".join(f"file '{path.resolve()}'\n" for path in sequence_paths),
        encoding="utf-8",
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    concat_file.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed for {output_path.name}: {result.stderr[:500]}")
