"""Deployment profile (M1/L3), run inside the API container by check_demo.py:

    docker exec -i <project>-api-1 python - < deploy/demo/check_profile.py

Prints one JSON object: the RAG_* settings whose effective value differs from the default in this
image's code (main), and the LLM profile. No secret is read or printed.
"""

import json

from app.core.config import Settings, get_settings

settings = get_settings()
flags = [name for name in Settings.model_fields if name.startswith("rag_")]
differs = {}
for name in flags:
    field = Settings.model_fields[name]
    default = field.default_factory() if field.default_factory else field.default
    if getattr(settings, name) != default:
        differs[name.upper()] = {"value": getattr(settings, name), "default": default}
print(
    json.dumps(
        {
            "rag_flags": len(flags),
            "rag_differs": differs,
            "rag_answer_mode": settings.rag_answer_mode,
            "llm_enabled": settings.llm_enabled,
            "llm_provider": settings.llm_provider,
            "llm_ollama_model": settings.llm_ollama_model,
        },
        default=str,
    )
)
