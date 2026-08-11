from __future__ import annotations

from app.providers.registry import provider_registry


def build_script_prompt(topic: str, language: str, duration: int) -> str:
    words = max(45, int(duration * 2.15))
    return f"""You are a professional short-form video writer.
Create a compelling voice-over script about: {topic}
Language: {language}
Target spoken duration: about {duration} seconds (roughly {words} words).
Requirements:
- Start with a strong hook immediately.
- Use natural human phrasing, short spoken sentences, and clear progression.
- No markdown headings, no bullet labels, no scene directions, no emojis.
- Avoid unsupported factual claims.
- End with a concise memorable takeaway or call to action.
Return ONLY the narration text.
""".strip()


def generate_script(
    provider: str,
    topic: str,
    language: str,
    duration: int,
    model: str | None = None,
) -> str:
    prompt = build_script_prompt(topic, language, duration)
    return provider_registry.generate(provider, prompt, model=model).strip()
