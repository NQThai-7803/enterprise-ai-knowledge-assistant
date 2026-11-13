"""Applies the PROMPT 6 ablations (scripts/diagnostics/ablation_patches.py) at interpreter start.

The eval stack puts this directory first on PYTHONPATH for the API only. With EVAL_ABLATION
unset nothing is imported. Python's site module swallows ordinary exceptions raised here, so a
failure becomes SystemExit: a run must never pass as an ablation it is not.
"""

import os

if os.environ.get("EVAL_ABLATION"):
    try:
        from scripts.diagnostics import ablation_patches

        ablation_patches.apply(ablation_patches.selected())
    except Exception as exc:
        raise SystemExit(f"ABLATION failed: {exc}") from exc
