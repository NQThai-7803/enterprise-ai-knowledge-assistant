"""Per-test client addresses that keep the Redis rate limiter from sharing counters.

The login and refresh limits key on the client IP. Starlette's default TestClient host
("testclient") is not an IP, so every test would share the identity ``ip:unknown`` and a
real Redis would count all their logins together. A random unique-local IPv6 address per
client gives each test its own key without changing or disabling the limiter.
"""

from __future__ import annotations

import ipaddress
import uuid

_UNIQUE_LOCAL_PREFIX = 0xFD00 << 112
_HOST_BITS = (1 << 112) - 1


def isolated_client_address() -> tuple[str, int]:
    """Return a fresh ``(host, port)`` for ``TestClient(client=...)`` inside fd00::/16."""
    host = ipaddress.IPv6Address(_UNIQUE_LOCAL_PREFIX | (uuid.uuid4().int & _HOST_BITS))
    return str(host), 50000
