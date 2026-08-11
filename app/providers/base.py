from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderDescriptor:
    id: str
    name: str
    icon: str
    kind: str
    executable: str
    login_command: tuple[str, ...] | None
    install_hint: str
    login_hint: str


class ProviderError(RuntimeError):
    pass


class TextProvider(ABC):
    descriptor: ProviderDescriptor

    @abstractmethod
    def installed(self) -> bool: ...

    @abstractmethod
    def auth_status(self) -> tuple[bool | None, str]: ...

    @abstractmethod
    def generate(self, prompt: str) -> str: ...
