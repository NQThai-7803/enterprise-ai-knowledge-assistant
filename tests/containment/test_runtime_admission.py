"""Synthetic interface assertions only. Fake replies are NOT authentication.

No resource access. Do not run through the existing unsafe root pytest harness.
"""

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from types import MappingProxyType
from typing import Any

import pytest

from tests.containment_guard import (
    Capability,
    ErrorCode,
    PolicyStatus,
    PolicyViolation,
    validate_contract,
)
from tests.containment_runtime import (
    AdmissionCode,
    AdmissionRejected,
    ExecutionIdentity,
    LaunchContext,
    OperationReceipt,
    review_admission,
)

NOW = datetime(2030, 1, 1, tzinfo=UTC)


def projection() -> dict[str, Any]:
    return {
        "contract_version": "1", "policy_version": "e00-p1-v1",
        "run_id": "synthetic-run", "sandbox_id": "synthetic-sandbox",
        "lease_id": "synthetic-lease",
        "issued_at": NOW - timedelta(minutes=1),
        "expires_at": NOW + timedelta(minutes=5),
        "postgres": {"resource_id": "db-instance", "database": "synthetic_db",
                     "role": "synthetic_role", "schema": "public"},
        "redis": {"instance_id": "redis-instance", "broker_instance_id": "redis-instance",
                  "backend_instance_id": "redis-instance",
                  "rate_limit_instance_id": "redis-instance",
                  "broker_db": 1, "backend_db": 2, "rate_limit_db": 0},
        "queues": {"default_queue": "default", "document_queue": "documents",
                   "worker_queues": ["default", "documents"]},
        "storage": {"resource_id": "volume", "root_id": "uploads",
                    "root_path": "/scratch/uploads"},
        "ownership": [
            {"resource_id": resource_id, "kind": kind,
             "run_id": "synthetic-run", "sandbox_id": "synthetic-sandbox"}
            for resource_id, kind in (("db-instance", "postgres"),
                                      ("redis-instance", "redis"), ("volume", "storage"))
        ],
        "capabilities": [item.value for item in Capability],
    }


class FakeBridge:
    """Memory-only scenario model, never an authenticated bridge implementation."""

    def __init__(self, context: LaunchContext) -> None:
        self.context = context
        self.provenance = True
        self.attestation = True
        self.authorization = True
        self.accept_receipt = True
        self.spent: set[str] = set()

    def get_context(self) -> LaunchContext:
        return self.context

    def verify_provenance(
        self, context: LaunchContext, expected: ExecutionIdentity, now: datetime
    ) -> bool:
        return self.provenance

    def attest_resources(self, context: LaunchContext, now: datetime) -> bool:
        return self.attestation

    def execution_authorized(
        self, context: LaunchContext, operation: str, now: datetime
    ) -> bool:
        return self.authorization

    def consume_receipt(
        self, context: LaunchContext, receipt: OperationReceipt, now: datetime
    ) -> bool:
        if not self.accept_receipt or receipt.receipt_id in self.spent:
            return False
        self.spent.add(receipt.receipt_id)
        return True


def scenario() -> dict[str, Any]:
    identity = ExecutionIdentity("synthetic-run", "synthetic-sandbox", "synthetic-audience",
                                 "synthetic-nonce", "synthetic-source", "e00-p1-v1",
                                 "synthetic-launch")
    payload = projection()
    context = LaunchContext("1", identity, "synthetic-manifest", payload)
    receipt = OperationReceipt(
        "1", "synthetic-receipt", identity, context.manifest_id, "synthetic-lease",
        "db.cleanup", "db-instance", NOW - timedelta(seconds=1), NOW + timedelta(seconds=30),
    )
    return {"bridge": FakeBridge(context), "expected": identity, "operation": "db.cleanup",
            "observed": deepcopy(payload["postgres"]), "receipt": receipt, "now": NOW}


def reject(case: dict[str, Any], code: AdmissionCode) -> None:
    with pytest.raises(AdmissionRejected) as caught:
        review_admission(**case)
    assert caught.value.code == code
    assert str(caught.value) == code.value


def test_missing_bridge() -> None:
    case = scenario()
    case["bridge"] = None
    reject(case, AdmissionCode.BRIDGE_MISSING)


def test_blank_context_identity() -> None:
    case = scenario()
    bridge = case["bridge"]
    bridge.context = replace(bridge.context, identity=replace(case["expected"], audience=""))
    reject(case, AdmissionCode.INVALID_CONTEXT)


def test_invalid_expected_identity() -> None:
    case = scenario()
    case["expected"] = replace(case["expected"], nonce="")
    reject(case, AdmissionCode.INVALID_CONTEXT)


def test_unsupported_context_interface() -> None:
    case = scenario()
    case["bridge"].context = replace(case["bridge"].context, interface_version="unsupported")
    reject(case, AdmissionCode.INVALID_CONTEXT)


@pytest.mark.parametrize("field", ["run_id", "sandbox_id", "audience", "nonce",
                                   "source_id", "policy_id", "launch_id"])
def test_wrong_execution_identity(field: str) -> None:
    case = scenario()
    bridge = case["bridge"]
    bridge.context = replace(bridge.context, identity=replace(case["expected"], **{field: "other"}))
    reject(case, AdmissionCode.IDENTITY_MISMATCH)


def test_expired_lease_reuses_p1() -> None:
    case = scenario()
    case["bridge"].context.projection["expires_at"] = NOW
    with pytest.raises(PolicyViolation) as caught:
        review_admission(**case)
    assert caught.value.code == ErrorCode.LEASE_EXPIRED


def test_missing_operation_capability_reuses_p1() -> None:
    case = scenario()
    case["bridge"].context.projection["capabilities"] = []
    with pytest.raises(PolicyViolation) as caught:
        review_admission(**case)
    assert caught.value.code == ErrorCode.MISSING_CAPABILITY


def test_unsupported_capability_reuses_p1() -> None:
    case = scenario()
    case["bridge"].context.projection["capabilities"] = ["unsafe.execute"]
    with pytest.raises(PolicyViolation) as caught:
        review_admission(**case)
    assert caught.value.code == ErrorCode.UNSUPPORTED_CAPABILITY


def test_database_binding_mismatch_reuses_p1() -> None:
    case = scenario()
    case["observed"]["resource_id"] = "other-db"
    with pytest.raises(PolicyViolation) as caught:
        review_admission(**case)
    assert caught.value.code == ErrorCode.DATABASE_MISMATCH


@pytest.mark.parametrize("field,value", [
    ("identity", ExecutionIdentity("other-run", "synthetic-sandbox", "synthetic-audience",
                                   "synthetic-nonce", "synthetic-source", "e00-p1-v1",
                                   "synthetic-launch")),
    ("manifest_id", "other-manifest"), ("lease_id", "other-lease"),
    ("operation", "db.migrate"), ("resource_id", "other-db"),
])
def test_receipt_binding_mismatch(field: str, value: object) -> None:
    case = scenario()
    case["receipt"] = replace(case["receipt"], **{field: value})
    reject(case, AdmissionCode.RECEIPT_MISMATCH)


@pytest.mark.parametrize("field,value", [
    ("expires_at", NOW), ("issued_at", NOW + timedelta(seconds=1)),
    ("expires_at", NOW + timedelta(minutes=6)),
])
def test_stale_or_out_of_lease_receipt(field: str, value: datetime) -> None:
    case = scenario()
    case["receipt"] = replace(case["receipt"], **{field: value})
    reject(case, AdmissionCode.RECEIPT_STALE)


@pytest.mark.parametrize("field,value", [
    ("interface_version", "unsupported"), ("receipt_id", ""),
    ("issued_at", NOW.replace(tzinfo=None)),
    ("issued_at", datetime.min.replace(tzinfo=timezone(timedelta(hours=1)))),
    ("expires_at", datetime.max.replace(tzinfo=timezone(timedelta(hours=-1)))),
])
def test_invalid_receipt(field: str, value: object) -> None:
    case = scenario()
    case["receipt"] = replace(case["receipt"], **{field: value})
    reject(case, AdmissionCode.INVALID_RECEIPT)


def test_replayed_receipt_is_rejected_by_fake_ledger_model() -> None:
    case = scenario()
    review_admission(**case)
    reject(case, AdmissionCode.RECEIPT_NOT_ACCEPTED)


def test_forged_receipt_rejected_by_bridge_reply() -> None:
    case = scenario()
    case["bridge"].accept_receipt = False
    reject(case, AdmissionCode.RECEIPT_NOT_ACCEPTED)


def test_unknown_operation() -> None:
    case = scenario()
    case["operation"] = "destroy.production"
    reject(case, AdmissionCode.UNKNOWN_OPERATION)


@pytest.mark.parametrize("attribute,code", [
    ("provenance", AdmissionCode.PROVENANCE_NOT_VERIFIED),
    ("attestation", AdmissionCode.RESOURCE_NOT_ATTESTED),
    ("authorization", AdmissionCode.EXECUTION_NOT_AUTHORIZED),
])
def test_structurally_valid_projection_does_not_replace_external_checks(
    attribute: str, code: AdmissionCode
) -> None:
    case = scenario()
    setattr(case["bridge"], attribute, False)
    reject(case, code)


@pytest.mark.parametrize("operation", [item.value for item in Capability])
def test_consistent_synthetic_interface_never_grants_execution(operation: str) -> None:
    case = scenario()
    payload = case["bridge"].context.projection
    case["operation"] = operation
    if operation.startswith("db."):
        resource_id, observed = "db-instance", payload["postgres"]
    elif operation == "storage.write":
        resource_id, observed = "volume", payload["storage"]
    else:
        resource_id = "redis-instance"
        observed = {"redis": payload["redis"], "queues": payload["queues"]}
    case["observed"] = deepcopy(observed)
    case["receipt"] = replace(case["receipt"], operation=operation, resource_id=resource_id)
    original_payload = deepcopy(payload)
    original_observed = deepcopy(case["observed"])
    original_receipt = case["receipt"]
    result = review_admission(**case)
    assert result.interface_status == "INTERFACE_CONSISTENT"
    assert result.policy.structural_status == PolicyStatus.STRUCTURALLY_VALID
    assert result.trust_status == PolicyStatus.TRUST_NOT_ESTABLISHED
    assert result.execution_status == PolicyStatus.EXECUTION_NOT_AUTHORIZED
    assert payload == original_payload
    assert case["observed"] == original_observed
    assert case["receipt"] == original_receipt


def test_invalid_input_is_not_mutated_or_consumed() -> None:
    case = scenario()
    case["observed"]["schema"] = "different"
    original_payload = deepcopy(case["bridge"].context.projection)
    original_observed = deepcopy(case["observed"])
    with pytest.raises(PolicyViolation):
        review_admission(**case)
    assert case["bridge"].context.projection == original_payload
    assert case["observed"] == original_observed
    assert case["bridge"].spent == set()


def test_unexpected_bridge_error_is_sanitized() -> None:
    class BrokenBridge(FakeBridge):
        def get_context(self) -> LaunchContext:
            raise RuntimeError("synthetic-secret-url-do-not-log")

    case = scenario()
    case["bridge"] = BrokenBridge(case["bridge"].context)
    reject(case, AdmissionCode.BRIDGE_FAILURE)


def test_typed_bridge_error_is_rebuilt_without_raw_message() -> None:
    class BrokenBridge(FakeBridge):
        def get_context(self) -> LaunchContext:
            error = AdmissionRejected(AdmissionCode.INVALID_CONTEXT)
            error.args = ("synthetic-secret-url-do-not-log",)
            raise error

    case = scenario()
    case["bridge"] = BrokenBridge(case["bridge"].context)
    reject(case, AdmissionCode.INVALID_CONTEXT)


def test_s01_original_projection_mutation_after_snapshot_is_isolated() -> None:
    class AliasBridge(FakeBridge):
        def verify_provenance(self, context, expected, now) -> bool:
            self.context.projection["postgres"]["database"] = "changed-after-snapshot"
            assert context.projection["postgres"]["database"] == "synthetic_db"
            return True

    case = scenario()
    case["bridge"] = AliasBridge(case["bridge"].context)
    result = review_admission(**case)
    assert result.policy.contract.postgres.database == "synthetic_db"
    assert case["bridge"].context.projection["postgres"]["database"] == "changed-after-snapshot"


def test_s02_nested_dict_and_list_aliases_are_isolated() -> None:
    class AliasBridge(FakeBridge):
        def verify_provenance(self, context, expected, now) -> bool:
            self.context.projection["queues"]["worker_queues"].append("later")
            self.context.projection["ownership"][0]["run_id"] = "later-run"
            self.context.projection["capabilities"].clear()
            assert context.projection["queues"]["worker_queues"] == ("default", "documents")
            assert context.projection["ownership"][0]["run_id"] == expected.run_id
            assert "db.cleanup" in context.projection["capabilities"]
            return True

    case = scenario()
    case["bridge"] = AliasBridge(case["bridge"].context)
    result = review_admission(**case)
    assert Capability.DB_CLEANUP in result.policy.contract.capabilities


def test_s03_bridge_cannot_mutate_nested_projection_or_consume_after_failure() -> None:
    class MutatingBridge(FakeBridge):
        def verify_provenance(self, context, expected, now) -> bool:
            context.projection["postgres"]["database"] = "attempted-change"
            return True

    case = scenario()
    case["bridge"] = MutatingBridge(case["bridge"].context)
    original = deepcopy(case["bridge"].context.projection)
    reject(case, AdmissionCode.BRIDGE_FAILURE)
    assert case["bridge"].context.projection == original
    assert case["bridge"].spent == set()


@pytest.mark.parametrize("operation,section,field,changed", [
    ("db.cleanup", "postgres", "database", "other_database"),
    ("redis.purge", "redis", "broker_db", 7),
    ("storage.write", "storage", "root_path", "/scratch/other"),
])
def test_s04_external_resource_alias_changes_do_not_change_checked_snapshot(
    operation: str, section: str, field: str, changed: object
) -> None:
    case = scenario()
    payload = case["bridge"].context.projection
    if section == "redis":
        observed = {"redis": payload["redis"], "queues": payload["queues"]}
        resource_id = "redis-instance"
    else:
        observed = payload[section]
        resource_id = "db-instance" if section == "postgres" else "volume"
    original_value = payload[section][field]

    class AliasBridge(FakeBridge):
        def verify_provenance(self, context, expected, now) -> bool:
            payload[section][field] = changed
            assert context.projection[section][field] == original_value
            return True

    case.update(bridge=AliasBridge(case["bridge"].context), operation=operation, observed=observed,
                receipt=replace(case["receipt"], operation=operation, resource_id=resource_id))
    result = review_admission(**case)
    assert result.interface_status == "INTERFACE_CONSISTENT"
    assert payload[section][field] == changed


def test_s04_observed_input_is_copied_before_get_context_callback() -> None:
    case = scenario()
    observed = case["observed"]

    class AliasBridge(FakeBridge):
        def get_context(self) -> LaunchContext:
            observed["database"] = "changed-by-get-context"
            return self.context

    case["bridge"] = AliasBridge(case["bridge"].context)
    result = review_admission(**case)
    assert result.policy.contract.postgres.database == "synthetic_db"
    assert observed["database"] == "changed-by-get-context"


def test_s05_all_bridge_checks_share_one_logical_snapshot() -> None:
    class RecordingBridge(FakeBridge):
        def __init__(self, context: LaunchContext) -> None:
            super().__init__(context)
            self.seen: list[LaunchContext] = []

        def verify_provenance(self, context, expected, now) -> bool:
            self.seen.append(context)
            return True

        def attest_resources(self, context, now) -> bool:
            self.seen.append(context)
            return True

        def execution_authorized(self, context, operation, now) -> bool:
            self.seen.append(context)
            return True

        def consume_receipt(self, context, receipt, now) -> bool:
            self.seen.append(context)
            assert receipt.identity == context.identity
            assert receipt.manifest_id == context.manifest_id
            assert receipt.lease_id == context.projection["lease_id"]
            return super().consume_receipt(context, receipt, now)

    case = scenario()
    bridge = RecordingBridge(case["bridge"].context)
    case["bridge"] = bridge
    result = review_admission(**case)
    assert len(bridge.seen) == 4
    assert all(context is bridge.seen[0] for context in bridge.seen)
    assert bridge.seen[0] is not bridge.context
    checked = validate_contract(bridge.seen[0].projection, now=NOW)
    assert checked.contract == result.policy.contract


@pytest.mark.parametrize("location", ["projection", "observed", "nested"])
def test_s06_custom_mapping_hooks_are_not_invoked(location: str) -> None:
    class HookMapping(Mapping):
        def __getitem__(self, key):
            raise AssertionError("custom mapping hook invoked")

        def __iter__(self):
            raise AssertionError("custom mapping hook invoked")

        def __len__(self):
            raise AssertionError("custom mapping hook invoked")

    case = scenario()
    if location == "projection":
        case["bridge"].context = replace(case["bridge"].context, projection=HookMapping())
    elif location == "observed":
        case["observed"] = HookMapping()
    else:
        case["bridge"].context.projection["postgres"] = HookMapping()
    reject(case, AdmissionCode.INVALID_CONTEXT)
    assert case["bridge"].spent == set()


def test_s06_custom_deepcopy_hook_is_never_called() -> None:
    class HookObject:
        def __deepcopy__(self, memo):
            raise AssertionError("deepcopy hook invoked")

    case = scenario()
    case["bridge"].context.projection["postgres"]["database"] = HookObject()
    reject(case, AdmissionCode.INVALID_CONTEXT)


def test_s06_input_proxy_cannot_hide_a_custom_mapping() -> None:
    class HookMapping(Mapping):
        def __getitem__(self, key):
            raise AssertionError("proxy mapping hook invoked")

        def __iter__(self):
            raise AssertionError("proxy mapping hook invoked")

        def __len__(self):
            raise AssertionError("proxy mapping hook invoked")

    case = scenario()
    case["observed"] = MappingProxyType(HookMapping())
    reject(case, AdmissionCode.INVALID_CONTEXT)


def test_s07_local_receipt_failure_does_not_consume() -> None:
    case = scenario()
    case["receipt"] = replace(case["receipt"], resource_id="wrong-resource")
    reject(case, AdmissionCode.RECEIPT_MISMATCH)
    assert case["bridge"].spent == set()


def test_s08_duplicate_receipt_remains_spent_in_same_fake_ledger() -> None:
    case = scenario()
    result = review_admission(**case)
    assert result.interface_status == "INTERFACE_CONSISTENT"
    assert case["bridge"].spent == {case["receipt"].receipt_id}
    reject(case, AdmissionCode.RECEIPT_NOT_ACCEPTED)


def test_s09_late_bridge_exception_is_sanitized() -> None:
    class BrokenBridge(FakeBridge):
        def attest_resources(self, context, now) -> bool:
            raise RuntimeError("synthetic-private-transport-message")

    case = scenario()
    case["bridge"] = BrokenBridge(case["bridge"].context)
    reject(case, AdmissionCode.BRIDGE_FAILURE)
    assert case["bridge"].spent == set()


@pytest.mark.parametrize("exception_type", [AdmissionRejected, PolicyViolation])
@pytest.mark.parametrize("malformed", ["missing_code", "wrong_code", "subclass"])
def test_s10_malformed_typed_errors_are_sanitized(exception_type, malformed: str) -> None:
    class BrokenBridge(FakeBridge):
        def get_context(self) -> LaunchContext:
            code = (AdmissionCode.INVALID_CONTEXT if exception_type is AdmissionRejected
                    else ErrorCode.INVALID_STRUCTURE)
            if malformed == "subclass":
                class DerivedError(exception_type):
                    @property
                    def code(self):
                        raise RuntimeError("synthetic-private-property-message")

                    @code.setter
                    def code(self, value):
                        pass

                error = DerivedError(code)
            else:
                error = exception_type(code)
                if malformed == "missing_code":
                    del error.code
                else:
                    error.code = "synthetic-private-code"
            error.args = ("synthetic-private-error-message",)
            raise error

    case = scenario()
    case["bridge"] = BrokenBridge(case["bridge"].context)
    reject(case, AdmissionCode.BRIDGE_FAILURE)


def test_s11_positive_snapshot_does_not_establish_trust_or_authority() -> None:
    result = review_admission(**scenario())
    assert result.interface_status == "INTERFACE_CONSISTENT"
    assert result.trust_status == PolicyStatus.TRUST_NOT_ESTABLISHED
    assert result.execution_status == PolicyStatus.EXECUTION_NOT_AUTHORIZED
    assert result.policy.trust_status == PolicyStatus.TRUST_NOT_ESTABLISHED
    assert result.policy.execution_status == PolicyStatus.EXECUTION_NOT_AUTHORIZED


def test_s12_frozen_projection_preserves_p1_public_semantics() -> None:
    class CheckingBridge(FakeBridge):
        def verify_provenance(self, context, expected, now) -> bool:
            pure = validate_contract(context.projection, now=now,
                                     required_capabilities=(Capability.DB_CLEANUP,))
            assert pure.contract.queues.worker_queues == ("default", "documents")
            assert pure.contract.issued_at == NOW - timedelta(minutes=1)
            assert pure.contract.expires_at == NOW + timedelta(minutes=5)
            assert pure.structural_status == PolicyStatus.STRUCTURALLY_VALID
            return True

    case = scenario()
    case["bridge"] = CheckingBridge(case["bridge"].context)
    result = review_admission(**case)
    assert result.policy.contract == validate_contract(projection(), now=NOW).contract
