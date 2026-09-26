"""One admission path for preflight and the trainer.

RUNE.PREFLIGHT_LAUNCH_PARITY(x) =
    effective_environment_hash(preflight)
    == effective_environment_hash(launch)
    AND admission_gate_sequence(preflight)
    == admission_gate_sequence(launch)
    AND admission_result(preflight)
    == admission_result(launch)

Controlled experiments (``HLX_EXPERIMENT_ID`` set) use ``CONTROLLED_RESERVE``.
A sealed evaluation reserve with zero training overlap satisfies the holdout
requirement. ``HLX_HOLDOUT_MANIFESTS`` does not. ``HLX_ALLOW_NO_HOLDOUT`` does
not. Legacy launches that are not controlled experiments still use
``require_holdout_for_training``.

``HLX_ADMISSION_ONLY=1`` is not part of the environment hash. The trainer
returns after these gates and does not construct an optimizer.

``TRAINING_READY`` exists only when all three are true: these scientific
gates passed, a sealed threshold authorization matches this experiment, and
admission returns ``ADMISSION_PASS``. Without that decision rule the status
stays ``PREREGISTERED`` and ``ready_to_train`` stays false. An admission pass
is not a training launch.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping

from .export import repo_root
from .holdout_guard import (
    HoldoutSpec,
    allow_no_holdout,
    load_holdout_spec,
    normalized_text_sha256,
    require_holdout_for_training,
)
from .identity_ledger import (
    RESERVE_LEDGER_ENV,
    IdentityLedger,
    derived_state,
)
from .selection_surface import row_id
from .train_input import (
    TrainInputAdmissionError,
    load_training_bundle,
    train_input_receipt,
)

CONTRACT_RESERVE = "CONTROLLED_RESERVE"
CONTRACT_MANIFEST = "LEGACY_MANIFEST"
CONTRACT_UNCONTROLLED = "UNCONTROLLED"
BINDING_SCHEMA = "hyperlex.reserve_binding.v1"
ADMISSION_ONLY_ENV = "HLX_ADMISSION_ONLY"
RESERVE_BINDING_ENV = "HLX_RESERVE_BINDING"
BASELINE_ENV = "HLX_BASELINE_ENV"
CANDIDATE_ENV = "HLX_CANDIDATE_ENV"
BEST_SHA_ENV = "HLX_BEST_SHA256"
BEST_WEIGHTS_ENV = "HLX_BEST_WEIGHTS"
TRUNK_SHA_ENV = "HLX_TRUNK_SHA256"
TRAIN_OUT_ENV = "HYPERLEX_TRAIN_OUT"
SELECT_METRIC_KEY = "HLX_SELECT_METRIC"
THRESHOLD_AUTHORIZATION_ENV = "HLX_THRESHOLD_AUTHORIZATION"
THRESHOLD_SCHEMA = "hyperlex.threshold_authorization.v1"
THRESHOLDS_BLOCKED = "BLOCKED_PENDING_OPERATOR_AUTHORIZATION"
REQUIRED_SLICES = ("classify", "classify_observed", "classify_non_none", "unbind_clean")

GATE_SEQUENCE = (
    "experiment_binding",
    "launch_gate",
    "holdout_reserve",
    "pinned_training_input",
    "train_reserve_disjointness",
    "single_variable",
    "best_trunk",
    "output_directory",
    "ready",
)

# Process environment that admission reads. ``HLX_ADMISSION_ONLY`` is omitted
# so a dry launch and preflight hash the same binding.
ENV_KEYS = (
    "HLX_EXPERIMENT_ID",
    "HLX_THRESHOLD_AUTHORIZATION",
    "HYPERLEX_ALLOW_TRAIN",
    "HLX_EVAL_RESERVE_LEDGER",
    "HLX_RESERVE_BINDING",
    "HLX_HOLDOUT_MANIFESTS",
    "HLX_ALLOW_NO_HOLDOUT",
    "HLX_TRAIN_EXPORT_PATH",
    "HLX_TRAIN_EXPORT_SHA256",
    "HLX_TRAIN_EXPORT_ROWS",
    "HLX_BASELINE_ENV",
    "HLX_CANDIDATE_ENV",
    "HLX_SELECT_METRIC",
    "HLX_BEST_SHA256",
    "HLX_BEST_WEIGHTS",
    "HLX_TRUNK_SHA256",
    "HYPERLEX_TRUNK_DIR",
    "HYPERLEX_TRAIN_OUT",
    "HYPERLEX_INCLUDE_LIVE",
)

METADATA_KEYS = frozenset(
    {
        "HLX_EXPERIMENT_ID",
        "HYPERLEX_TRAIN_OUT",
        "HYPERLEX_UNBIND_RESIDUAL_DUMP",
        "HLX_EVAL_RESERVE_LEDGER",
        "HLX_RESERVE_BINDING",
        "HLX_BASELINE_ENV",
        "HLX_CANDIDATE_ENV",
    }
)
LAUNCH_OVERLAY_KEYS = frozenset({"HYPERLEX_ALLOW_TRAIN", ADMISSION_ONLY_ENV})

MISSING_RESERVE_REASON = (
    "ADMISSION FAIL: HYPERLEX_ALLOW_TRAIN=1 but no sealed evaluation reserve. "
    "Set HLX_EVAL_RESERVE_LEDGER to the sealed ledger. "
    "CONTROLLED_RESERVE does not accept a legacy holdout manifest."
)


class AdmissionError(SystemExit):
    """Admission refused. ``SystemExit`` so the trainer CLI does not treat it as a crash."""

    def __init__(self, message: str, receipt: dict[str, Any]) -> None:
        super().__init__(message)
        self.receipt = receipt


class AdmissionResult:
    def __init__(
        self,
        *,
        ready: bool,
        status: str | None,
        admission_result: str,
        contract: str,
        launch_armed: bool,
        bundle: dict[str, Any] | None,
        holdout_spec: HoldoutSpec,
        input_receipt: dict[str, Any] | None,
        disjoint_receipt: dict[str, Any] | None,
        reserve_receipt: dict[str, Any] | None,
        receipt: dict[str, Any],
        error: str | None = None,
    ) -> None:
        self.ready = ready
        self.status = status
        self.admission_result = admission_result
        self.contract = contract
        self.launch_armed = launch_armed
        self.bundle = bundle
        self.holdout_spec = holdout_spec
        self.input_receipt = input_receipt
        self.disjoint_receipt = disjoint_receipt
        self.reserve_receipt = reserve_receipt
        self.receipt = receipt
        self.error = error


def effective_environment_material() -> dict[str, str | None]:
    """Admission environment. Absent variables are null. No timestamps."""
    return {key: os.environ.get(key) for key in ENV_KEYS}


def effective_environment_hash() -> str:
    payload = json.dumps(
        effective_environment_material(),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _empty_spec() -> HoldoutSpec:
    return HoldoutSpec(frozenset(), frozenset(), ())


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_env_file(path: Path, what: str) -> dict[str, str]:
    if not path.is_file():
        raise AdmissionError(
            f"ADMISSION FAIL: {what} is missing: {path}",
            {},
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AdmissionError(f"ADMISSION FAIL: {what} is not JSON", {}) from exc
    if not isinstance(payload, dict):
        raise AdmissionError(f"ADMISSION FAIL: {what} must be a JSON object", {})
    out: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise AdmissionError(
                f"ADMISSION FAIL: {what} values must be strings",
                {},
            )
        out[key] = value
    return out


def admit_training_run(
    *,
    include_live: bool = False,
    live_store: Path | None = None,
    export_dataset: Callable[..., dict[str, Any]] | None = None,
    trunk: Path | None = None,
    out_dir: Path | None = None,
) -> AdmissionResult:
    """Run the trainer admission gates. Does not construct an optimizer."""
    if export_dataset is None:
        from .export import export_dataset as export_dataset

    experiment_id = os.environ.get("HLX_EXPERIMENT_ID", "").strip()
    controlled = bool(experiment_id)
    launch = os.environ.get("HYPERLEX_ALLOW_TRAIN") == "1"
    contract = CONTRACT_RESERVE if controlled else (CONTRACT_MANIFEST if launch else CONTRACT_UNCONTROLLED)
    ctx = _Context(
        include_live=include_live,
        live_store=live_store,
        export_dataset=export_dataset,
        trunk=trunk,
        out_dir=out_dir,
        experiment_id=experiment_id,
        controlled=controlled,
        launch=launch,
        contract=contract,
    )
    if not launch:
        return _admit_unarmed(ctx)
    if not controlled:
        return _admit_legacy_launch(ctx)
    return _admit_controlled(ctx)


class _Context:
    def __init__(self, **kwargs: Any) -> None:
        self.__dict__.update(kwargs)
        self.env_hash = effective_environment_hash()
        self.failed_gate: str | None = None

    def receipt(self, **fields: Any) -> dict[str, Any]:
        payload = {
            "schema": "hyperlex.admission.v1",
            "controlled_holdout_contract": self.contract,
            "admission_gate_sequence": list(GATE_SEQUENCE),
            "failed_gate": self.failed_gate,
            "environment_hash": self.env_hash,
            "experiment_id": self.experiment_id or None,
            "launch_armed": self.launch,
            "training_started": False,
            "epochs": 0,
            "gradient_steps": 0,
            "optimizer_loaded": False,
            "best_moved": False,
            "hlx_allow_no_holdout": allow_no_holdout(),
            "holdout_admitted": False,
        }
        payload.update(fields)
        return payload

    def fail(self, gate: str, message: str, **fields: Any) -> None:
        self.failed_gate = gate
        raise AdmissionError(message, self.receipt(**fields))


def _load_bundle(ctx: _Context) -> dict[str, Any]:
    try:
        return load_training_bundle(
            repo_root(),
            include_live=ctx.include_live,
            live_store=ctx.live_store,
            export_dataset=ctx.export_dataset,
        )
    except TrainInputAdmissionError as exc:
        ctx.fail("pinned_training_input", str(exc))
        raise AssertionError("unreachable") from exc


def _unarmed_result(ctx: _Context, bundle: dict[str, Any], spec: HoldoutSpec) -> AdmissionResult:
    proof = train_input_receipt(bundle)
    status = "NOT_READY" if ctx.controlled else None
    receipt = ctx.receipt(
        admission_result="NOT_ARMED",
        status=status,
        ready_to_train=False,
        **proof,
    )
    return AdmissionResult(
        ready=False,
        status=status,
        admission_result="NOT_ARMED",
        contract=ctx.contract,
        launch_armed=False,
        bundle=bundle,
        holdout_spec=spec,
        input_receipt=proof,
        disjoint_receipt=None,
        reserve_receipt=None,
        receipt=receipt,
    )


def _admit_unarmed(ctx: _Context) -> AdmissionResult:
    """ALLOW_TRAIN is unset. Load a pinned bundle when one is declared.

    This is not launch admission. Callers that still execute ``run_loop``
    keep the previous non-launch behavior.
    """
    bundle = _load_bundle(ctx)
    spec = load_holdout_spec()
    from .holdout_guard import assert_pinned_holdout_disjoint

    if ctx.experiment_id:
        assert_pinned_holdout_disjoint(bundle["rows"], spec)
    ledger = os.environ.get(RESERVE_LEDGER_ENV, "").strip()
    if ledger:
        from .identity_ledger import assert_training_disjoint_from_reserve

        assert_training_disjoint_from_reserve(bundle["rows"], IdentityLedger.load(ledger))
    return _unarmed_result(ctx, bundle, spec)


def _admit_legacy_launch(ctx: _Context) -> AdmissionResult:
    try:
        spec = require_holdout_for_training()
    except SystemExit as exc:
        ctx.fail("holdout_reserve", str(exc))
        raise AssertionError("unreachable") from exc
    bundle = _load_bundle(ctx)
    proof = train_input_receipt(bundle)
    ready = _trunk_config_ok(ctx.trunk)
    receipt = ctx.receipt(
        admission_result="ADMISSION_PASS" if ready else "NOT_READY",
        status=None,
        ready_to_train=ready,
        holdout_admitted=bool(spec.manifests) or allow_no_holdout(),
        **proof,
    )
    return AdmissionResult(
        ready=ready,
        status=None,
        admission_result=receipt["admission_result"],
        contract=CONTRACT_MANIFEST,
        launch_armed=True,
        bundle=bundle,
        holdout_spec=spec,
        input_receipt=proof,
        disjoint_receipt=None,
        reserve_receipt=None,
        receipt=receipt,
    )


def _trunk_config_ok(trunk: Path | None) -> bool:
    return bool(trunk) and trunk.is_dir() and (trunk / "config.json").is_file()


def _admit_controlled(ctx: _Context) -> AdmissionResult:
    _gate_experiment(ctx)
    _gate_launch(ctx)
    ledger, binding = _gate_reserve(ctx)
    bundle = _load_bundle(ctx)
    proof = train_input_receipt(bundle)
    if proof["training_input_mode"] != "PINNED_EXPORT" or proof["live_export_generation_enabled"]:
        ctx.fail(
            "pinned_training_input",
            "ADMISSION FAIL: controlled experiment did not consume a pinned export",
            **proof,
        )
    overlap = _gate_disjoint(ctx, bundle, ledger)
    _gate_single_variable(ctx)
    _gate_best_trunk(ctx)
    _gate_output(ctx)
    decision_sealed, decision_state = _decision_authorization(ctx)
    status = "TRAINING_READY" if decision_sealed else "PREREGISTERED"
    spec = _empty_spec()
    disjoint = {
        "holdout_train_row_id_overlap": 0,
        "holdout_train_text_hash_overlap": 0,
        "holdout_filter_training_rows_removed": 0,
        "holdout_training_disjoint": True,
    }
    receipt = ctx.receipt(
        admission_result="ADMISSION_PASS",
        status=status,
        ready_to_train=decision_sealed,
        scientific_contract_sealed=True,
        decision_rule_sealed=decision_sealed,
        decision_threshold_state=decision_state,
        training_launch_authorized=False,
        holdout_admitted=True,
        holdout_state="EVAL_RESERVE",
        holdout_experiment_id=ctx.experiment_id,
        holdout_manifest_sha256=None,
        reserve_lifecycle="EVAL_RESERVE",
        reserve_events_sha256=binding["ledger_events_sha256"],
        reserve_counts=binding["counts"],
        **proof,
        **overlap,
        **disjoint,
    )
    return AdmissionResult(
        ready=True,
        status=status,
        admission_result="ADMISSION_PASS",
        contract=CONTRACT_RESERVE,
        launch_armed=True,
        bundle=bundle,
        holdout_spec=spec,
        input_receipt=proof,
        disjoint_receipt=disjoint,
        reserve_receipt=overlap,
        receipt=receipt,
    )


def _decision_authorization(ctx: _Context) -> tuple[bool, str]:
    """A missing authorization stays blocked. A bad file fails closed."""
    raw = os.environ.get(THRESHOLD_AUTHORIZATION_ENV, "").strip()
    if not raw:
        return False, THRESHOLDS_BLOCKED
    path = Path(raw)
    if not path.is_file():
        ctx.fail("ready", "ADMISSION FAIL: threshold authorization path is not a file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        ctx.fail("ready", "ADMISSION FAIL: threshold authorization is not JSON")
    if not isinstance(payload, dict) or payload.get("schema") != THRESHOLD_SCHEMA:
        ctx.fail(
            "ready",
            "ADMISSION FAIL: threshold authorization schema is not " + THRESHOLD_SCHEMA,
        )
    if payload.get("experiment_id") != ctx.experiment_id:
        ctx.fail(
            "ready",
            "ADMISSION FAIL: threshold authorization experiment_id does not match",
        )
    if payload.get("sealed") is not True:
        ctx.fail("ready", "ADMISSION FAIL: threshold authorization is not sealed")
    thresholds = payload.get("decision_thresholds")
    if not isinstance(thresholds, dict) or not thresholds:
        ctx.fail(
            "ready",
            "ADMISSION FAIL: threshold authorization does not seal numeric decision thresholds",
        )
    for key, value in thresholds.items():
        if not isinstance(key, str) or isinstance(value, bool) or not isinstance(value, (int, float)):
            ctx.fail(
                "ready",
                "ADMISSION FAIL: threshold authorization does not seal numeric decision thresholds",
            )
    return True, "SEALED"


def _gate_experiment(ctx: _Context) -> None:
    if os.environ.get("HLX_HOLDOUT_MANIFESTS", "").strip():
        ctx.fail(
            "experiment_binding",
            "ADMISSION FAIL: legacy holdout manifest is not the CONTROLLED_RESERVE contract",
        )
    if allow_no_holdout():
        ctx.fail(
            "experiment_binding",
            "ADMISSION FAIL: HLX_ALLOW_NO_HOLDOUT does not admit a controlled experiment",
        )


def _gate_launch(ctx: _Context) -> None:
    if not _trunk_config_ok(ctx.trunk):
        ctx.fail(
            "launch_gate",
            "ADMISSION FAIL: trunk config is missing",
        )


def _gate_reserve(ctx: _Context) -> tuple[IdentityLedger, dict[str, Any]]:
    raw_ledger = os.environ.get(RESERVE_LEDGER_ENV, "").strip()
    raw_binding = os.environ.get(RESERVE_BINDING_ENV, "").strip()
    if not raw_ledger or not raw_binding:
        ctx.fail("holdout_reserve", MISSING_RESERVE_REASON)
    ledger_dir = Path(raw_ledger)
    binding_path = Path(raw_binding)
    if not (ledger_dir / "events.jsonl").is_file():
        ctx.fail("holdout_reserve", MISSING_RESERVE_REASON)
    if not binding_path.is_file():
        ctx.fail("holdout_reserve", MISSING_RESERVE_REASON)
    try:
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        ctx.fail("holdout_reserve", "ADMISSION FAIL: reserve binding is not JSON")
    if not isinstance(binding, dict) or binding.get("schema") != BINDING_SCHEMA:
        ctx.fail("holdout_reserve", "ADMISSION FAIL: reserve binding schema is not sealed")
    if binding.get("experiment_id") != ctx.experiment_id:
        ctx.fail(
            "holdout_reserve",
            "ADMISSION FAIL: reserve binding experiment_id does not match HLX_EXPERIMENT_ID",
        )
    if binding.get("lifecycle") != "EVAL_RESERVE":
        ctx.fail(
            "holdout_reserve",
            "ADMISSION FAIL: reserve lifecycle is not EVAL_RESERVE",
        )
    actual_events = _sha256_file(ledger_dir / "events.jsonl")
    if binding.get("ledger_events_sha256") != actual_events:
        ctx.fail(
            "holdout_reserve",
            "ADMISSION FAIL: reserve ledger events sha256 does not match the binding",
        )
    ledger = IdentityLedger.load(ledger_dir)
    counts = ledger.reserve_counts()
    expected_counts = binding.get("counts")
    if not isinstance(expected_counts, dict):
        ctx.fail("holdout_reserve", "ADMISSION FAIL: reserve binding counts are missing")
    for key in REQUIRED_SLICES:
        if counts.get(key, 0) < 1:
            ctx.fail("holdout_reserve", f"ADMISSION FAIL: reserve slice {key} is absent")
        if int(expected_counts.get(key, -1)) != int(counts[key]):
            ctx.fail(
                "holdout_reserve",
                f"ADMISSION FAIL: reserve slice {key} does not match the binding",
            )
    # The sealed reserve is EVAL_RESERVE. Historical spent and abandoned
    # identities share the ledger and are not that reserve. An identity that
    # still carries evaluation_reserved but has moved off EVAL_RESERVE fails.
    reserved = [
        record
        for record in ledger.identities.values()
        if record.get("evaluation_reserved") or derived_state(record) == "EVAL_RESERVE"
    ]
    if not reserved:
        ctx.fail("holdout_reserve", "ADMISSION FAIL: sealed evaluation reserve has no identities")
    for record in reserved:
        state = derived_state(record)
        if state != "EVAL_RESERVE":
            ctx.fail(
                "holdout_reserve",
                f"ADMISSION FAIL: reserve lifecycle {state} is not EVAL_RESERVE",
            )
    if "identities" in binding and int(binding["identities"]) != len(reserved):
        ctx.fail("holdout_reserve", "ADMISSION FAIL: reserve identity count does not match the binding")
    return ledger, binding


def _gate_disjoint(ctx: _Context, bundle: Mapping[str, Any], ledger: IdentityLedger) -> dict[str, int]:
    reserved = [
        record
        for record in ledger.identities.values()
        if derived_state(record) == "EVAL_RESERVE"
    ]
    hashes = {record["normalized_text_sha256"] for record in reserved}
    ids: set[str] = set()
    for record in reserved:
        ids.update(str(item) for item in record.get("row_ids") or [])
    id_overlap = 0
    text_overlap = 0
    for row in bundle["rows"]:
        if row_id(row) in ids:
            id_overlap += 1
        if normalized_text_sha256(str(row.get("text") or "")) in hashes:
            text_overlap += 1
    if id_overlap or text_overlap:
        ctx.fail(
            "train_reserve_disjointness",
            "ADMISSION FAIL: training input overlaps the sealed reserve "
            f"(row_id_overlap={id_overlap}, text_hash_overlap={text_overlap})",
            reserve_train_row_id_overlap=id_overlap,
            reserve_train_text_hash_overlap=text_overlap,
            training_rows_removed=0,
        )
    return {
        "reserve_train_row_id_overlap": 0,
        "reserve_train_text_hash_overlap": 0,
        "training_rows_removed": 0,
    }


def _scientific_items(payload: Mapping[str, str]) -> dict[str, str]:
    return {key: value for key, value in payload.items() if key not in METADATA_KEYS and key not in LAUNCH_OVERLAY_KEYS}


def _gate_single_variable(ctx: _Context) -> None:
    baseline_path = os.environ.get(BASELINE_ENV, "").strip()
    candidate_path = os.environ.get(CANDIDATE_ENV, "").strip()
    if not baseline_path or not candidate_path:
        ctx.fail("single_variable", "ADMISSION FAIL: baseline and candidate environments are not bound")
    try:
        baseline = _read_env_file(Path(baseline_path), "baseline environment")
        candidate = _read_env_file(Path(candidate_path), "candidate environment")
    except AdmissionError as exc:
        ctx.fail("single_variable", str(exc))
    for key in LAUNCH_OVERLAY_KEYS:
        if key in candidate or key in baseline:
            ctx.fail(
                "single_variable",
                "ADMISSION FAIL: launch overlay is persisted in the sealed environment",
            )
    base_sci = _scientific_items(baseline)
    cand_sci = _scientific_items(candidate)
    changed = sorted(set(base_sci) | set(cand_sci))
    changed = [key for key in changed if base_sci.get(key) != cand_sci.get(key)]
    if changed != [SELECT_METRIC_KEY]:
        ctx.fail(
            "single_variable",
            "ADMISSION FAIL: scientific variable count is "
            f"{len(changed)}: {','.join(changed) or 'none'}",
        )
    for key, value in cand_sci.items():
        if os.environ.get(key) != value:
            ctx.fail(
                "single_variable",
                f"ADMISSION FAIL: process environment {key} does not match the sealed candidate",
            )
    for key, value in base_sci.items():
        if key == SELECT_METRIC_KEY:
            continue
        if os.environ.get(key) != value:
            ctx.fail(
                "single_variable",
                f"ADMISSION FAIL: process environment {key} does not match the sealed baseline",
            )


def _gate_best_trunk(ctx: _Context) -> None:
    best_sha = os.environ.get(BEST_SHA_ENV, "").strip()
    best_path = os.environ.get(BEST_WEIGHTS_ENV, "").strip()
    trunk_sha = os.environ.get(TRUNK_SHA_ENV, "").strip()
    if not best_sha or not best_path or not trunk_sha:
        ctx.fail("best_trunk", "ADMISSION FAIL: BEST or trunk digest is not bound")
    best = Path(best_path)
    if not best.is_file():
        ctx.fail("best_trunk", "ADMISSION FAIL: BEST weights are missing")
    actual_best = _sha256_file(best)
    if actual_best != best_sha:
        ctx.fail("best_trunk", "ADMISSION FAIL: BEST weights sha256 mismatch")
    trunk = ctx.trunk
    weights = (trunk / "model.safetensors") if trunk else Path()
    if trunk is None or not weights.is_file():
        ctx.fail("best_trunk", "ADMISSION FAIL: trunk weights are missing")
    if _sha256_file(weights) != trunk_sha:
        ctx.fail("best_trunk", "ADMISSION FAIL: trunk weights sha256 mismatch")


def _gate_output(ctx: _Context) -> None:
    raw = os.environ.get(TRAIN_OUT_ENV, "").strip()
    if not raw:
        ctx.fail("output_directory", "ADMISSION FAIL: output directory is not bound")
    out = Path(raw)
    if ctx.out_dir is not None and ctx.out_dir.resolve() != out.resolve():
        ctx.fail(
            "output_directory",
            "ADMISSION FAIL: output directory does not match HYPERLEX_TRAIN_OUT",
        )
    if out.exists():
        ctx.fail("output_directory", "ADMISSION FAIL: output directory collision")
    lock = Path(str(out) + ".lock")
    if lock.exists():
        ctx.fail("output_directory", "ADMISSION FAIL: conflicting training run")
