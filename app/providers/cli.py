from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from app.core.config import settings
from app.providers.base import ProviderDescriptor, ProviderError, TextProvider


def _run(args: list[str], timeout: int = 180, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("NO_COLOR", "1")
    try:
        return subprocess.run(
            args,
            text=True,
            capture_output=True,
            timeout=timeout,
            cwd=str(cwd or settings.storage_dir),
            env=env,
            stdin=subprocess.DEVNULL,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args,
            returncode=124,
            stdout="",
            stderr=f"Provider command timed out after {timeout} seconds",
        )
    except OSError as exc:
        return subprocess.CompletedProcess(args, returncode=127, stdout="", stderr=str(exc))


class CodexProvider(TextProvider):
    descriptor = ProviderDescriptor(
        id="chatgpt",
        name="ChatGPT",
        icon="✦",
        kind="account",
        executable="codex",
        login_command=("codex", "login"),
        install_hint="npm install -g @openai/codex",
        login_hint="Sign in with your ChatGPT account in the official Codex login flow.",
    )

    def installed(self) -> bool:
        return shutil.which("codex") is not None

    def auth_status(self) -> tuple[bool | None, str]:
        if not self.installed():
            return False, "Codex CLI is not installed"
        p = _run(["codex", "login", "status"], timeout=15)
        text = (p.stdout + "\n" + p.stderr).strip()
        ok = p.returncode == 0 and "logged in" in text.lower() and "not logged in" not in text.lower()
        return ok, text or ("Connected" if ok else "Not connected")

    def generate(self, prompt: str, model: str | None = None) -> str:
        if not self.installed():
            raise ProviderError("Install Codex CLI first")
        args = ["codex", "exec", "--ephemeral", "--skip-git-repo-check"]
        if model:
            args += ["--model", model]
        p = _run([*args, prompt], timeout=240)
        if p.returncode != 0:
            raise ProviderError((p.stderr or p.stdout).strip() or "Codex failed")
        text = p.stdout.strip()
        if not text:
            raise ProviderError("Codex returned an empty response")
        return text


class ClaudeProvider(TextProvider):
    descriptor = ProviderDescriptor(
        id="claude",
        name="Claude",
        icon="A",
        kind="account",
        executable="claude",
        login_command=("claude", "auth", "login"),
        install_hint="npm install -g @anthropic-ai/claude-code",
        login_hint="Sign in with your Claude account (supported subscription/organization required).",
    )

    def installed(self) -> bool:
        return shutil.which("claude") is not None

    def auth_status(self) -> tuple[bool | None, str]:
        if not self.installed():
            return False, "Claude Code is not installed"
        p = _run(["claude", "auth", "status"], timeout=15)
        text = (p.stdout + "\n" + p.stderr).strip()
        lowered = text.lower()
        ok = p.returncode == 0 and ("loggedin" in lowered or "logged in" in lowered)
        if '"loggedin": false' in lowered or "not logged" in lowered:
            ok = False
        return ok, text or ("Connected" if ok else "Not connected")

    def generate(self, prompt: str, model: str | None = None) -> str:
        if not self.installed():
            raise ProviderError("Install Claude Code first")
        args = ["claude", "-p", prompt]
        if model:
            args += ["--model", model]
        p = _run(args, timeout=240)
        if p.returncode != 0:
            raise ProviderError((p.stderr or p.stdout).strip() or "Claude failed")
        text = p.stdout.strip()
        if not text:
            raise ProviderError("Claude returned an empty response")
        return text


class GeminiProvider(TextProvider):
    descriptor = ProviderDescriptor(
        id="gemini",
        name="Gemini",
        icon="◆",
        kind="account",
        executable="gemini",
        login_command=("gemini",),
        install_hint="npm install -g @google/gemini-cli",
        login_hint="Open Gemini CLI, choose Login with Google, and complete the browser sign-in.",
    )

    def installed(self) -> bool:
        return shutil.which("gemini") is not None

    def auth_status(self) -> tuple[bool | None, str]:
        if not self.installed():
            return False, "Gemini CLI is not installed"
        return None, "Installed — connection is verified on first generation"

    def generate(self, prompt: str, model: str | None = None) -> str:
        if not self.installed():
            raise ProviderError("Install Gemini CLI first")
        args = ["gemini", "-p", prompt, "--output-format", "json"]
        if model:
            args += ["--model", model]
        p = _run(args, timeout=240)
        if p.returncode != 0:
            raise ProviderError((p.stderr or p.stdout).strip() or "Gemini failed")
        raw = p.stdout.strip()
        try:
            payload = json.loads(raw)
            text = payload.get("response") or payload.get("result") or ""
        except json.JSONDecodeError:
            text = raw
        if not str(text).strip():
            raise ProviderError("Gemini returned an empty response")
        return str(text).strip()


class OllamaProvider(TextProvider):
    descriptor = ProviderDescriptor(
        id="ollama",
        name="Ollama Local",
        icon="◉",
        kind="local",
        executable="ollama",
        login_command=None,
        install_hint="Install Ollama, then pull any model you want (Qwen, DeepSeek, Llama, Mistral, etc.).",
        login_hint="No account or API key required.",
    )

    def installed(self) -> bool:
        return shutil.which("ollama") is not None

    def auth_status(self) -> tuple[bool | None, str]:
        if not self.installed():
            return False, "Ollama is not installed"
        p = _run(["ollama", "list"], timeout=20)
        ok = p.returncode == 0
        return ok, "Local runtime ready" if ok else (p.stderr.strip() or "Ollama is not running")

    def list_models(self) -> list[str]:
        if not self.installed():
            return []
        p = _run(["ollama", "list"], timeout=20)
        if p.returncode != 0:
            return []
        lines = [line.strip() for line in p.stdout.splitlines() if line.strip()]
        if len(lines) <= 1:
            return []
        return [line.split()[0] for line in lines[1:] if line.split()]

    def generate(self, prompt: str, model: str | None = None) -> str:
        if not self.installed():
            raise ProviderError("Install Ollama first")
        selected = (model or settings.default_ollama_model).strip()
        p = _run(["ollama", "run", selected, prompt], timeout=300)
        if p.returncode != 0:
            raise ProviderError((p.stderr or p.stdout).strip() or "Ollama failed")
        text = p.stdout.strip()
        if not text:
            raise ProviderError("Ollama returned an empty response")
        return text
