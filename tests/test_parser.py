from pathlib import Path

from tts_pipeline.config import derive_dataset_slug, default_output_dir
from tts_pipeline.parser import parse_markdown_sentences


def test_parse_markdown_sentences_handles_formal_and_informal_variants(tmp_path: Path) -> None:
    source = tmp_path / "sample.md"
    source.write_text(
        "# Section One\n\n"
        "دوستانه: **Hallo, wie geht's?**\n"
        "رسمی: **Guten Tag, wie geht es Ihnen?**\n"
        "سلام، حال شما چطور است؟\n",
        encoding="utf-8",
    )

    entries = parse_markdown_sentences(source)

    assert len(entries) == 2
    assert entries[0].section_index == 1
    assert entries[0].register == "informal"
    assert entries[1].register == "formal"
    assert entries[0].persian_text == "سلام، حال شما چطور است؟"


def test_parse_markdown_sentences_raises_without_persian_line(tmp_path: Path) -> None:
    source = tmp_path / "broken.md"
    source.write_text("# Section One\n\n**Hallo.**\n", encoding="utf-8")

    try:
        parse_markdown_sentences(source)
    except ValueError as exc:
        assert "Persian translation" in str(exc)
    else:
        raise AssertionError("Expected ValueError for dangling German sentence block.")


def test_dataset_slug_uses_part_directory_name() -> None:
    input_path = Path("data/parts/part_02/sentences.md")

    dataset_slug = derive_dataset_slug(input_path)

    assert dataset_slug == "part_02"
    assert default_output_dir(Path("artifacts/audio"), "gradium", dataset_slug) == Path(
        "artifacts/audio/gradium/part_02"
    )
