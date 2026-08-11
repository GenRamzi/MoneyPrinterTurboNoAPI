from app.services.script import build_script_prompt


def test_prompt_contains_topic_language_and_duration():
    prompt = build_script_prompt("Focus habits", "Arabic", 45)
    assert "Focus habits" in prompt
    assert "Arabic" in prompt
    assert "45 seconds" in prompt
    assert "Return ONLY" in prompt
