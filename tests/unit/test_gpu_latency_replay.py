"""gpu_latency_replay.py: prompts rebuilt as the simple path builds them, time per question."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.llm.models import LLMGenerationResult
from app.services.grounded_answer_service import SIMPLE_RETRY_INSTRUCTIONS
from scripts.eval import gpu_latency_replay as replay

SOURCE = {"label": "SOURCE_1", "title": "Quy dinh", "pages": [3], "text": "Tai trong 2.500 kg."}
FIRST = {"asked": "Tai trong?", "question": "Tai trong?", "attempt": 1, "draft": "2.500 kg.",
         "outcome": "citation_missing", "sources": [SOURCE]}  # fmt: skip
SECOND = {**FIRST, "attempt": 2, "draft": "2.500 kg [SOURCE_1].", "outcome": "answered"}


def test_a_retry_prompt_carries_the_reason_and_the_first_draft() -> None:
    settings = replay.eval_settings("http://127.0.0.1:11434", "m")
    first, second = replay.prompts([SECOND, FIRST], settings)
    assert "--- SOURCE_1 START ---\nDocument title: Quy dinh\nPage: 3" in first[1].content
    assert "rejected" not in first[1].content
    assert SIMPLE_RETRY_INSTRUCTIONS["citation_missing"] in second[1].content
    assert "2.500 kg." in second[1].content.split("Your previous answer")[1]


def test_percentiles_are_nearest_rank() -> None:
    values = list(range(10, 110, 10))
    assert (replay.percentile(values, 0.5), replay.percentile(values, 0.95)) == (50, 100)


def test_a_question_without_drafts_costs_no_llm_time(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    class Provider:
        async def generate(self, *, messages, temperature, max_output_tokens):  # noqa: ANN001
            return LLMGenerationResult(
                content="x", model="m", finish_reason="stop", prompt_tokens=1,
                completion_tokens=1, response_time_ms=7,
            )  # fmt: skip

    monkeypatch.setattr(replay, "create_llm_provider", lambda settings: Provider())
    trace = tmp_path / "trace.jsonl"
    trace.write_text("\n".join(json.dumps(r) for r in (FIRST, SECOND)), encoding="utf-8")
    items = [{"id": "ND-001", "question": "Tai  trong?"}, {"id": "ND-002", "question": "Khac?"}]
    out = asyncio.run(
        replay.replay({"s3t": trace}, items, replay.eval_settings("http://127.0.0.1:11434", "m"))
    )
    config = out["configs"]["s3t"]
    assert config["items"] == {
        "ND-001": {"calls": 2, "llm_ms": 14},
        "ND-002": {"calls": 0, "llm_ms": 0},
    }
    assert (config["p50_ms"], config["p95_ms"], config["calls"]) == (0, 14, 2)
