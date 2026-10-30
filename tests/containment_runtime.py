"""Q3 interface adapter, not a launcher, authenticator or execution authority.

The owner-controlled external bootstrap must supply the bridge and expected
identity through an independently approved channel. No bridge is discovered in
environment variables, repository modules, files or application settings.
Protocol conformance and True replies do NOT authenticate a bridge. A fake bridge
can exercise this interface but cannot establish external trust. Every result
therefore remains TRUST_NOT_ESTABLISHED / EXECUTION_NOT_AUTHORIZED in this package.

Bridge calls may perform external checks in a future implementation; importing
this module does not. Receipt consumption must be atomic in an external ledger,
across processes and adapter instances. This adapter keeps no replay cache.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol

from tests.containment_guard import (
    Capability,
    ErrorCode,
    PolicyAssessment,
    PolicyStatus,
    PolicyViolation,
    validate_contract,
    validate_database_bindings,
    validate_queue_binding,
    validate_redis_binding,
    validate_storage_binding,
)


class AdmissionCode(StrEnum):
    BRIDGE_MISSING = "BRIDGE_MISSING"
    BRIDGE_FAILURE = "BRIDGE_FAILURE"
    INVALID_CONTEXT = "INVALID_CONTEXT"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    UNKNOWN_OPERATION = "UNKNOWN_OPERATION"
    PROVENANCE_NOT_VERIFIED = "PROVENANCE_NOT_VERIFIED"
    RESOURCE_NOT_ATTESTED = "RESOURCE_NOT_ATTESTED"
    EXECUTION_NOT_AUTHORIZED = "EXECUTION_NOT_AUTHORIZED"
    INVALID_RECEIPT = "INVALID_RECEIPT"
    RECEIPT_MISMATCH = "RECEIPT_MISMATCH"
    RECEIPT_STALE = "RECEIPT_STALE"
    RECEIPT_NOT_ACCEPTED = "RECEIPT_NOT_ACCEPTED"


class AdmissionRejected(ValueError):
    def __init__(self, code: AdmissionCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, repr=False, slots=True)
class ExecutionIdentity:
    run_id: str
    sandbox_id: str
    audience: str
    nonce: str
    source_id: str
    policy_id: str
    launch_id: str


@dataclass(frozen=True, repr=False, slots=True)
class LaunchContext:
    interface_version: str
    identity: ExecutionIdentity
    manifest_id: str
    projection: Mapping[str, object]


@dataclass(frozen=True, repr=False, slots=True)
class OperationReceipt:
    interface_version: str
    receipt_id: str
    identity: ExecutionIdentity
    manifest_id: str
    lease_id: str
    operation: str
    resource_id: str
    issued_at: datetime
    expires_at: datetime


class LaunchBridge(Protocol):
    """External interface proposal; none of these methods is implemented here.

    verify_provenance must bind the ENTIRE context/projection to authenticated
    manifest bytes, expected launch identity and the current supervisor lease.
    attest_resources must consult the authoritative provisioning ledger and
    endpoint bindings. execution_authorized must consult separate owner approval.
    consume_receipt must authenticate all receipt fields and atomically spend its
    ID once, rejecting forged, revoked or replayed receipts. It returns True only
    after consumption; denial/errors never grant authority. Implementations must
    not mutate supplied objects. All checks receive the same owned, deeply frozen
    context snapshot, NOT the object returned by get_context. Implementations must
    compare logical values rather than caller object identity. The producer must
    synchronize publication during snapshot acquisition; this adapter does not
    promise an atomic read of a concurrently changing input graph. Signing and
    provisioning secrets stay outside repo.
    """

    def get_context(self) -> LaunchContext: ...

    def verify_provenance(
        self, context: LaunchContext, expected: ExecutionIdentity, now: datetime
    ) -> bool: ...

    def attest_resources(self, context: LaunchContext, now: datetime) -> bool: ...

    def execution_authorized(
        self, context: LaunchContext, operation: str, now: datetime
    ) -> bool: ...

    def consume_receipt(
        self, context: LaunchContext, receipt: OperationReceipt, now: datetime
    ) -> bool: ...


@dataclass(frozen=True)
class AdmissionReview:
    """Interface-level report only; never use as a mutation permit."""

    policy: PolicyAssessment = field(repr=False)
    interface_status: str = field(default="INTERFACE_CONSISTENT", init=False)
    trust_status: PolicyStatus = field(default=PolicyStatus.TRUST_NOT_ESTABLISHED, init=False)
    execution_status: PolicyStatus = field(
        default=PolicyStatus.EXECUTION_NOT_AUTHORIZED, init=False
    )


def _token(value: object) -> bool:
    return type(value) is str and re.fullmatch(
        r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", value
    ) is not None


def _identity_valid(value: object) -> bool:
    return type(value) is ExecutionIdentity and all(_token(item) for item in (
        value.run_id, value.sandbox_id, value.audience, value.nonce,
        value.source_id, value.policy_id, value.launch_id,
    ))


def _utc(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise AdmissionRejected(AdmissionCode.INVALID_RECEIPT)
    try:
        return value.astimezone(UTC)
    except OverflowError:
        raise AdmissionRejected(AdmissionCode.INVALID_RECEIPT) from None


def _freeze(value: object, depth: int = 0) -> object:
    """Copy ordinary decoded data only; never invoke deepcopy/custom hooks.

    Inputs use exact builtin dict/list/tuple and scalar types only. Input mapping
    proxies reject too: they may wrap a custom Mapping with executable hooks.
    Every OUTPUT mapping proxy wraps a NEW private dict. Tuples are P1-compatible.
    Cycles/over-deep graphs reject at the depth limit. Builtin datetime/timezone
    objects are immutable; subclasses and arbitrary tzinfo callbacks reject.
    This is alias isolation, not a security boundary against hostile Python code.
    """
    if depth > 32:
        raise AdmissionRejected(AdmissionCode.INVALID_CONTEXT)
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is datetime:
        if value.tzinfo is not None and type(value.tzinfo) is not timezone:
            raise AdmissionRejected(AdmissionCode.INVALID_CONTEXT)
        return value
    if type(value) is dict:
        copied: dict[str, object] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise AdmissionRejected(AdmissionCode.INVALID_CONTEXT)
            copied[key] = _freeze(item, depth + 1)
        return MappingProxyType(copied)
    if type(value) in (list, tuple):
        return tuple(_freeze(item, depth + 1) for item in value)
    raise AdmissionRejected(AdmissionCode.INVALID_CONTEXT)


def _snapshot_mapping(value: object) -> Mapping[str, object]:
    frozen = _freeze(value)
    if type(frozen) is not MappingProxyType:
        raise AdmissionRejected(AdmissionCode.INVALID_CONTEXT)
    return frozen


def _snapshot_identity(value: object) -> ExecutionIdentity:
    if not _identity_valid(value):
        raise AdmissionRejected(AdmissionCode.INVALID_CONTEXT)
    return ExecutionIdentity(value.run_id, value.sandbox_id, value.audience, value.nonce,
                             value.source_id, value.policy_id, value.launch_id)


def _snapshot_receipt(value: object) -> OperationReceipt:
    if type(value) is not OperationReceipt:
        raise AdmissionRejected(AdmissionCode.INVALID_RECEIPT)
    # Check leaf types before a callback can observe them; retain existing local
    # receipt validation/error codes for blank IDs, versions and timestamp range.
    if any(type(item) is not str for item in (
        value.interface_version, value.receipt_id, value.manifest_id, value.lease_id,
        value.operation, value.resource_id,
    )) or not _identity_valid(value.identity):
        raise AdmissionRejected(AdmissionCode.INVALID_RECEIPT)
    for instant in (value.issued_at, value.expires_at):
        if (type(instant) is not datetime or
                (instant.tzinfo is not None and type(instant.tzinfo) is not timezone)):
            raise AdmissionRejected(AdmissionCode.INVALID_RECEIPT)
    return OperationReceipt(
        value.interface_version, value.receipt_id, _snapshot_identity(value.identity),
        value.manifest_id, value.lease_id, value.operation, value.resource_id,
        value.issued_at, value.expires_at,
    )


def _review(
    bridge: LaunchBridge,
    expected: ExecutionIdentity,
    operation: str,
    observed: Mapping[str, object],
    receipt: OperationReceipt,
    now: datetime,
) -> AdmissionReview:
    # Snapshot caller declarations BEFORE get_context or any verification call.
    expected = _snapshot_identity(expected)
    observed = _snapshot_mapping(observed)
    receipt = _snapshot_receipt(receipt)
    frozen_now = _freeze(now)
    if type(frozen_now) is not datetime:
        raise PolicyViolation(ErrorCode.INVALID_LEASE)
    now = frozen_now
    if type(operation) not in (str, Capability) or operation not in {
        item.value for item in Capability
    }:
        raise AdmissionRejected(AdmissionCode.UNKNOWN_OPERATION)
    operation = str(operation)
    capability = Capability(operation)
    raw_context = bridge.get_context()
    if (type(raw_context) is not LaunchContext
            or type(raw_context.interface_version) is not str
            or raw_context.interface_version != "1"
            or not _identity_valid(raw_context.identity) or not _token(raw_context.manifest_id)):
        raise AdmissionRejected(AdmissionCode.INVALID_CONTEXT)
    context = LaunchContext(
        "1", _snapshot_identity(raw_context.identity), raw_context.manifest_id,
        _snapshot_mapping(raw_context.projection),
    )
    if context.identity != expected:
        raise AdmissionRejected(AdmissionCode.IDENTITY_MISMATCH)

    policy = validate_contract(
        context.projection, now=now, required_capabilities=(capability,)
    )
    contract = policy.contract
    if (contract.run_id != expected.run_id or contract.sandbox_id != expected.sandbox_id
            or contract.policy_version != expected.policy_id):
        raise AdmissionRejected(AdmissionCode.IDENTITY_MISMATCH)
    # Compare fully parsed declarations, never URL substrings or resource names.
    if capability in (Capability.DB_MIGRATE, Capability.DB_CLEANUP, Capability.DB_WRITE):
        validate_database_bindings(contract, migration=observed, session=observed, cleanup=observed)
        resource_id = contract.postgres.resource_id
    elif capability in (Capability.REDIS_PURGE, Capability.CELERY_PUBLISH, Capability.CELERY_WORKER):
        if set(observed) != {"redis", "queues"}:
            raise AdmissionRejected(AdmissionCode.INVALID_CONTEXT)
        validate_redis_binding(contract, observed["redis"])
        validate_queue_binding(contract, observed["queues"])
        resource_id = contract.redis.instance_id
    else:
        validate_storage_binding(contract, observed)
        resource_id = contract.storage.resource_id

    if bridge.verify_provenance(context, expected, now) is not True:
        raise AdmissionRejected(AdmissionCode.PROVENANCE_NOT_VERIFIED)
    if bridge.attest_resources(context, now) is not True:
        raise AdmissionRejected(AdmissionCode.RESOURCE_NOT_ATTESTED)
    if bridge.execution_authorized(context, operation, now) is not True:
        raise AdmissionRejected(AdmissionCode.EXECUTION_NOT_AUTHORIZED)
    if (type(receipt) is not OperationReceipt or receipt.interface_version != "1"
            or not _token(receipt.receipt_id)):
        raise AdmissionRejected(AdmissionCode.INVALID_RECEIPT)
    if (receipt.identity != expected or receipt.manifest_id != context.manifest_id
            or receipt.lease_id != contract.lease_id or receipt.operation != operation
            or receipt.resource_id != resource_id):
        raise AdmissionRejected(AdmissionCode.RECEIPT_MISMATCH)
    issued, expires, current = (_utc(value) for value in (
        receipt.issued_at, receipt.expires_at, now
    ))
    if not (contract.issued_at <= issued <= current < expires <= contract.expires_at):
        raise AdmissionRejected(AdmissionCode.RECEIPT_STALE)
    if bridge.consume_receipt(context, receipt, now) is not True:
        raise AdmissionRejected(AdmissionCode.RECEIPT_NOT_ACCEPTED)
    return AdmissionReview(policy)


def review_admission(
    *,
    bridge: LaunchBridge | None = None,
    expected: ExecutionIdentity,
    operation: str,
    observed: Mapping[str, object],
    receipt: OperationReceipt,
    now: datetime,
) -> AdmissionReview:
    """Effectful admission-before-operation interface; NOT a dry-run/preview.

    Bridge authenticity/transport/publication are NOT implemented. Dependencies
    must be injected by the future external bootstrap, not a test-supplied claim.
    A successful call consumes a receipt through the bridge even though it does
    not execute the operation or authorize mutation. Never preview real receipts
    here. On uncertain consumption/error, do not automatically retry an operation;
    only the authoritative external ledger can resolve spent state. The returned
    review is deliberately not an execution authorization.
    """
    if bridge is None:
        raise AdmissionRejected(AdmissionCode.BRIDGE_MISSING)
    try:
        return _review(bridge, expected, operation, observed, receipt, now)
    except AdmissionRejected as exc:
        # Rebuild even typed errors: an external implementation could attach raw
        # transport text to exception args. Only known enum codes leave here.
        state = exc.__dict__ if type(exc) is AdmissionRejected else {}
        candidate = state.get("code") if type(state) is dict else None
        code = candidate if type(candidate) is AdmissionCode else AdmissionCode.BRIDGE_FAILURE
        raise AdmissionRejected(code) from None
    except PolicyViolation as exc:
        state = exc.__dict__ if type(exc) is PolicyViolation else {}
        candidate = state.get("code") if type(state) is dict else None
        if type(candidate) is ErrorCode:
            raise PolicyViolation(candidate) from None
        raise AdmissionRejected(AdmissionCode.BRIDGE_FAILURE) from None
    except Exception:
        # Narrow boundary around unimplemented bridge/data interface: strip any
        # raw transport/implementation errors, including possible credentials.
        raise AdmissionRejected(AdmissionCode.BRIDGE_FAILURE) from None
