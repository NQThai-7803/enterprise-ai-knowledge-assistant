"""Source-authored synthetic assertions, not execution evidence or authorization.

Do not run on the host: existing root conftest still imports application code.
P1 neither changes that harness nor establishes an external execution boundary.
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from tests.containment_guard import (
    Capability,
    ErrorCode,
    PolicyStatus,
    PolicyViolation,
    validate_contract,
    validate_database_bindings,
    validate_queue_binding,
    validate_redis_binding,
    validate_storage_binding,
)


NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


def synthetic_contract() -> dict[str, Any]:
    return {
        "contract_version": "1",
        "policy_version": "e00-p1-v1",
        "run_id": "synthetic-run",
        "sandbox_id": "synthetic-sandbox",
        "lease_id": "synthetic-lease",
        "issued_at": NOW - timedelta(minutes=1),
        "expires_at": NOW + timedelta(minutes=5),
        "postgres": {
            "resource_id": "synthetic-db-instance",
            "database": "synthetic_db",
            "role": "synthetic_role",
            "schema": "public",
        },
        "redis": {
            "instance_id": "synthetic-redis-instance",
            "broker_instance_id": "synthetic-redis-instance",
            "backend_instance_id": "synthetic-redis-instance",
            "rate_limit_instance_id": "synthetic-redis-instance",
            "broker_db": 1,
            "backend_db": 2,
            "rate_limit_db": 0,
        },
        "queues": {
            "default_queue": "default",
            "document_queue": "documents",
            "worker_queues": ["default", "documents"],
        },
        "storage": {
            "resource_id": "synthetic-volume",
            "root_id": "synthetic-root",
            "root_path": "/scratch/uploads",
        },
        "ownership": [
            {"resource_id": resource_id, "kind": kind, "run_id": "synthetic-run",
             "sandbox_id": "synthetic-sandbox"}
            for resource_id, kind in (
                ("synthetic-db-instance", "postgres"),
                ("synthetic-redis-instance", "redis"),
                ("synthetic-volume", "storage"),
            )
        ],
        "capabilities": [capability.value for capability in Capability],
    }


def assert_rejected(
    payload: dict[str, Any] | None,
    code: ErrorCode,
    *,
    required_capabilities: tuple[Capability, ...] = (),
) -> None:
    with pytest.raises(PolicyViolation) as caught:
        validate_contract(payload, now=NOW, required_capabilities=required_capabilities)
    assert caught.value.code == code
    assert str(caught.value) == code.value


def test_n01_missing_contract() -> None:
    assert_rejected(None, ErrorCode.MISSING_CONTRACT)


@pytest.mark.parametrize("field", ["contract_version", "policy_version"])
def test_n02_invalid_version(field: str) -> None:
    payload = synthetic_contract()
    payload[field] = "unsupported"
    assert_rejected(payload, ErrorCode.UNSUPPORTED_VERSION)


@pytest.mark.parametrize("offset", [0, -1])
def test_n03_expired_lease(offset: int) -> None:
    payload = synthetic_contract()
    payload["expires_at"] = NOW + timedelta(seconds=offset)
    assert_rejected(payload, ErrorCode.LEASE_EXPIRED)


@pytest.mark.parametrize("field", ["run_id", "sandbox_id", "lease_id"])
@pytest.mark.parametrize("value", ["", " ", None])
def test_n04_missing_identity(field: str, value: object) -> None:
    payload = synthetic_contract()
    payload[field] = value
    assert_rejected(payload, ErrorCode.MISSING_IDENTITY)


def test_n05_database_name_is_not_provisioning_identity() -> None:
    payload = synthetic_contract()
    payload["postgres"]["database"] = "test_disposable"
    payload["postgres"]["resource_id"] = ""
    assert_rejected(payload, ErrorCode.MISSING_IDENTITY)


@pytest.mark.parametrize("consumer", ["migration", "session", "cleanup"])
@pytest.mark.parametrize("field", ["resource_id", "database", "role", "schema"])
def test_n06_database_consumer_mismatch(consumer: str, field: str) -> None:
    payload = synthetic_contract()
    contract = validate_contract(payload, now=NOW).contract
    bindings = {name: deepcopy(payload["postgres"]) for name in (
        "migration", "session", "cleanup"
    )}
    bindings[consumer][field] = "different-identity"
    with pytest.raises(PolicyViolation) as caught:
        validate_database_bindings(contract, **bindings)
    assert caught.value.code == ErrorCode.DATABASE_MISMATCH


@pytest.mark.parametrize("field", [
    "broker_instance_id", "backend_instance_id", "rate_limit_instance_id"
])
def test_n07_redis_instance_mismatch(field: str) -> None:
    payload = synthetic_contract()
    payload["redis"][field] = "different-instance"
    assert_rejected(payload, ErrorCode.REDIS_MISMATCH)


def test_n07_redis_logical_database_conflict() -> None:
    payload = synthetic_contract()
    payload["redis"]["backend_db"] = payload["redis"]["broker_db"]
    assert_rejected(payload, ErrorCode.REDIS_MISMATCH)


def test_n07_internally_consistent_redis_binding_still_must_match_contract() -> None:
    payload = synthetic_contract()
    contract = validate_contract(payload, now=NOW).contract
    observed = deepcopy(payload["redis"])
    observed["broker_db"] = 3
    with pytest.raises(PolicyViolation) as caught:
        validate_redis_binding(contract, observed)
    assert caught.value.code == ErrorCode.REDIS_MISMATCH


@pytest.mark.parametrize("value", [True, -1, "1", None])
def test_n07_invalid_redis_index(value: object) -> None:
    payload = synthetic_contract()
    payload["redis"]["broker_db"] = value
    assert_rejected(payload, ErrorCode.INVALID_STRUCTURE)


def test_n08_worker_queue_mismatch() -> None:
    payload = synthetic_contract()
    payload["queues"]["worker_queues"] = ["default", "other"]
    assert_rejected(payload, ErrorCode.QUEUE_MISMATCH)


def test_n08_internally_consistent_queues_still_must_match_contract() -> None:
    payload = synthetic_contract()
    contract = validate_contract(payload, now=NOW).contract
    observed = {"default_queue": "other", "document_queue": "documents",
                "worker_queues": ["other", "documents"]}
    with pytest.raises(PolicyViolation) as caught:
        validate_queue_binding(contract, observed)
    assert caught.value.code == ErrorCode.QUEUE_MISMATCH


@pytest.mark.parametrize("field,value", [
    ("resource_id", "another-volume"),
    ("root_id", "another-root"),
    ("root_path", "/scratch/other"),
])
def test_n09_storage_binding_mismatch(field: str, value: str) -> None:
    payload = synthetic_contract()
    contract = validate_contract(payload, now=NOW).contract
    observed = deepcopy(payload["storage"])
    observed[field] = value
    with pytest.raises(PolicyViolation) as caught:
        validate_storage_binding(contract, observed)
    assert caught.value.code == ErrorCode.STORAGE_MISMATCH


@pytest.mark.parametrize("path", [
    "/", "relative", "/scratch/../protected", "/scratch/./uploads",
    "/scratch//uploads", "/scratch/uploads/", "C:\\synthetic", "/scratch\\uploads",
])
def test_n09_noncanonical_storage_path(path: str) -> None:
    payload = synthetic_contract()
    payload["storage"]["root_path"] = path
    assert_rejected(payload, ErrorCode.STORAGE_MISMATCH)


@pytest.mark.parametrize("capability", list(Capability))
def test_n10_missing_required_capability(capability: Capability) -> None:
    payload = synthetic_contract()
    payload["capabilities"].remove(capability.value)
    assert_rejected(payload, ErrorCode.MISSING_CAPABILITY,
                    required_capabilities=(capability,))


@pytest.mark.parametrize("section", [None, "postgres", "redis", "queues", "storage"])
def test_n11_unsupported_fields(section: str | None) -> None:
    payload = synthetic_contract()
    target = payload if section is None else payload[section]
    target["trusted"] = True
    assert_rejected(payload, ErrorCode.UNSUPPORTED_FIELD)


@pytest.mark.parametrize("change", ["duplicate", "wrong_owner", "wrong_kind", "extra"])
def test_n11_inconsistent_ownership(change: str) -> None:
    payload = synthetic_contract()
    if change == "duplicate":
        payload["ownership"][1] = deepcopy(payload["ownership"][0])
    elif change == "wrong_owner":
        payload["ownership"][0]["run_id"] = "another-run"
    elif change == "wrong_kind":
        payload["ownership"][0]["kind"] = "redis"
    else:
        payload["ownership"].append(deepcopy(payload["ownership"][0]))
    assert_rejected(payload, ErrorCode.OWNERSHIP_MISMATCH)


def test_n11_resource_id_reused_across_kinds() -> None:
    payload = synthetic_contract()
    payload["storage"]["resource_id"] = payload["postgres"]["resource_id"]
    assert_rejected(payload, ErrorCode.OWNERSHIP_MISMATCH)


def test_n11_unknown_capability() -> None:
    payload = synthetic_contract()
    payload["capabilities"].append("execution.authorized")
    assert_rejected(payload, ErrorCode.UNSUPPORTED_CAPABILITY)


@pytest.mark.parametrize("field", ["database_url_file", "signature", "digest", "safe"])
def test_n11_trust_claims_or_target_overrides_are_not_policy_fields(field: str) -> None:
    payload = synthetic_contract()
    payload[field] = "synthetic-claim"
    assert_rejected(payload, ErrorCode.UNSUPPORTED_FIELD)


@pytest.mark.parametrize("section", ["postgres", "redis", "storage"])
def test_missing_resource_identity_field(section: str) -> None:
    payload = synthetic_contract()
    key = "instance_id" if section == "redis" else "resource_id"
    del payload[section][key]
    assert_rejected(payload, ErrorCode.INVALID_STRUCTURE)


def test_duplicate_capability_is_rejected() -> None:
    payload = synthetic_contract()
    payload["capabilities"].append(payload["capabilities"][0])
    assert_rejected(payload, ErrorCode.INVALID_STRUCTURE)


def test_wrong_contract_structure_is_rejected() -> None:
    payload = synthetic_contract()
    payload["ownership"] = "not-a-list"
    assert_rejected(payload, ErrorCode.INVALID_STRUCTURE)


def test_n12_structural_validity_never_establishes_trust() -> None:
    result = validate_contract(synthetic_contract(), now=NOW)
    assert result.structural_status == PolicyStatus.STRUCTURALLY_VALID
    assert result.trust_status == PolicyStatus.TRUST_NOT_ESTABLISHED
    assert result.execution_status == PolicyStatus.EXECUTION_NOT_AUTHORIZED
    assert not hasattr(result, "safe")


def test_p01_consistent_contract_without_input_mutation() -> None:
    payload = synthetic_contract()
    original = deepcopy(payload)
    result = validate_contract(payload, now=NOW, required_capabilities=tuple(Capability))
    assert result.contract.run_id == "synthetic-run"
    assert payload == original
    payload["queues"]["worker_queues"].append("later-mutation")
    assert result.contract.queues.worker_queues == ("default", "documents")


def test_p02_matching_database_bindings() -> None:
    payload = synthetic_contract()
    contract = validate_contract(payload, now=NOW).contract
    assert validate_database_bindings(contract, migration=payload["postgres"],
                                      session=payload["postgres"],
                                      cleanup=payload["postgres"]) is None


def test_p03_matching_redis_queue_and_storage_bindings() -> None:
    payload = synthetic_contract()
    contract = validate_contract(payload, now=NOW).contract
    assert validate_redis_binding(contract, payload["redis"]) is None
    payload["queues"]["worker_queues"].reverse()
    assert validate_queue_binding(contract, payload["queues"]) is None
    assert validate_storage_binding(contract, payload["storage"]) is None


def test_p04_valid_lease_at_issue_time() -> None:
    payload = synthetic_contract()
    result = validate_contract(payload, now=payload["issued_at"])
    assert result.contract.issued_at < result.contract.expires_at


@pytest.mark.parametrize("change,code", [
    ("future", ErrorCode.LEASE_NOT_STARTED),
    ("reversed", ErrorCode.INVALID_LEASE),
    ("naive", ErrorCode.INVALID_LEASE),
])
def test_lease_rejections(change: str, code: ErrorCode) -> None:
    payload = synthetic_contract()
    if change == "future":
        payload["issued_at"] = NOW + timedelta(seconds=1)
    elif change == "reversed":
        payload["expires_at"] = payload["issued_at"]
    else:
        payload["issued_at"] = NOW.replace(tzinfo=None)
    assert_rejected(payload, code)


def test_p05_formatted_errors_never_include_input_secrets() -> None:
    synthetic_secret = "synthetic-password-do-not-log"
    payload = synthetic_contract()
    payload["postgres"]["resource_id"] = (
        f"postgresql://synthetic:{synthetic_secret}@invalid.example/synthetic"
    )
    with pytest.raises(PolicyViolation) as caught:
        validate_contract(payload, now=NOW)
    assert caught.value.code == ErrorCode.MISSING_IDENTITY
    assert synthetic_secret not in str(caught.value)
    assert synthetic_secret not in repr(caught.value)
    result = validate_contract(synthetic_contract(), now=NOW)
    assert "synthetic-run" not in repr(result)
    assert "/scratch/uploads" not in repr(result.contract.storage)


def test_n13_lower_bound_utc_conversion_overflow() -> None:
    payload = synthetic_contract()
    payload["issued_at"] = datetime.min.replace(tzinfo=timezone(timedelta(hours=1)))
    assert_rejected(payload, ErrorCode.INVALID_LEASE)


def test_n14_upper_bound_utc_conversion_overflow() -> None:
    payload = synthetic_contract()
    payload["expires_at"] = datetime.max.replace(tzinfo=timezone(timedelta(hours=-1)))
    assert_rejected(payload, ErrorCode.INVALID_LEASE)


def test_p06_equivalent_instants_normalize_to_utc() -> None:
    utc_payload = synthetic_contract()
    offset_payload = deepcopy(utc_payload)
    offset = timezone(timedelta(hours=1))
    offset_payload["issued_at"] = utc_payload["issued_at"].astimezone(offset)
    offset_payload["expires_at"] = utc_payload["expires_at"].astimezone(offset)

    utc_result = validate_contract(utc_payload, now=NOW)
    offset_result = validate_contract(offset_payload, now=NOW.astimezone(offset))

    assert offset_result.contract.issued_at == utc_result.contract.issued_at
    assert offset_result.contract.expires_at == utc_result.contract.expires_at
    assert offset_result.contract.issued_at.tzinfo is timezone.utc
    assert offset_result.contract.expires_at.tzinfo is timezone.utc


def test_p07_lease_interval_keeps_inclusive_start_and_exclusive_end() -> None:
    payload = synthetic_contract()
    at_start = validate_contract(payload, now=payload["issued_at"])
    before_end = validate_contract(
        payload, now=payload["expires_at"] - timedelta(microseconds=1)
    )
    assert at_start.structural_status == PolicyStatus.STRUCTURALLY_VALID
    assert before_end.structural_status == PolicyStatus.STRUCTURALLY_VALID

    with pytest.raises(PolicyViolation) as caught:
        validate_contract(payload, now=payload["expires_at"])
    assert caught.value.code == ErrorCode.LEASE_EXPIRED
    assert str(caught.value) == ErrorCode.LEASE_EXPIRED.value


def test_naive_now_is_rejected() -> None:
    with pytest.raises(PolicyViolation) as caught:
        validate_contract(synthetic_contract(), now=NOW.replace(tzinfo=None))
    assert caught.value.code == ErrorCode.INVALID_LEASE
    assert str(caught.value) == ErrorCode.INVALID_LEASE.value
