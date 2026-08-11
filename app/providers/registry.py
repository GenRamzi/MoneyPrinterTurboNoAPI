from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import asdict

from app.models.schemas import ProviderInfo
from app.providers.base import ProviderError, TextProvider
from app.providers.cli import ClaudeProvider, CodexProvider, GeminiProvider, OllamaProvider


class ProviderRegistry:
    def __init__(self) -> None:
        providers: list[TextProvider] = [CodexProvider(), GeminiProvider(), ClaudeProvider(), OllamaProvider()]
        self._providers = {provider.descriptor.id: provider for provider in providers}

    def get(self, provider_id: str) -> TextProvider:
        provider = self._providers.get(provider_id)
        if not provider:
            raise ProviderError(f"Unknown provider: {provider_id}")
        return provider

    def list(self) -> list[ProviderInfo]:
        result: list[ProviderInfo] = []
        for provider in self._providers.values():
            d = provider.descriptor
            installed = provider.installed()
            authenticated, status = provider.auth_status() if installed else (False, f"{d.name} is not installed")
            result.append(
                ProviderInfo(
                    id=d.id,
                    name=d.name,
                    icon=d.icon,
                    kind=d.kind,
                    installed=installed,
                    authenticated=authenticated,
                    status=status[:400],
                    login_hint=d.login_hint,
                    install_hint=d.install_hint,
                )
            )
        return result

    def generate(self, provider_id: str, prompt: str) -> str:
        return self.get(provider_id).generate(prompt)

    def open_login(self, provider_id: str) -> str:
        provider = self.get(provider_id)
        command = provider.descriptor.login_command
        if not command:
            return provider.descriptor.login_hint
        if not provider.installed():
            return provider.descriptor.install_hint

        system = platform.system().lower()
        cmd_text = " ".join(command)
        try:
            if system == "windows":
                subprocess.Popen(["cmd.exe", "/c", "start", "", "cmd.exe", "/k", cmd_text])
            elif system == "darwin":
                escaped = cmd_text.replace('"', '\\"')
                subprocess.Popen(["osascript", "-e", f'tell application "Terminal" to do script "{escaped}"'])
            else:
                terminal = shutil.which("x-terminal-emulator") or shutil.which("gnome-terminal") or shutil.which("konsole")
                if not terminal:
                    return f"Run this command in a terminal: {cmd_text}"
                if terminal.endswith("gnome-terminal"):
                    subprocess.Popen([terminal, "--", "bash", "-lc", f"{cmd_text}; exec bash"])
                else:
                    subprocess.Popen([terminal, "-e", "bash", "-lc", f"{cmd_text}; exec bash"])
        except Exception:
            return f"Run this command in a terminal: {cmd_text}"
        return f"Login opened. Complete the sign-in flow, then refresh provider status. Command: {cmd_text}"


provider_registry = ProviderRegistry()
