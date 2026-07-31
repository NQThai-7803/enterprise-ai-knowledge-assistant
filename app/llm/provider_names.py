from __future__ import annotations

OPENAI_COMPATIBLE_PROVIDER = "openai_compatible"
AZURE_OPENAI_PROVIDER = "azure_openai"
GEMINI_PROVIDER = "gemini"
ANTHROPIC_PROVIDER = "anthropic"
OLLAMA_PROVIDER = "ollama"
LM_STUDIO_PROVIDER = "lm_studio"
OPENROUTER_PROVIDER = "openrouter"

SUPPORTED_PROVIDER_NAMES = frozenset(
    {
        OPENAI_COMPATIBLE_PROVIDER,
        AZURE_OPENAI_PROVIDER,
        GEMINI_PROVIDER,
        ANTHROPIC_PROVIDER,
        OLLAMA_PROVIDER,
        LM_STUDIO_PROVIDER,
        OPENROUTER_PROVIDER,
    }
)

OPENAI_COMPATIBLE_PROVIDER_NAMES = frozenset(
    {
        OPENAI_COMPATIBLE_PROVIDER,
        OLLAMA_PROVIDER,
        LM_STUDIO_PROVIDER,
        OPENROUTER_PROVIDER,
    }
)

_PROVIDER_DISPLAY_NAMES = {
    OPENAI_COMPATIBLE_PROVIDER: "OpenAI-compatible",
    AZURE_OPENAI_PROVIDER: "Azure OpenAI",
    GEMINI_PROVIDER: "Google Gemini",
    ANTHROPIC_PROVIDER: "Anthropic Claude",
    OLLAMA_PROVIDER: "Ollama",
    LM_STUDIO_PROVIDER: "LM Studio",
    OPENROUTER_PROVIDER: "OpenRouter",
}


def normalize_provider_name(provider_name: str) -> str:
    return provider_name.strip().lower().replace("-", "_")


def provider_display_name(provider_name: str) -> str:
    normalized = normalize_provider_name(provider_name)
    return _PROVIDER_DISPLAY_NAMES.get(normalized, normalized)
