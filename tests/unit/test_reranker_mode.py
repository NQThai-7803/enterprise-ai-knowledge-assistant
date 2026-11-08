"""reranker_mode, the fallback warning, and the eval runners' refusal."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import threading
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
from scripts.eval import ollama_check, reranker_check
from scripts.eval.reranker_check import RerankerModeRefusedError

ERROR_CODE = "RERANKER_FALLBACK_ACTIVE"
OLLAMA_OK = {
    "ollama_version": "0.40.15",
    "ollama_backend": "CUDA",
    "ollama_expected_version": "0.40.15",
    "ollama_expected_backend": "CUDA",
    "ollama_auto_update": False,
}


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
    monkeypatch.setattr(ollama_check, "read", lambda: dict(OLLAMA_OK))
    assert reranker_check.guard(_args(), "http://x") == {
        "reranker_mode": "lexical_fallback",
        "expected_reranker_mode": "lexical_fallback",
        "allow_reranker_fallback": False,
        **OLLAMA_OK,
    }
    with pytest.raises(RerankerModeRefusedError):
        reranker_check.guard(_args("cross_encoder"), "http://x")


@pytest.mark.parametrize(
    ("version", "backend"), [("0.40.16", "CUDA"), ("0.40.15", "VULKAN"), ("0.40.15", None)]
)
def test_guard_refuses_another_ollama_version_or_backend(
    monkeypatch: pytest.MonkeyPatch, version: str, backend: str | None
) -> None:
    monkeypatch.setattr(reranker_check, "read_mode", lambda *_: "lexical_fallback")
    fields = {**OLLAMA_OK, "ollama_version": version, "ollama_backend": backend}
    monkeypatch.setattr(ollama_check, "read", lambda: fields)
    with pytest.raises(RerankerModeRefusedError, match="Ollama"):
        reranker_check.guard(_args(), "http://x")


def test_expected_ollama_comes_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EVAL_OLLAMA_EXPECTED_VERSION", raising=False)
    monkeypatch.delenv("EVAL_OLLAMA_EXPECTED_BACKEND", raising=False)
    assert ollama_check.expected() == ("0.40.15", "CUDA")
    monkeypatch.setenv("EVAL_OLLAMA_EXPECTED_VERSION", "0.40.15")
    monkeypatch.setenv("EVAL_OLLAMA_EXPECTED_BACKEND", "cpu")
    assert ollama_check.expected() == ("0.40.15", "CPU")


def test_backend_is_read_from_the_current_server_only() -> None:
    old = 'msg="Listening on 127.0.0.1:11434 (version 0.40.14)"\n'
    vulkan = 'msg="inference compute" id=0 filter_id=1 library=Vulkan compute=0.0 driver=0.0\n'
    cuda = 'msg="inference compute" id=0 filter_id=0 library=CUDA compute=7.5 driver=13.3\n'
    new = 'msg="Listening on 127.0.0.1:11434 (version 0.40.15)"\n'
    assert ollama_check.backend_from_log(old + vulkan) == "VULKAN"
    assert ollama_check.backend_from_log(old + vulkan + new + cuda) == "CUDA"
    assert ollama_check.backend_from_log(old + vulkan + new) is None
    cpu = 'msg="inference compute" id=cpu library=cpu compute="" driver=0.0\n'
    assert ollama_check.backend_from_log(new + cpu) == "CPU"


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
    meta = {"reranker_mode": "cross_encoder", **OLLAMA_OK}
    monkeypatch.setattr(reranker_check, "read_mode", lambda *_: "cross_encoder")
    monkeypatch.setattr(ollama_check, "read", lambda: dict(OLLAMA_OK))
    assert reranker_check.finish(output, meta, "http://x", 0) == 0
    monkeypatch.setattr(reranker_check, "read_mode", lambda *_: "lexical_fallback")
    assert reranker_check.finish(output, meta, "http://x", 0) == reranker_check.EXIT_MODE_CHANGED
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["reranker_mode_end"] == "lexical_fallback"


def test_ollama_update_during_a_run_invalidates_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "run.json"
    output.write_text("{}", encoding="utf-8")
    meta = {"reranker_mode": "cross_encoder", **OLLAMA_OK}
    monkeypatch.setattr(reranker_check, "read_mode", lambda *_: "cross_encoder")
    monkeypatch.setattr(ollama_check, "read", lambda: {**OLLAMA_OK, "ollama_version": "0.40.16"})
    assert reranker_check.finish(output, meta, "http://x", 0) == reranker_check.EXIT_MODE_CHANGED
    assert json.loads(output.read_text(encoding="utf-8"))["ollama_version_end"] == "0.40.16"


class _Model:
    def __init__(self, *, release: threading.Event | None = None, error: bool = False) -> None:
        self.release = release
        self.error = error

    def predict(self, pairs: list[list[str]], **kwargs: object) -> list[float]:
        if self.release is not None:
            self.release.wait(5)
        if self.error:
            raise RuntimeError("predict failed")
        return [0.1 * index for index in range(len(pairs))]


def _rerank(reranker: object) -> tuple:
    return asyncio.run(reranker.rerank(query="q", hits=(_hit(0), _hit(1)), top_k=1))


def test_timeout_falls_back_for_that_request_only(caplog: pytest.LogCaptureFixture) -> None:
    release = threading.Event()
    model = _Model(release=release)
    reranker = _reranker(model_loader=lambda name, **kwargs: model, timeout_seconds=0.05)
    with caplog.at_level(logging.WARNING):
        first = _rerank(reranker)
    assert "RERANKER_TIMEOUT" in _codes(caplog)
    assert ERROR_CODE in _codes(caplog)
    assert first[0].chunk_index == 0  # lexical order keeps the first hit on a tie
    assert reranker._model_load_failed is False
    assert reranker.mode == "cross_encoder"

    release.set()
    caplog.clear()
    reranker._timeout_seconds = 5.0
    with caplog.at_level(logging.WARNING):
        second = _rerank(reranker)
    assert second[0].chunk_index == 1  # the model scored the second hit higher
    assert _codes(caplog) == []


def test_load_failure_sets_the_flag_and_is_not_retried(caplog: pytest.LogCaptureFixture) -> None:
    calls = []

    def loader(name: str, **kwargs: object) -> object:
        calls.append(name)
        raise RuntimeError("no model")

    reranker = _reranker(model_loader=loader)
    with caplog.at_level(logging.WARNING):
        _rerank(reranker)
        _rerank(reranker)
    assert reranker._model_load_failed is True
    assert reranker.mode == "lexical_fallback"
    assert len(calls) == 1
    assert "RERANKER_TIMEOUT" not in _codes(caplog)


def test_slow_load_that_times_out_is_not_a_load_failure_and_loads_once() -> None:
    release = threading.Event()
    created = []

    def loader(name: str, **kwargs: object) -> object:
        created.append(name)
        release.wait(5)
        return _Model()

    reranker = _reranker(model_loader=loader, timeout_seconds=0.05)
    _rerank(reranker)
    assert reranker._model_load_failed is False
    release.set()
    reranker._timeout_seconds = 5.0
    assert _rerank(reranker)[0].chunk_index == 1
    assert len(created) == 1


def test_predict_error_falls_back_without_the_load_flag(caplog: pytest.LogCaptureFixture) -> None:
    model = _Model(error=True)
    reranker = _reranker(model_loader=lambda name, **kwargs: model)
    with caplog.at_level(logging.WARNING):
        assert len(_rerank(reranker)) == 1
    assert "RERANKER_PREDICT_FAILED" in _codes(caplog)
    assert reranker._model_load_failed is False
    assert reranker.mode == "cross_encoder"
