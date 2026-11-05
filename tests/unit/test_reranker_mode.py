"""reranker_mode, the fallback warning, and the eval runners' refusal."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.retrieval import reranker_factory
from app.retrieval.models import HybridRetrievalHit
from app.retrieval.reranker import (
    HeuristicRetrievalReranker,
    SentenceTransformerCrossEncoderReranker,
)
from app.retrieval.reranker_factory import log_reranker_startup_status, resolve_reranker_mode
from scripts.eval import reranker_check
from scripts.eval.reranker_check import RerankerModeRefusedError

ERROR_CODE = "RERANKER_FALLBACK_ACTIVE"


def _hit(index: int = 0) -> HybridRetrievalHit:
    return HybridRetrievalHit(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="Doc",
        chunk_index=index,
        text="some text",
        page_numbers=(1,),
        start_page=1,
        end_page=1,
        token_count=2,
        hybrid_score=0.5,
        semantic_score=0.5,
        semantic_rank=1,
        keyword_score=None,
        keyword_rank=None,
        matched_by=("semantic",),
    )


def _reranker(cache: Path | str = "./missing-cache", **kwargs) -> object:
    defaults = {
        "model_name": "org/model",
        "model_revision": "",
        "device": "cpu",
        "batch_size": 2,
        "max_length": 128,
        "timeout_seconds": 5.0,
        "local_files_only": True,
        "cache_folder": str(cache),
    }
    return SentenceTransformerCrossEncoderReranker(**{**defaults, **kwargs})


def _settings(tmp_path: Path, **kwargs) -> Settings:
    reranker_factory._RERANKER_CACHE.clear()
    return Settings(
        reranker_model_cache_path=str(tmp_path),
        reranker_model="org/model",
        _env_file=None,
        **kwargs,
    )


def _fake_cache(root: Path, *, weights: bool) -> None:
    snapshot = root / "models--org--model" / "snapshots" / "abc"
    snapshot.mkdir(parents=True)
    (root / "models--org--model" / "refs").mkdir()
    (root / "models--org--model" / "refs" / "main").write_text("abc", encoding="utf-8")
    (snapshot / "config.json").write_text("{}", encoding="utf-8")
    if weights:
        (snapshot / "model.safetensors").write_text("x", encoding="utf-8")


def _codes(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.error_code for r in caplog.records if hasattr(r, "error_code")]


def test_missing_cache_means_lexical_fallback(tmp_path: Path) -> None:
    assert _reranker(tmp_path).mode == "lexical_fallback"


def test_config_without_weights_means_lexical_fallback(tmp_path: Path) -> None:
    _fake_cache(tmp_path, weights=False)
    assert _reranker(tmp_path).mode == "lexical_fallback"


def test_cached_weights_mean_cross_encoder_without_loading(tmp_path: Path) -> None:
    _fake_cache(tmp_path, weights=True)
    reranker = _reranker(tmp_path)
    assert reranker.mode == "cross_encoder"
    assert reranker._model is None


def test_failed_load_turns_the_mode_to_lexical_fallback_and_warns(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    def loader(name: str, **kwargs: object) -> object:
        raise RuntimeError("no model")

    reranker = _reranker(tmp_path, model_loader=loader)
    assert reranker.mode == "cross_encoder"
    with caplog.at_level(logging.WARNING):
        asyncio.run(reranker.rerank(query="q", hits=(_hit(0), _hit(1)), top_k=1))
        asyncio.run(reranker.rerank(query="q", hits=(_hit(0), _hit(1)), top_k=1))
    assert reranker.mode == "lexical_fallback"
    assert _codes(caplog).count(ERROR_CODE) == 2


def test_explicit_heuristic_warns_on_each_use(caplog: pytest.LogCaptureFixture) -> None:
    reranker = HeuristicRetrievalReranker()
    assert reranker.mode == "lexical_fallback"
    with caplog.at_level(logging.WARNING):
        asyncio.run(reranker.rerank(query="q", hits=(_hit(),), top_k=1))
    assert _codes(caplog) == [ERROR_CODE]


def test_resolve_mode_covers_disabled_and_heuristic(tmp_path: Path) -> None:
    assert resolve_reranker_mode(_settings(tmp_path, reranker_enabled=False)) == "disabled"
    heuristic = _settings(tmp_path, reranker_provider="heuristic")
    assert resolve_reranker_mode(heuristic) == "lexical_fallback"
    assert resolve_reranker_mode(_settings(tmp_path)) == "lexical_fallback"


def test_startup_warns_only_on_fallback(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        assert log_reranker_startup_status(_settings(tmp_path)) == "lexical_fallback"
    assert _codes(caplog) == [ERROR_CODE]
    caplog.clear()
    _fake_cache(tmp_path, weights=True)
    with caplog.at_level(logging.WARNING):
        assert log_reranker_startup_status(_settings(tmp_path)) == "cross_encoder"
    assert _codes(caplog) == []


def test_application_startup_logs_the_fallback(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    settings = _settings(tmp_path, app_env="test", secret_key="k" * 40)
    with caplog.at_level(logging.WARNING), TestClient(create_app(settings)):
        pass
    assert ERROR_CODE in _codes(caplog)


@pytest.mark.parametrize(
    ("actual", "expected", "allow", "refused"),
    [
        ("lexical_fallback", "lexical_fallback", False, False),
        ("cross_encoder", "cross_encoder", False, False),
        ("lexical_fallback", "cross_encoder", False, True),
        ("lexical_fallback", "cross_encoder", True, False),
        ("cross_encoder", "lexical_fallback", False, True),
        ("cross_encoder", "lexical_fallback", True, True),
        ("disabled", "cross_encoder", True, True),
        (None, "lexical_fallback", True, True),
    ],
)
def test_refusal_rules(actual: str | None, expected: str, allow: bool, refused: bool) -> None:
    assert (reranker_check.refusal(actual, expected, allow) is not None) is refused


def _args(expected: str = "lexical_fallback", allow: bool = False) -> argparse.Namespace:
    return SimpleNamespace(expected_reranker_mode=expected, allow_reranker_fallback=allow)


def test_guard_records_the_mode_and_raises_on_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reranker_check, "read_mode", lambda *_: "lexical_fallback")
    assert reranker_check.guard(_args(), "http://x") == {
        "reranker_mode": "lexical_fallback",
        "expected_reranker_mode": "lexical_fallback",
        "allow_reranker_fallback": False,
    }
    with pytest.raises(RerankerModeRefusedError):
        reranker_check.guard(_args("cross_encoder"), "http://x")


def test_expected_mode_defaults_to_cross_encoder_and_reads_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(reranker_check.ENV_EXPECTED, raising=False)
    parser = argparse.ArgumentParser()
    reranker_check.add_arguments(parser)
    assert parser.parse_args([]).expected_reranker_mode == "cross_encoder"
    monkeypatch.setenv(reranker_check.ENV_EXPECTED, "lexical_fallback")
    parser = argparse.ArgumentParser()
    reranker_check.add_arguments(parser)
    assert parser.parse_args([]).expected_reranker_mode == "lexical_fallback"


def test_mode_change_during_a_run_invalidates_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "run.json"
    output.write_text("{}", encoding="utf-8")
    meta = {"reranker_mode": "cross_encoder"}
    monkeypatch.setattr(reranker_check, "read_mode", lambda *_: "cross_encoder")
    assert reranker_check.finish(output, meta, "http://x", 0) == 0
    monkeypatch.setattr(reranker_check, "read_mode", lambda *_: "lexical_fallback")
    assert reranker_check.finish(output, meta, "http://x", 0) == reranker_check.EXIT_MODE_CHANGED
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["reranker_mode_end"] == "lexical_fallback"
