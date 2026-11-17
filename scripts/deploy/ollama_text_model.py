"""Build an Ollama model without its base's vision projector, optionally pinned to the GPU.

usage (any OS, on the machine that runs Ollama):
  python scripts/deploy/ollama_text_model.py qwen3.5:4b qwen3.5-text:4b --num-gpu 99

DEC-029 B: the deployment model is `qwen3.5-text:4b`, the text part of `qwen3.5:4b` with all layers
on the GPU. The Ollama library has no text-only tag, and the app cannot pass `num_gpu` (the `/v1`
endpoint ignores options), so the model itself carries it.

Steps: pull the base (unless --no-pull); read `ollama show --modelfile <base>`; find the projector
layer in the base's manifest (under OLLAMA_MODELS, default ~/.ollama/models); drop the FROM line of
that layer; set PARAMETER num_gpu; `ollama create`. Refuses if the base has no projector or if the
new model still lists the vision capability. Weights are shared with the base, not copied.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def manifest_path(models_dir: Path, base: str) -> Path:
    name, _, tag = base.partition(":")
    namespace, _, model = name.rpartition("/")
    library = models_dir / "manifests" / "registry.ollama.ai" / (namespace or "library")
    return library / model / (tag or "latest")


def projector_digests(manifest: dict) -> list[str]:
    """Blob names (sha256-...) of the projector layers, as they appear in FROM lines."""
    return [
        layer["digest"].replace(":", "-")
        for layer in manifest["layers"]
        if layer["mediaType"].endswith(".projector")
    ]


def text_modelfile(modelfile: str, projectors: list[str], num_gpu: int | None) -> str:
    """The base's Modelfile without its projector FROM line, with num_gpu set when given."""
    if not projectors:
        raise ValueError("the base model has no projector layer")
    lines = [
        line
        for line in modelfile.splitlines()
        if not (line.startswith("FROM ") and any(digest in line for digest in projectors))
        and not (num_gpu is not None and re.match(r"PARAMETER\s+num_gpu\b", line))
    ]
    if sum(line.startswith("FROM ") for line in lines) != 1:
        raise ValueError("expected exactly one FROM line once the projector is removed")
    if num_gpu is not None:
        lines.append(f"PARAMETER num_gpu {num_gpu}")
    return "\n".join(lines) + "\n"


def has_vision(show_output: str) -> bool:
    return any(line.strip() == "vision" for line in show_output.splitlines())


def _ollama(*args: str) -> str:
    return subprocess.run(["ollama", *args], capture_output=True, text=True, check=True).stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("base", help="e.g. qwen3.5:4b")
    parser.add_argument("name", help="e.g. qwen3.5-text:4b")
    parser.add_argument("--num-gpu", type=int, help="layers on the GPU; 99 = all")
    parser.add_argument("--no-pull", action="store_true")
    args = parser.parse_args(argv)
    models = Path(os.environ.get("OLLAMA_MODELS") or Path.home() / ".ollama" / "models")
    if not args.no_pull:
        subprocess.run(["ollama", "pull", args.base], check=True)
    manifest = json.loads(manifest_path(models, args.base).read_text(encoding="utf-8"))
    try:
        text = text_modelfile(
            _ollama("show", "--modelfile", args.base), projector_digests(manifest), args.num_gpu
        )
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "Modelfile"
        path.write_text(text, encoding="utf-8")
        subprocess.run(["ollama", "create", args.name, "-f", str(path)], check=True)
    if has_vision(_ollama("show", args.name)):
        print(f"REFUSED: {args.name} still lists vision", file=sys.stderr)
        return 2
    print(f"{args.name}: text only" + (f", num_gpu {args.num_gpu}" if args.num_gpu else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
