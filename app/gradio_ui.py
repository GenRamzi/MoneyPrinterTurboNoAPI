from __future__ import annotations

import html
import re
import shutil
import uuid
from pathlib import Path

import gradio as gr

from app.api import VOICES
from app.core.config import settings
from app.models.schemas import GenerateRequest, TaskInfo
from app.providers.registry import provider_registry
from app.services.gpu import gpu_status
from app.services.script import generate_script
from app.services.subtitle_templates import apply_template, list_templates
from app.services.tasks import task_manager
from app.services.tts import synthesize


VOICE_CHOICES = [(voice["name"], voice["id"]) for voice in VOICES]
TEMPLATE_CHOICES = [
    (f"{template['name']} — {template['description']}", template["id"])
    for template in list_templates()
]
GRADIO_CSS = """
.gradio-container { max-width: 1440px !important; }
.hero { border-radius: 18px; padding: 18px; background: linear-gradient(135deg,#17152b,#101318); }
.muted { color: #7f8797; }
"""


def _provider_choices() -> list[tuple[str, str]]:
    providers = provider_registry.list()
    return [(provider.name, provider.id) for provider in providers]


def _as_paths(value: str | list[str] | None) -> list[Path]:
    if not value:
        return []
    values = value if isinstance(value, list) else [value]
    return [Path(item) for item in values if item]


def _save_uploads(value: str | list[str] | None) -> list[str]:
    saved: list[str] = []
    for source in _as_paths(value):
        if not source.is_file():
            continue
        suffix = source.suffix.lower()
        target = settings.uploads_dir / f"{uuid.uuid4().hex}{suffix}"
        shutil.copyfile(source, target)
        saved.append(target.name)
    return saved


def _task_files(task: TaskInfo) -> list[str]:
    folder = settings.tasks_dir / task.id
    names = [*task.output_files, *task.artifact_files]
    return [str(folder / name) for name in names if (folder / name).is_file()]


def preview_script(topic: str, provider: str, model: str | None, language: str, duration: int):
    if not topic or len(topic.strip()) < 2:
        return "", "اكتب موضوع الفيديو أولاً."
    try:
        script = generate_script(
            provider,
            topic.strip(),
            language,
            int(duration),
            model=model if provider == "ollama" else None,
        )
        words = len(script.split())
        return script, f"{words} كلمة · مدة صوتية تقريبية {max(1, round(words / 2.15))} ثانية"
    except Exception as exc:
        return "", f"تعذر توليد النص: {exc}"


def preview_voice(text: str, voice: str):
    text = (text or "").strip()[:220] or "مرحباً بك في MoneyPrinterTurbo NoAPI"
    path = settings.uploads_dir / f"gradio-preview-{uuid.uuid4().hex}.mp3"
    try:
        synthesize(text, voice, path)
        return str(path)
    except Exception as exc:
        raise gr.Error(f"تعذر إنشاء معاينة الصوت: {exc}") from exc


def create_task(
    topic: str,
    provider: str,
    ollama_model: str,
    language: str,
    duration: int,
    clip_duration: float,
    aspect_ratio: str,
    voice: str,
    script: str,
    subtitles: bool,
    subtitle_format: str,
    subtitle_position: str,
    subtitle_font_size: int,
    subtitle_color: str,
    subtitle_outline_color: str,
    subtitle_template: str,
    subtitle_outline_width: int,
    subtitle_font_name: str,
    gpu_backend: str,
    materials: str | list[str] | None,
    bgm: str | list[str] | None,
    bgm_volume: float,
    batch_count: int,
):
    if not topic or len(topic.strip()) < 2:
        raise gr.Error("موضوع الفيديو مطلوب.")
    material_ids = _save_uploads(materials)
    bgm_ids = _save_uploads(bgm)
    request = GenerateRequest(
        topic=topic.strip(),
        provider=provider,
        ollama_model=ollama_model or None,
        language=language,
        script=script.strip() or None,
        duration=int(duration),
        clip_duration=float(clip_duration),
        aspect_ratio=aspect_ratio,
        voice=voice,
        subtitles=bool(subtitles),
        subtitle_template=subtitle_template,
        subtitle_format=subtitle_format,
        subtitle_position=subtitle_position,
        subtitle_font_size=int(subtitle_font_size),
        subtitle_color=subtitle_color,
        subtitle_outline_color=subtitle_outline_color,
        subtitle_outline_width=int(subtitle_outline_width),
        subtitle_font_name=subtitle_font_name or "Arial",
        gpu_backend=gpu_backend,
        material_ids=material_ids,
        bgm_id=bgm_ids[0] if bgm_ids else None,
        bgm_volume=float(bgm_volume),
        batch_count=int(batch_count),
    )
    try:
        task = task_manager.create(request)
    except Exception as exc:
        raise gr.Error(f"تعذر بدء المهمة: {exc}") from exc
    return task.id, f"بدأت المهمة {task.id[:8]} باستخدام {gpu_backend.upper()}"


def poll_task(task_id: str):
    if not task_id:
        return 0, "لا توجد مهمة نشطة", None, []
    task = task_manager.get(task_id)
    if not task:
        return 0, "المهمة غير موجودة", None, []
    status = task.message
    if task.error:
        status = f"{status}: {task.error}"
    files = _task_files(task) if task.state.value == "completed" else []
    video = next((path for path in files if path.endswith(".mp4")), None)
    return task.progress, f"{task.state.value}: {status}", video, files


def _safe_color(value: str, fallback: str) -> str:
    return value if re.fullmatch(r"#[0-9A-Fa-f]{6}", value or "") else fallback


def preview_subtitle(
    text: str,
    position: str,
    font_name: str,
    font_size: int,
    text_color: str,
    outline_color: str,
    outline_width: int,
) -> str:
    safe_text = html.escape((text or "معاينة الترجمة العربية والإنجليزية").strip())
    safe_font = html.escape((font_name or "Arial").strip())
    color = _safe_color(text_color, "#FFFFFF")
    outline = _safe_color(outline_color, "#000000")
    size = max(12, min(64, int(font_size or 22)))
    width = max(0, min(8, int(outline_width or 0)))
    shadows = ", ".join(
        f"{dx}px {dy}px 0 {outline}"
        for dx in range(-width, width + 1)
        for dy in range(-width, width + 1)
        if dx or dy
    ) or "none"
    justify = {"top": "flex-start", "center": "center", "bottom": "flex-end"}.get(position, "flex-end")
    return (
        '<div style="height:260px;border-radius:16px;padding:20px;display:flex;'
        f'align-items:{justify};justify-content:center;background:linear-gradient(135deg,#111827,#312e81);">'
        f'<div dir="auto" style="max-width:90%;font-family:{safe_font};font-size:{size}px;'
        f'line-height:1.25;text-align:center;color:{color};text-shadow:{shadows};">{safe_text}</div></div>'
    )


def apply_subtitle_template(template_id: str, preview_text: str = ""):
    try:
        values = apply_template(template_id)
    except ValueError as exc:
        raise gr.Error(str(exc)) from exc
    info = f"**{template_id}** applied · {values['subtitle_format'].upper()} · {values['subtitle_position']}"
    return (
        values["subtitles"],
        values["subtitle_format"],
        values["subtitle_position"],
        values["subtitle_font_name"],
        values["subtitle_font_size"],
        values["subtitle_color"],
        values["subtitle_outline_color"],
        values["subtitle_outline_width"],
        info,
        preview_subtitle(
            preview_text,
            values["subtitle_position"],
            values["subtitle_font_name"],
            values["subtitle_font_size"],
            values["subtitle_color"],
            values["subtitle_outline_color"],
            values["subtitle_outline_width"],
        ),
    )


def cancel_task(task_id: str):
    if not task_id:
        return "لا توجد مهمة لإلغائها"
    task = task_manager.cancel(task_id)
    return "تعذر العثور على المهمة" if not task else f"حالة المهمة: {task.state.value}"


def build_demo() -> gr.Blocks:
    providers = _provider_choices()
    default_provider = providers[0][1] if providers else "gemini"
    current_gpu = gpu_status()

    with gr.Blocks(title="MoneyPrinterTurbo NoAPI Studio") as demo:
        gr.Markdown("# MoneyPrinterTurbo NoAPI Studio\nواجهة متقدمة لإنشاء فيديوهات قصيرة مع ASS وGPU اختياري.", elem_classes=["hero"])
        with gr.Row():
            with gr.Column(scale=2):
                topic = gr.Textbox(label="موضوع الفيديو", lines=3, placeholder="مثال: كيف تبني عادة قراءة يومية؟")
                with gr.Row():
                    provider = gr.Dropdown(choices=providers, value=default_provider, label="مزوّد النص")
                    ollama_model = gr.Textbox(label="نموذج Ollama", value=settings.default_ollama_model)
                with gr.Row():
                    language = gr.Dropdown(["Arabic", "English", "French", "Spanish", "German", "Turkish"], value="Arabic", label="اللغة")
                    duration = gr.Slider(10, 600, value=45, step=1, label="المدة المستهدفة (ثانية)")
                with gr.Row():
                    clip_duration = gr.Slider(1, 15, value=4, step=0.5, label="مدة اللقطة")
                    aspect_ratio = gr.Dropdown(["9:16", "16:9", "1:1"], value="9:16", label="المقاس")
                    batch_count = gr.Slider(1, 4, value=1, step=1, label="عدد النسخ")
                script = gr.Textbox(label="النص الصوتي", lines=8, placeholder="اتركه فارغًا ليتم توليده تلقائيًا")
                script_meta = gr.Markdown("", elem_classes=["muted"])
                with gr.Row():
                    script_button = gr.Button("اقتراح نص", variant="secondary")
                    voice = gr.Dropdown(choices=VOICE_CHOICES, value=VOICE_CHOICES[0][1], label="الصوت")
                    voice_button = gr.Button("معاينة الصوت", variant="secondary")
                voice_audio = gr.Audio(label="معاينة الصوت", type="filepath")
            with gr.Column(scale=1):
                gr.Markdown("### التسريع والمعالجة")
                gpu_backend = gr.Dropdown(
                    choices=[("تلقائي", "auto"), ("CPU", "cpu"), ("NVIDIA NVENC", "nvenc"), ("VAAPI", "vaapi"), ("Intel QSV", "qsv")],
                    value="auto",
                    label="Encoder",
                )
                gpu_info = gr.JSON(value=current_gpu, label="حالة GPU / FFmpeg")
                refresh_gpu = gr.Button("تحديث حالة GPU")
                gr.Markdown("### الترجمة")
                subtitle_template = gr.Dropdown(choices=TEMPLATE_CHOICES, value="creator", label="قالب جاهز")
                apply_template_button = gr.Button("تطبيق القالب", variant="secondary")
                template_info = gr.Markdown("اختر قالبًا واضغط تطبيق القالب.", elem_classes=["muted"])
                preview_text = gr.Textbox(value="تعلم بسرعة مع ترجمة واضحة", lines=2, label="نص المعاينة الحية")
                subtitles = gr.Checkbox(value=True, label="تضمين الترجمة")
                subtitle_format = gr.Radio(["ass", "srt"], value="ass", label="التنسيق")
                subtitle_position = gr.Dropdown(["bottom", "center", "top"], value="bottom", label="الموضع")
                subtitle_font_name = gr.Textbox(value="Arial", label="اسم الخط")
                with gr.Row():
                    subtitle_font_size = gr.Slider(12, 64, value=22, step=1, label="حجم الخط")
                    subtitle_outline_width = gr.Slider(0, 8, value=2, step=1, label="الإطار")
                with gr.Row():
                    subtitle_color = gr.Textbox(value="#FFFFFF", label="لون النص")
                    subtitle_outline_color = gr.Textbox(value="#000000", label="لون الإطار")
                subtitle_preview = gr.HTML(
                    preview_subtitle("تعلم بسرعة مع ترجمة واضحة", "bottom", "Arial", 22, "#FFFFFF", "#000000", 2),
                    label="معاينة حية",
                )
        with gr.Row():
            materials = gr.File(file_count="multiple", file_types=[".mp4", ".mov", ".mkv", ".webm", ".jpg", ".jpeg", ".png", ".webp"], type="filepath", label="صور وفيديوهات")
            bgm = gr.File(file_count="single", file_types=[".mp3", ".wav", ".m4a", ".aac", ".ogg"], type="filepath", label="موسيقى خلفية")
            bgm_volume = gr.Slider(0, 1, value=0.12, step=0.01, label="مستوى الموسيقى")
        create_button = gr.Button("إنشاء الفيديو", variant="primary")
        task_id = gr.Textbox(label="معرّف المهمة", visible=False)
        task_status = gr.Markdown("جاهز للإنشاء")
        progress = gr.Slider(0, 100, value=0, step=1, label="التقدم", interactive=False)
        cancel_button = gr.Button("إلغاء المهمة", variant="stop")
        result_video = gr.Video(label="المعاينة", autoplay=False)
        result_files = gr.Files(label="النتائج والملفات المساندة", file_count="multiple")
        timer = gr.Timer(2)

        script_button.click(
            preview_script,
            inputs=[topic, provider, ollama_model, language, duration],
            outputs=[script, script_meta],
        )
        voice_button.click(preview_voice, inputs=[script, voice], outputs=voice_audio)
        refresh_gpu.click(gpu_status, outputs=gpu_info)
        apply_template_button.click(
            apply_subtitle_template,
            inputs=[subtitle_template, preview_text],
            outputs=[subtitles, subtitle_format, subtitle_position, subtitle_font_name, subtitle_font_size, subtitle_color, subtitle_outline_color, subtitle_outline_width, template_info, subtitle_preview],
        )
        for live_component in [preview_text, subtitle_position, subtitle_font_name, subtitle_font_size, subtitle_color, subtitle_outline_color, subtitle_outline_width]:
            live_component.change(
                preview_subtitle,
                inputs=[preview_text, subtitle_position, subtitle_font_name, subtitle_font_size, subtitle_color, subtitle_outline_color, subtitle_outline_width],
                outputs=subtitle_preview,
            )
        create_button.click(
            create_task,
            inputs=[
                topic, provider, ollama_model, language, duration, clip_duration, aspect_ratio, voice,
                script, subtitles, subtitle_format, subtitle_position, subtitle_font_size,                 subtitle_color, subtitle_outline_color, subtitle_template, subtitle_outline_width, subtitle_font_name, gpu_backend, materials,

                bgm, bgm_volume, batch_count,
            ],
            outputs=[task_id, task_status],
        )
        cancel_button.click(cancel_task, inputs=task_id, outputs=task_status)
        timer.tick(poll_task, inputs=task_id, outputs=[progress, task_status, result_video, result_files])
    return demo
