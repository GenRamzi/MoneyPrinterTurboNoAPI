# AI provider guide

MoneyPrinterTurbo NoAPI intentionally separates **account-based cloud providers** from **fully local models**.

## Account providers

| Provider | Adapter | Sign-in | User API key field |
|---|---|---|---|
| ChatGPT | OpenAI Codex CLI | `codex login` | No |
| Gemini | Google Gemini CLI | Google account flow inside `gemini` | No |
| Claude | Anthropic Claude Code | `claude auth login` | No |

The application calls these official command-line clients in non-interactive mode after the user completes their vendor sign-in. MoneyPrinterTurbo NoAPI does not read browser cookies or copy authentication databases.

## Local models

Ollama is the local provider. The UI reads `ollama list`, so every model installed in the user's Ollama runtime is selectable without changing this project.

Examples include compatible releases from model families such as Qwen, DeepSeek, Llama, Mistral, Gemma and others available to the user's Ollama installation.

```bash
ollama list
ollama pull qwen3:8b
```

## Why there is no generic “Sign in to every AI website” adapter

A consumer website login is not automatically a supported inference interface. Each cloud vendor controls which authenticated software, subscription, OAuth scope, endpoint, or CLI may invoke its models. This project only integrates a cloud account when there is an official client flow suitable for automation.

This avoids fragile browser automation, cookie theft patterns, hidden endpoints, CAPTCHAs, and unexpected account lockouts.

## Adding a provider

Implement `TextProvider` in `app/providers/`, then register it in `ProviderRegistry`. A provider should:

1. Use an official authentication mechanism.
2. Never ask the web UI for raw account passwords or session cookies.
3. Expose an installation check.
4. Expose a safe status check when the official client supports one.
5. Generate text non-interactively and return only useful text.
6. Keep login commands hard-coded or structured rather than accepting arbitrary shell input from the web UI.
