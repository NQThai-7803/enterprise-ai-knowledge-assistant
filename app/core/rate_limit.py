from __future__ import annotations

import time
from dataclasses import dataclass
from ipaddress import ip_address
from uuid import UUID

from fastapi import Request
from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.core.exceptions import RateLimitExceededError


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    scope: str
    requests: int
    window_seconds: int
    fail_closed: bool


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


class RateLimiterUnavailableError(Exception):
    """Raised when the configured rate-limit backend cannot be reached."""


class RedisFixedWindowRateLimiter:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def check(self, *, identity: str, rule: RateLimitRule) -> RateLimitDecision:
        window_started_at = int(time.time() // rule.window_seconds) * rule.window_seconds
        key = f"rate-limit:{rule.scope}:{identity}:{window_started_at}"
        client = Redis.from_url(
            self.settings.redis_url,
            socket_connect_timeout=self.settings.redis_connect_timeout_seconds,
            socket_timeout=self.settings.redis_socket_timeout_seconds,
            health_check_interval=self.settings.redis_health_check_interval_seconds,
            decode_responses=True,
        )
        try:
            pipeline = client.pipeline(transaction=True)
            pipeline.incr(key)
            pipeline.expire(key, rule.window_seconds)
            count_result, _ = await pipeline.execute()
            count = int(count_result)
        except Exception as exc:
            raise RateLimiterUnavailableError from exc
        finally:
            await client.aclose()

        retry_after = max(1, window_started_at + rule.window_seconds - int(time.time()))
        if count > rule.requests:
            return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)
        return RateLimitDecision(allowed=True)


class InMemoryFixedWindowRateLimiter:
    def __init__(self) -> None:
        self._counts: dict[tuple[str, str, int], int] = {}

    async def check(self, *, identity: str, rule: RateLimitRule) -> RateLimitDecision:
        window_started_at = int(time.time() // rule.window_seconds) * rule.window_seconds
        key = (rule.scope, identity, window_started_at)
        self._counts[key] = self._counts.get(key, 0) + 1
        retry_after = max(1, window_started_at + rule.window_seconds - int(time.time()))
        if self._counts[key] > rule.requests:
            return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)
        return RateLimitDecision(allowed=True)


async def enforce_rate_limit(
    request: Request,
    *,
    rule: RateLimitRule,
    identity: str,
    limiter: RedisFixedWindowRateLimiter | InMemoryFixedWindowRateLimiter | None = None,
    settings: Settings | None = None,
) -> None:
    resolved_settings = settings or get_settings()
    if not resolved_settings.rate_limit_enabled:
        return
    resolved_limiter = limiter or RedisFixedWindowRateLimiter(resolved_settings)
    safe_identity = _normalize_identity(identity)
    try:
        decision = await resolved_limiter.check(identity=safe_identity, rule=rule)
    except RateLimiterUnavailableError:
        if rule.fail_closed:
            raise RateLimitExceededError(retry_after_seconds=rule.window_seconds) from None
        return
    if not decision.allowed:
        raise RateLimitExceededError(retry_after_seconds=decision.retry_after_seconds)


def anonymous_identity(request: Request) -> str:
    client_host = request.client.host if request.client is not None else "unknown"
    try:
        return f"ip:{ip_address(client_host)}"
    except ValueError:
        return "ip:unknown"


def user_identity(user_id: UUID) -> str:
    return f"user:{user_id}"


def login_rule(settings: Settings | None = None) -> RateLimitRule:
    resolved = settings or get_settings()
    return RateLimitRule(
        scope="login",
        requests=resolved.rate_limit_login_requests,
        window_seconds=resolved.rate_limit_login_window_seconds,
        fail_closed=resolved.app_env == "production",
    )


def refresh_rule(settings: Settings | None = None) -> RateLimitRule:
    resolved = settings or get_settings()
    return RateLimitRule(
        scope="refresh",
        requests=resolved.rate_limit_refresh_requests,
        window_seconds=resolved.rate_limit_refresh_window_seconds,
        fail_closed=resolved.app_env == "production",
    )


def upload_rule(settings: Settings | None = None) -> RateLimitRule:
    resolved = settings or get_settings()
    return RateLimitRule(
        scope="upload",
        requests=resolved.rate_limit_upload_requests,
        window_seconds=resolved.rate_limit_upload_window_seconds,
        fail_closed=resolved.app_env == "production",
    )


def chat_rule(settings: Settings | None = None) -> RateLimitRule:
    resolved = settings or get_settings()
    return RateLimitRule(
        scope="chat",
        requests=resolved.rate_limit_chat_requests,
        window_seconds=resolved.rate_limit_chat_window_seconds,
        fail_closed=resolved.app_env == "production",
    )


def feedback_rule(settings: Settings | None = None) -> RateLimitRule:
    resolved = settings or get_settings()
    return RateLimitRule(
        scope="feedback",
        requests=resolved.rate_limit_feedback_requests,
        window_seconds=resolved.rate_limit_feedback_window_seconds,
        fail_closed=False,
    )


def _normalize_identity(identity: str) -> str:
    normalized = identity.strip().replace(" ", "_")
    return normalized[:128] or "unknown"
