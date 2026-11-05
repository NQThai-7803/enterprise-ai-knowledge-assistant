"""Host resource sample for eval runs on a Windows host: memory, pagefile and Ollama liveness.

Eval only. Reads the same counters as PowerShell Get-Counter ('\\Memory\\Available MBytes',
'\\Paging File(_Total)\\% Usage') through typeperf, the PID of the Ollama server process
(ollama.exe; a changed PID means Ollama restarted) and whether its API answers. Any field that
cannot be read is None; sampling never raises.
"""

from __future__ import annotations

import csv
import io
import subprocess
from datetime import UTC, datetime
from urllib.request import urlopen

COUNTERS = (r"\Memory\Available MBytes", r"\Paging File(_Total)\% Usage")


def _counters() -> tuple[float | None, float | None]:
    try:
        out = subprocess.run(
            ["typeperf", *COUNTERS, "-sc", "1"],
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout
        rows = [r for r in csv.reader(io.StringIO(out)) if len(r) == 3]
        values = rows[-1][1:]
        return round(float(values[0]), 1), round(float(values[1]), 2)
    except Exception:
        return None, None


def _ollama_pids() -> list[int] | None:
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq ollama.exe", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout
        return sorted(int(r[1]) for r in csv.reader(io.StringIO(out)) if len(r) > 1)
    except Exception:
        return None


def _ollama_up(base_url: str) -> bool:
    try:
        with urlopen(base_url.rstrip("/") + "/api/version", timeout=5) as response:
            return response.status == 200
    except Exception:
        return False


def sample(ollama_url: str = "http://127.0.0.1:11434") -> dict[str, object]:
    available_mb, pagefile_pct = _counters()
    return {
        "at": datetime.now(UTC).isoformat(),
        "available_mb": available_mb,
        "pagefile_pct": pagefile_pct,
        "ollama_pids": _ollama_pids(),
        "ollama_up": _ollama_up(ollama_url),
    }
