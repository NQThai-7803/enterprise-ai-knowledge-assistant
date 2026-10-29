"""E00-P1 pure policy; this module grants no execution or mutation authority.

All identities are unverified claims. No URL, credential, signature, digest or
application settings are accepted. External authentication, provisioning-ledger
checks, server attestation and OS restrictions remain separate requirements.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import NoReturn


class ErrorCode(StrEnum):
    MISSING_CONTRACT = "MISSING_CONTRACT"
    INVALID_STRUCTURE = "INVALID_STRUCTURE"
    UNSUPPORTED_FIELD = "UNSUPPORTED_FIELD"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"
    MISSING_IDENTITY = "MISSING_IDENTITY"
    INVALID_LEASE = "INVALID_LEASE"
    LEASE_NOT_STARTED = "LEASE_NOT_STARTED"
    LEASE_EXPIRED = "LEASE_EXPIRED"
    MISSING_CAPABILITY = "MISSING_CAPABILITY"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    DATABASE_MISMATCH = "DATABASE_MISMATCH"
    REDIS_MISMATCH = "REDIS_MISMATCH"
    QUEUE_MISMATCH = "QUEUE_MISMATCH"
    STORAGE_MISMATCH = "STORAGE_MISMATCH"
    OWNERSHIP_MISMATCH = "OWNERSHIP_MISMATCH"


class PolicyViolation(ValueError):
    """Only fixed error codes are exposed; input values are never formatted."""

    def __init__(self, code: ErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class Capability(StrEnum):
    DB_MIGRATE = "db.migrate"
    DB_CLEANUP = "db.cleanup"
    DB_WRITE = "db.write"
    REDIS_PURGE = "redis.purge"
    CELERY_PUBLISH = "celery.publish"
    CELERY_WORKER = "celery.worker"
    STORAGE_WRITE = "storage.write"


class PolicyStatus(StrEnum):
    STRUCTURALLY_VALID = "STRUCTURALLY_VALID"
    TRUST_NOT_ESTABLISHED = "TRUST_NOT_ESTABLISHED"
    EXECUTION_NOT_AUTHORIZED = "EXECUTION_NOT_AUTHORIZED"


@dataclass(frozen=True, repr=False)
class DatabaseTarget:
    resource_id: str
    database: str
    role: str
    schema: str


@dataclass(frozen=True, repr=False)
class RedisTarget:
    instance_id: str
    broker_instance_id: str
    backend_instance_id: str
    rate_limit_instance_id: str
    broker_db: int
    backend_db: int
    rate_limit_db: int


@dataclass(frozen=True, repr=False)
class QueueContract:
    default_queue: str
    document_queue: str
    worker_queues: tuple[str, ...]


@dataclass(frozen=True, repr=False)
class StorageTarget:
    resource_id: str
    root_id: str
    root_path: str


@dataclass(frozen=True, repr=False)
class ResourceOwnership:
    resource_id: str
    kind: str
    run_id: str
    sandbox_id: str


@dataclass(frozen=True, repr=False)
class TestTargetContract:
    __test__ = False

    contract_version: str
    policy_version: str
    run_id: str
    sandbox_id: str
    lease_id: str
    issued_at: datetime
    expires_at: datetime
    postgres: DatabaseTarget
    redis: RedisTarget
    queues: QueueContract
    storage: StorageTarget
    ownership: tuple[ResourceOwnership, ...]
    capabilities: tuple[Capability, ...]


@dataclass(frozen=True)
class PolicyAssessment:
    contract: TestTargetContract = field(repr=False)
    structural_status: PolicyStatus = field(default=PolicyStatus.STRUCTURALLY_VALID, init=False)
    trust_status: PolicyStatus = field(default=PolicyStatus.TRUST_NOT_ESTABLISHED, init=False)
    execution_status: PolicyStatus = field(
        default=PolicyStatus.EXECUTION_NOT_AUTHORIZED, init=False
    )


def _reject(code: ErrorCode) -> NoReturn:
    raise PolicyViolation(code)


def _record(value: object, fields: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _reject(ErrorCode.INVALID_STRUCTURE)
    expected = set(fields.split())
    if any(not isinstance(key, str) or key not in expected for key in value):
        _reject(ErrorCode.UNSUPPORTED_FIELD)
    if set(value) != expected:
        _reject(ErrorCode.INVALID_STRUCTURE)
    return value


def _identity(value: object) -> str:
    # Opaque identifiers, never URLs. No naming convention proves provisioning.
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", value):
        _reject(ErrorCode.MISSING_IDENTITY)
    return value


def _sequence(value: object) -> tuple[object, ...]:
    if not isinstance(value, (list, tuple)):
        _reject(ErrorCode.INVALID_STRUCTURE)
    return tuple(value)


def _instant(value: object) -> datetime:
    # Explicit aware datetimes only: wire timestamp decoding belongs to P2.
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        _reject(ErrorCode.INVALID_LEASE)
    try:
        return value.astimezone(timezone.utc)
    except OverflowError:
        raise PolicyViolation(ErrorCode.INVALID_LEASE) from None


def _database(value: object) -> DatabaseTarget:
    data = _record(value, "resource_id database role schema")
    return DatabaseTarget(*(_identity(data[key]) for key in (
        "resource_id", "database", "role", "schema"
    )))


def _redis_index(value: object) -> int:
    if type(value) is not int or value < 0:
        _reject(ErrorCode.INVALID_STRUCTURE)
    return value


def _redis(value: object) -> RedisTarget:
    data = _record(value, "instance_id broker_instance_id backend_instance_id "
                   "rate_limit_instance_id broker_db backend_db rate_limit_db")
    ids = tuple(_identity(data[key]) for key in (
        "instance_id", "broker_instance_id", "backend_instance_id", "rate_limit_instance_id"
    ))
    if len(set(ids)) != 1:
        _reject(ErrorCode.REDIS_MISMATCH)
    indices = tuple(_redis_index(data[key]) for key in (
        "broker_db", "backend_db", "rate_limit_db"
    ))
    if len(set(indices)) != 3:
        _reject(ErrorCode.REDIS_MISMATCH)
    return RedisTarget(*ids, *indices)


def _queues(value: object) -> QueueContract:
    data = _record(value, "default_queue document_queue worker_queues")
    default = _identity(data["default_queue"])
    document = _identity(data["document_queue"])
    workers = tuple(_identity(item) for item in _sequence(data["worker_queues"]))
    if default == document or len(workers) != 2 or set(workers) != {default, document}:
        _reject(ErrorCode.QUEUE_MISMATCH)
    return QueueContract(default, document, workers)


def _storage(value: object) -> StorageTarget:
    data = _record(value, "resource_id root_id root_path")
    resource_id = _identity(data["resource_id"])
    root_id = _identity(data["root_id"])
    path = data["root_path"]
    # V1 accepts canonical POSIX sandbox paths only, compared exactly. Reject
    # root '/', duplicate separators, trailing '/', '.', '..', backslashes and
    # non-ASCII segments. This is lexical validation, never symlink attestation.
    if not isinstance(path, str) or not path.startswith("/"):
        _reject(ErrorCode.STORAGE_MISMATCH)
    if any(part in {"", ".", ".."} or not re.fullmatch(r"[A-Za-z0-9_.-]+", part)
           for part in path[1:].split("/")):
        _reject(ErrorCode.STORAGE_MISMATCH)
    return StorageTarget(resource_id, root_id, path)


def _capabilities(value: object) -> tuple[Capability, ...]:
    result: list[Capability] = []
    for item in _sequence(value):
        if not isinstance(item, str) or item not in {member.value for member in Capability}:
            _reject(ErrorCode.UNSUPPORTED_CAPABILITY)
        result.append(Capability(item))
    if len(set(result)) != len(result):
        _reject(ErrorCode.INVALID_STRUCTURE)
    return tuple(result)


def validate_contract(
    payload: Mapping[str, object] | None,
    *,
    now: datetime,
    required_capabilities: tuple[Capability, ...] = (),
) -> PolicyAssessment:
    """Validate claims only; even a successful result never authorizes execution.

    Input mappings must be ordinary decoded data, not objects with user-defined
    mapping hooks. No trust, connection or provisioning check is performed.
    """
    if payload is None:
        _reject(ErrorCode.MISSING_CONTRACT)
    data = _record(payload, "contract_version policy_version run_id sandbox_id lease_id "
                   "issued_at expires_at postgres redis queues storage ownership capabilities")
    if data["contract_version"] != "1" or data["policy_version"] != "e00-p1-v1":
        _reject(ErrorCode.UNSUPPORTED_VERSION)
    run_id = _identity(data["run_id"])
    sandbox_id = _identity(data["sandbox_id"])
    lease_id = _identity(data["lease_id"])
    issued, expires, current = (_instant(value) for value in (
        data["issued_at"], data["expires_at"], now
    ))
    if issued >= expires:
        _reject(ErrorCode.INVALID_LEASE)
    if current < issued:
        _reject(ErrorCode.LEASE_NOT_STARTED)
    if current >= expires:
        _reject(ErrorCode.LEASE_EXPIRED)
    postgres = _database(data["postgres"])
    redis = _redis(data["redis"])
    queues = _queues(data["queues"])
    storage = _storage(data["storage"])
    resources = ((postgres.resource_id, "postgres"), (redis.instance_id, "redis"),
                 (storage.resource_id, "storage"))
    if len({resource_id for resource_id, _ in resources}) != 3:
        _reject(ErrorCode.OWNERSHIP_MISMATCH)
    owners: list[ResourceOwnership] = []
    for item in _sequence(data["ownership"]):
        owner = _record(item, "resource_id kind run_id sandbox_id")
        owners.append(ResourceOwnership(*(_identity(owner[key]) for key in (
            "resource_id", "kind", "run_id", "sandbox_id"
        ))))
    expected = {ResourceOwnership(resource_id, kind, run_id, sandbox_id)
                for resource_id, kind in resources}
    if len(owners) != 3 or set(owners) != expected:
        _reject(ErrorCode.OWNERSHIP_MISMATCH)
    capabilities = _capabilities(data["capabilities"])
    required = _capabilities(required_capabilities)
    if not set(required).issubset(capabilities):
        _reject(ErrorCode.MISSING_CAPABILITY)
    contract = TestTargetContract(
        "1", "e00-p1-v1", run_id, sandbox_id, lease_id, issued, expires,
        postgres, redis, queues, storage, tuple(owners), capabilities,
    )
    return PolicyAssessment(contract)


def validate_database_bindings(
    contract: TestTargetContract,
    *,
    migration: Mapping[str, object],
    session: Mapping[str, object],
    cleanup: Mapping[str, object],
) -> None:
    """Compare declared consumers; this does not inspect engines or servers."""
    if any(_database(value) != contract.postgres for value in (migration, session, cleanup)):
        _reject(ErrorCode.DATABASE_MISMATCH)


def validate_redis_binding(contract: TestTargetContract, observed: Mapping[str, object]) -> None:
    if _redis(observed) != contract.redis:
        _reject(ErrorCode.REDIS_MISMATCH)


def validate_queue_binding(contract: TestTargetContract, observed: Mapping[str, object]) -> None:
    actual = _queues(observed)
    expected = contract.queues
    if (actual.default_queue != expected.default_queue
            or actual.document_queue != expected.document_queue
            or set(actual.worker_queues) != set(expected.worker_queues)):
        _reject(ErrorCode.QUEUE_MISMATCH)


def validate_storage_binding(contract: TestTargetContract, observed: Mapping[str, object]) -> None:
    if _storage(observed) != contract.storage:
        _reject(ErrorCode.STORAGE_MISMATCH)
