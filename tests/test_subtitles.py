from app.services.subtitles import split_sentences, write_srt


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
