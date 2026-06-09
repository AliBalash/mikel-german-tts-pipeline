from pathlib import Path

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
