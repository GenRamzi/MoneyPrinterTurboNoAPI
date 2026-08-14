from app.services.subtitles import split_sentences, write_ass, write_srt


def test_split_sentences_supports_arabic_question_mark():
    assert split_sentences("مرحبا بالعالم. كيف حالك؟ ممتاز!") == [
        "مرحبا بالعالم.",
        "كيف حالك؟",
        "ممتاز!",
    ]


def test_write_srt_ends_at_duration(tmp_path):
    path = write_srt("One sentence. Another sentence.", 10.0, tmp_path / "captions.srt")
    content = path.read_text(encoding="utf-8")
    assert "00:00:10,000" in content
    assert content.count(" --> ") == 2


def test_write_ass_contains_custom_style_and_events(tmp_path):
    path = write_ass(
        "مرحبا بالعالم. كيف حالك؟",
        10.0,
        tmp_path / "captions.ass",
        position="center",
        font_size=30,
        text_color="#00FF00",
        outline_color="#111111",
        outline_width=3,
        font_name="Arial",
    )
    content = path.read_text(encoding="utf-8-sig")
    assert "PlayResX: 1080" in content
    assert "Format: Name, Fontname, Fontsize" in content
    assert "Style: Default,Arial,30" in content
    assert "&H0000FF00" in content
    assert "[Events]" in content
    assert content.count("Dialogue: ") == 2
