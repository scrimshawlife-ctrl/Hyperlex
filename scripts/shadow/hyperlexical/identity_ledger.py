"""Global text-identity ledger for Hyperlex evaluation reserves.

Contamination is owned by ``holdout_guard.normalized_text_sha256``. This
module does not train, score, or store raw text. A second normalizer is not
defined here. ``unbind_clean`` on a label is a slice predicate computed by
the caller with ``soft_ceiling.clean_surface``; it is not an identity.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .holdout_guard import normalized_text_sha256
from .selection_surface import row_id

SCHEMA = "hyperlex.identity_ledger.v1"
EVENT_SCHEMA = "hyperlex.identity_event.v1"
POLICY_ID = "hyperlex.eval_reserve.v1"
GENERATION = "GEN-0"
RESERVE_LEDGER_ENV = "HLX_EVAL_RESERVE_LEDGER"

# Sealed planning quotas. These are the SELECT-002 row composition, not a
# statistical minimum. See evaluation-reserve.md.
PLANNING_TARGETS: dict[str, int] = {
    "classify": 606,
    "classify_observed": 287,
    "classify_non_none": 604,
    "unbind_clean": 250,
}
REQUIRED_SLICES = tuple(PLANNING_TARGETS)

FORWARD = frozenset(
    {
        ("NEW", "TRAIN_CANDIDATE"),
        ("NEW", "EVAL_RESERVE"),
        ("AVAILABLE", "TRAIN_CANDIDATE"),
        ("AVAILABLE", "EVAL_RESERVE"),
        ("TRAIN_CANDIDATE", "TRAIN_CONSUMED"),
        ("EVAL_RESERVE", "EVAL_BOUND"),
        ("EVAL_BOUND", "EVAL_SPENT"),
        ("EVAL_BOUND", "EVAL_ABANDONED"),
    }
)
HISTORICAL_FLAGS = frozenset(
    {"training_consumed", "evaluation_spent", "evaluation_abandoned"}
)
_FORBIDDEN_KEYS = frozenset(
    {
        "text",
        "normalized_text",
        "raw_text",
        "candidate_score",
        "model_error",
        "model_score",
        "prediction",
    }
)
_SCORE_KEYS = frozenset({"candidate_score", "model_error", "model_score", "prediction"})


def _refuse_mapping(value: Mapping[str, Any], where: str) -> None:
    for key in value:
        if key in _FORBIDDEN_KEYS:
            raise SystemExit(f"REFUSE: {where} must not carry {key}")


def policy_sealed() -> bool:
    """The assignment rule is the code under ``POLICY_ID``. It does not read scores."""
    return True


def _empty_identity(digest: str) -> dict[str, Any]:
    return {
        "normalized_text_sha256": digest,
        "row_ids": [],
        "source_artifacts": [],
        "first_seen": "",
        "current_sources": [],
        "training_consumed": False,
        "training_artifacts": [],
        "evaluation_spent": False,
        "evaluation_spent_artifacts": [],
        "evaluation_abandoned": False,
        "evaluation_abandoned_artifacts": [],
        "evaluation_reserved": False,
        "evaluation_bound": False,
        "train_candidate": False,
        "catalogued": False,
        "experiment_bindings": [],
        "labels": [],
        "provenance": [],
        "generation": GENERATION,
    }


def derived_state(record: Mapping[str, Any]) -> str:
    """Blocking historical flags win. Routing flags apply only when none are set."""
    if record.get("training_consumed"):
        return "TRAIN_CONSUMED"
    if record.get("evaluation_spent"):
        return "EVAL_SPENT"
    if record.get("evaluation_abandoned"):
        return "EVAL_ABANDONED"
    if record.get("evaluation_bound"):
        return "EVAL_BOUND"
    if record.get("evaluation_reserved"):
        return "EVAL_RESERVE"
    if record.get("train_candidate"):
        return "TRAIN_CANDIDATE"
    if record.get("catalogued"):
        return "AVAILABLE"
    return "NEW"


def slices_of(record: Mapping[str, Any]) -> set[str]:
    """Metric slices this identity can support. One identity counts once per slice."""
    found: set[str] = set()
    classify = [lab for lab in record.get("labels") or [] if lab.get("task") == "classify"]
    if classify:
        found.add("classify")
        if any(lab.get("class") == "OBSERVED" for lab in classify):
            found.add("classify_observed")
        if any(str(lab.get("lineage") or "") not in ("", "none") for lab in classify):
            found.add("classify_non_none")
    if any(lab.get("task") == "unbind" and lab.get("unbind_clean") is True for lab in record.get("labels") or []):
        found.add("unbind_clean")
    return found


def _sorted_unique(items: Sequence[str]) -> list[str]:
    return sorted({item for item in items if item})


def _label(row: Mapping[str, Any], *, unbind_clean: bool | None) -> dict[str, Any]:
    label: dict[str, Any] = {
        "task": str(row.get("task") or ""),
        "class": str(row.get("class") or ""),
        "lineage": str(row.get("lineage") or ""),
        "split": str(row.get("split") or ""),
    }
    if label["task"] == "unbind":
        label["unbind_clean"] = bool(unbind_clean)
    return label


def _merge_label(labels: list[dict[str, Any]], label: Mapping[str, Any]) -> None:
    if label not in labels:
        labels.append(dict(label))
        labels.sort(key=lambda item: json.dumps(item, sort_keys=True))


class IdentityLedger:
    """Append-only events plus a derived identity index. No raw text."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.identities: dict[str, dict[str, Any]] = {}
        self.row_owner: dict[str, str] = {}
        self.row_id_collisions: list[dict[str, str]] = []

    def identity(self, digest: str) -> dict[str, Any] | None:
        return self.identities.get(digest)

    def _append(self, event: dict[str, Any]) -> None:
        _refuse_mapping(event, "ledger event")
        event = dict(event)
        event["schema"] = EVENT_SCHEMA
        event["seq"] = len(self.events) + 1
        event["generation"] = GENERATION
        self.events.append(event)

    def _touch(self, digest: str) -> dict[str, Any]:
        record = self.identities.get(digest)
        if record is None:
            record = _empty_identity(digest)
            self.identities[digest] = record
        return record

    def observe(
        self,
        digest: str,
        *,
        source_artifact: str,
        row_ids: Sequence[str] = (),
        labels: Sequence[Mapping[str, Any]] = (),
        current_source: bool = False,
        catalogued: bool = False,
        provenance: str,
        experiment_id: str = "",
    ) -> dict[str, Any]:
        """Attach ids, labels, and provenance. Does not route the identity."""
        if len(digest) != 64:
            raise SystemExit("REFUSE: normalized_text_sha256 must be 64 hex characters")
        record = self._touch(digest)
        if not record["first_seen"]:
            record["first_seen"] = source_artifact
        record["source_artifacts"] = _sorted_unique([*record["source_artifacts"], source_artifact])
        if current_source:
            record["current_sources"] = _sorted_unique([*record["current_sources"], source_artifact])
        if catalogued:
            record["catalogued"] = True
        for ident in row_ids:
            self._claim_row_id(record, ident)
        for label in labels:
            _merge_label(record["labels"], label)
        if experiment_id:
            record["experiment_bindings"] = _sorted_unique(
                [*record["experiment_bindings"], experiment_id]
            )
        if provenance and provenance not in record["provenance"]:
            record["provenance"].append(provenance)
        self._append(
            {
                "kind": "observe",
                "normalized_text_sha256": digest,
                "source_artifact": source_artifact,
                "row_ids": list(row_ids),
                "current_source": current_source,
                "catalogued": catalogued,
                "provenance": provenance,
                "experiment_id": experiment_id,
                "labels": [dict(item) for item in labels],
            }
        )
        return record

    def _claim_row_id(self, record: dict[str, Any], ident: str) -> None:
        if not ident:
            return
        owner = self.row_owner.get(ident)
        digest = record["normalized_text_sha256"]
        if owner is None:
            self.row_owner[ident] = digest
        elif owner != digest:
            self.row_id_collisions.append(
                {"row_id": ident, "existing_hash": owner, "new_hash": digest}
            )
        if ident not in record["row_ids"]:
            record["row_ids"] = _sorted_unique([*record["row_ids"], ident])

    def mark_historical(
        self,
        digest: str,
        flag: str,
        *,
        source_artifact: str,
        provenance: str,
        experiment_id: str = "",
    ) -> dict[str, Any]:
        """Record a receipt-backed past state. Flags only ever turn on."""
        if flag not in HISTORICAL_FLAGS:
            raise SystemExit(f"REFUSE: unknown historical flag {flag}")
        record = self._touch(digest)
        record[flag] = True
        artifact_key = {
            "training_consumed": "training_artifacts",
            "evaluation_spent": "evaluation_spent_artifacts",
            "evaluation_abandoned": "evaluation_abandoned_artifacts",
        }[flag]
        record[artifact_key] = _sorted_unique([*record[artifact_key], source_artifact])
        if experiment_id:
            record["experiment_bindings"] = _sorted_unique(
                [*record["experiment_bindings"], experiment_id]
            )
        if provenance and provenance not in record["provenance"]:
            record["provenance"].append(provenance)
        self._append(
            {
                "kind": "historical",
                "normalized_text_sha256": digest,
                "flag": flag,
                "source_artifact": source_artifact,
                "provenance": provenance,
                "experiment_id": experiment_id,
            }
        )
        return record

    def transition(self, digest: str, to_state: str, *, source_artifact: str, provenance: str) -> str:
        """Monotonic forward route. Historical blocks cannot be cleared."""
        record = self.identities.get(digest)
        if record is None:
            raise SystemExit("REFUSE: cannot route an unseen text identity")
        state = derived_state(record)
        if record["training_consumed"] or record["evaluation_spent"] or record["evaluation_abandoned"]:
            raise SystemExit(
                f"REFUSE: text identity is {state}; that block is monotonic in {GENERATION}"
            )
        if (state, to_state) not in FORWARD:
            raise SystemExit(f"REFUSE: transition {state} -> {to_state} is not allowed")
        if to_state == "TRAIN_CANDIDATE":
            record["train_candidate"] = True
        elif to_state == "TRAIN_CONSUMED":
            record["training_consumed"] = True
            record["training_artifacts"] = _sorted_unique(
                [*record["training_artifacts"], source_artifact]
            )
        elif to_state == "EVAL_RESERVE":
            record["evaluation_reserved"] = True
        elif to_state == "EVAL_BOUND":
            record["evaluation_bound"] = True
        elif to_state == "EVAL_SPENT":
            record["evaluation_spent"] = True
        elif to_state == "EVAL_ABANDONED":
            record["evaluation_abandoned"] = True
        else:
            raise SystemExit(f"REFUSE: unknown route {to_state}")
        if provenance and provenance not in record["provenance"]:
            record["provenance"].append(provenance)
        self._append(
            {
                "kind": "transition",
                "normalized_text_sha256": digest,
                "from_state": state,
                "to_state": to_state,
                "source_artifact": source_artifact,
                "provenance": provenance,
            }
        )
        return to_state

    def request_generation_reset(self, *, governed_receipt: str, confirm: bool) -> dict[str, Any]:
        """Record a request. Does not clear flags and does not create GEN-1."""
        if not confirm or not str(governed_receipt or "").strip():
            raise SystemExit(
                "REFUSE: generation reset requires confirm=True and a governed receipt"
            )
        self._append(
            {
                "kind": "generation_reset_requested",
                "normalized_text_sha256": "",
                "source_artifact": governed_receipt,
                "provenance": "requested only; flags unchanged; GEN-1 not created",
                "applied": False,
            }
        )
        return {"applied": False, "generation": GENERATION, "flags_cleared": 0}

    def observe_row(
        self,
        row: Mapping[str, Any],
        *,
        source_artifact: str,
        provenance: str,
        current_source: bool = False,
        catalogued: bool = False,
        unbind_clean: bool | None = None,
        experiment_id: str = "",
    ) -> str:
        """Hash one row and catalogue it. The row text is not retained."""
        if any(key in row for key in _SCORE_KEYS):
            raise SystemExit("REFUSE: catalogue input carries a model outcome field")
        digest = normalized_text_sha256(str(row.get("text") or ""))
        ids = [row_id(row)]
        declared = row.get("row_id")
        if isinstance(declared, str) and declared and declared not in ids:
            ids.append(declared)
        self.observe(
            digest,
            source_artifact=source_artifact,
            row_ids=ids,
            labels=[_label(row, unbind_clean=unbind_clean)],
            current_source=current_source,
            catalogued=catalogued,
            provenance=provenance,
            experiment_id=experiment_id,
        )
        return digest

    def reserve_counts(self) -> dict[str, int]:
        counts = {key: 0 for key in REQUIRED_SLICES}
        for record in self.identities.values():
            if derived_state(record) not in ("EVAL_RESERVE", "EVAL_BOUND"):
                continue
            for key in slices_of(record):
                if key in counts:
                    counts[key] += 1
        return counts

    def screen(
        self,
        rows: Sequence[Mapping[str, Any]],
        *,
        batch_id: str,
        targets: Mapping[str, int] | None = None,
        unbind_clean_hashes: set[str] | None = None,
    ) -> dict[str, Any]:
        """Admission decision without mutation. Duplicate text does not raise n."""
        return self._route(
            rows,
            batch_id=batch_id,
            targets=dict(targets or PLANNING_TARGETS),
            unbind_clean_hashes=set(unbind_clean_hashes or ()),
            apply=False,
        )

    def admit(
        self,
        rows: Sequence[Mapping[str, Any]],
        *,
        batch_id: str,
        source_artifact: str,
        targets: Mapping[str, int] | None = None,
        unbind_clean_hashes: set[str] | None = None,
    ) -> dict[str, Any]:
        """Route genuinely new text. Rejects hashes already consumed, spent, abandoned, or reserved."""
        if not str(batch_id or "").strip():
            raise SystemExit("REFUSE: admission batch_id is required")
        report = self._route(
            rows,
            batch_id=batch_id,
            targets=dict(targets or PLANNING_TARGETS),
            unbind_clean_hashes=set(unbind_clean_hashes or ()),
            apply=True,
            source_artifact=source_artifact,
        )
        return report

    def _route(
        self,
        rows: Sequence[Mapping[str, Any]],
        *,
        batch_id: str,
        targets: dict[str, int],
        unbind_clean_hashes: set[str],
        apply: bool,
        source_artifact: str = "",
    ) -> dict[str, Any]:
        grouped: dict[str, list[Mapping[str, Any]]] = {}
        collisions = 0
        batch_owner: dict[str, str] = {}
        for row in rows:
            if any(key in row for key in _SCORE_KEYS):
                raise SystemExit("REFUSE: admission input carries a model outcome field")
            digest = normalized_text_sha256(str(row.get("text") or ""))
            grouped.setdefault(digest, []).append(row)
            declared = row.get("row_id") if isinstance(row.get("row_id"), str) else ""
            computed = row_id(row)
            idents = [declared] if declared else []
            if computed not in idents:
                idents.append(computed)
            row_collides = False
            for ident in idents:
                owner = self.row_owner.get(ident) or batch_owner.get(ident)
                if owner is not None and owner != digest:
                    row_collides = True
                elif ident not in self.row_owner:
                    batch_owner.setdefault(ident, digest)
            if row_collides:
                collisions += 1
        def sort_key(digest: str) -> str:
            return hashlib.sha256(f"{GENERATION}|{batch_id}|{digest}".encode("utf-8")).hexdigest()

        counts = self.reserve_counts()
        rejected: dict[str, int] = {
            "TRAIN_CONSUMED": 0,
            "EVAL_SPENT": 0,
            "EVAL_ABANDONED": 0,
            "EVAL_RESERVE": 0,
            "EVAL_BOUND": 0,
            "TRAIN_CANDIDATE": 0,
        }
        reserved = 0
        candidates = 0
        duplicate_text_rows = 0
        accepted_hashes: list[str] = []
        for digest in sorted(grouped, key=sort_key):
            members = grouped[digest]
            if len(members) > 1:
                duplicate_text_rows += len(members) - 1
            record = self.identities.get(digest)
            state = derived_state(record) if record else "NEW"
            if state in rejected:
                rejected[state] += 1
                continue
            if state not in ("NEW", "AVAILABLE"):
                raise SystemExit(f"REFUSE: cannot admit text in state {state}")
            pending_labels = []
            pending_ids: list[str] = []
            for row in members:
                clean = digest in unbind_clean_hashes
                pending_labels.append(_label(row, unbind_clean=clean if str(row.get("task") or "") == "unbind" else None))
                pending_ids.append(row_id(row))
                declared = row.get("row_id")
                if isinstance(declared, str) and declared:
                    pending_ids.append(declared)
            snapshot = _empty_identity(digest)
            if record:
                snapshot["labels"] = [dict(item) for item in record["labels"]]
            for label in pending_labels:
                _merge_label(snapshot["labels"], label)
            served = slices_of(snapshot)
            opens = [key for key in served if counts.get(key, 0) < int(targets.get(key, 0))]
            to_state = "EVAL_RESERVE" if opens else "TRAIN_CANDIDATE"
            if apply:
                self.observe(
                    digest,
                    source_artifact=source_artifact,
                    row_ids=pending_ids,
                    labels=pending_labels,
                    provenance=f"admitted batch {batch_id}",
                )
                self.transition(
                    digest,
                    to_state,
                    source_artifact=source_artifact,
                    provenance=f"assignment {POLICY_ID} batch {batch_id}",
                )
            if to_state == "EVAL_RESERVE":
                reserved += 1
                accepted_hashes.append(digest)
                for key in served:
                    if key in counts:
                        counts[key] += 1
            else:
                candidates += 1
        return {
            "policy_id": POLICY_ID,
            "generation": GENERATION,
            "batch_id": batch_id,
            "raw_rows": len(rows),
            "unique_canonical_text_identities": len(grouped),
            "unique_admitted_to_eval_reserve": reserved,
            "unique_routed_to_train_candidate": candidates,
            "duplicate_text_rows_not_counted": duplicate_text_rows,
            "row_id_collisions_with_new_text": collisions,
            "rejected_existing_identities": rejected,
            "rejected_unique_identities": sum(rejected.values()),
            "reserve_counts_after": counts if apply else self._projected_counts(counts),
            "applied": apply,
            "model_outcomes_consulted": False,
        }

    def _projected_counts(self, counts: dict[str, int]) -> dict[str, int]:
        return dict(counts)

    def select_003_gate(self, train_hashes: set[str]) -> dict[str, Any]:
        """Necessary conditions only. Does not draft an experiment."""
        reserved = [
            record
            for record in self.identities.values()
            if derived_state(record) in ("EVAL_RESERVE", "EVAL_BOUND")
        ]
        hashes = {record["normalized_text_sha256"] for record in reserved}
        counts = self.reserve_counts()
        represented = {key: counts[key] >= 1 for key in REQUIRED_SLICES}
        blocked = [
            record["normalized_text_sha256"]
            for record in reserved
            if record["training_consumed"] or record["evaluation_spent"] or record["evaluation_abandoned"]
        ]
        overlap = sorted(hashes & train_hashes)
        eligible = (
            policy_sealed()
            and bool(reserved)
            and all(represented.values())
            and not blocked
            and not overlap
        )
        return {
            "select_003": "NOT_DRAFTED",
            "eligible": eligible,
            "policy_sealed": policy_sealed(),
            "reserve_identities": len(reserved),
            "required_slices_represented": represented,
            "text_disjoint_from_training": not overlap,
            "training_overlap_identities": len(overlap),
            "spent_or_abandoned_in_reserve": len(blocked),
            "authorization": "SEPARATE",
            "statistical_minimum": "NOT_COMPUTABLE",
        }

    def census(self, live_hashes: set[str]) -> dict[str, Any]:
        """Aggregate counts. Hash lists stay in the ledger, not in this summary."""
        def bucket(pred) -> set[str]:
            return {digest for digest, record in self.identities.items() if pred(record)}

        consumed = bucket(lambda record: record["training_consumed"])
        spent = bucket(lambda record: record["evaluation_spent"])
        abandoned = bucket(lambda record: record["evaluation_abandoned"])
        available = bucket(lambda record: derived_state(record) == "AVAILABLE")
        live_available = available & live_hashes
        by_slice = {key: 0 for key in (*REQUIRED_SLICES, "unbind", "classify_inferred", "other")}
        for digest in live_available:
            record = self.identities[digest]
            labels = list(record["labels"])
            tasks = {lab.get("task") for lab in labels}
            classify = [lab for lab in labels if lab.get("task") == "classify"]
            if classify:
                by_slice["classify"] += 1
                if any(lab.get("class") == "OBSERVED" for lab in classify):
                    by_slice["classify_observed"] += 1
                if any(lab.get("class") == "INFERRED" for lab in classify):
                    by_slice["classify_inferred"] += 1
                if any(str(lab.get("lineage") or "") not in ("", "none") for lab in classify):
                    by_slice["classify_non_none"] += 1
            if "unbind" in tasks:
                by_slice["unbind"] += 1
                if any(
                    lab.get("task") == "unbind" and lab.get("unbind_clean") is True for lab in labels
                ):
                    by_slice["unbind_clean"] += 1
            if not tasks:
                by_slice["other"] += 1
        return {
            "generation": GENERATION,
            "policy_id": POLICY_ID,
            "identities": len(self.identities),
            "all_live_text_hashes": len(live_hashes),
            "live_hashes_in_ledger": len(live_hashes & set(self.identities)),
            "training_consumed_hashes": len(consumed),
            "spent_evaluation_hashes": len(spent),
            "abandoned_evaluation_hashes": len(abandoned),
            "currently_available_hashes": len(available),
            "live_training_consumed_hashes": len(consumed & live_hashes),
            "live_spent_evaluation_hashes": len(spent & live_hashes),
            "live_abandoned_evaluation_hashes": len(abandoned & live_hashes),
            "live_available_hashes": len(live_available),
            "available_by_slice": by_slice,
            "reserve_counts": self.reserve_counts(),
            "row_id_collisions": len(self.row_id_collisions),
        }

    def project(self) -> dict[str, Any]:
        identities = []
        for digest in sorted(self.identities):
            record = dict(self.identities[digest])
            record["state"] = derived_state(record)
            record["slices"] = sorted(slices_of(record))
            identities.append(record)
        payload = {
            "schema": SCHEMA,
            "policy_id": POLICY_ID,
            "generation": GENERATION,
            "identity_function": "hyperlexical.holdout_guard.normalized_text_sha256",
            "planning_targets": dict(PLANNING_TARGETS),
            "planning_target_class": "PLANNING_TARGET",
            "statistical_minimum": "NOT_COMPUTABLE",
            "identities": identities,
            "row_id_collisions": list(self.row_id_collisions),
            "n_events": len(self.events),
        }
        _walk_forbid(payload)
        return payload

    def persist_append(self, directory: str | Path, prior_event_count: int) -> int:
        """Append events after ``prior_event_count`` and refresh the projection.

        ``events.jsonl`` is append-only. ``ledger.json`` is a derived view.
        """
        root = Path(directory)
        events_path = root / "events.jsonl"
        fresh = self.events[prior_event_count:]
        if fresh:
            with events_path.open("a", encoding="utf-8") as handle:
                for event in fresh:
                    handle.write(json.dumps(event, sort_keys=True) + "\n")
        (root / "ledger.json").write_text(
            json.dumps(self.project(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return len(fresh)

    def save(self, directory: str | Path) -> None:
        root = Path(directory)
        root.mkdir(parents=True, exist_ok=True)
        events_path = root / "events.jsonl"
        if events_path.exists():
            raise SystemExit(f"REFUSE: ledger events already exist: {events_path}")
        lines = [json.dumps(event, sort_keys=True) for event in self.events]
        events_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        (root / "ledger.json").write_text(
            json.dumps(self.project(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls, directory: str | Path) -> "IdentityLedger":
        events_path = Path(directory) / "events.jsonl"
        if not events_path.is_file():
            raise SystemExit(f"REFUSE: ledger events are missing: {events_path}")
        ledger = cls()
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            kind = event.get("kind")
            if kind == "observe":
                ledger.observe(
                    event["normalized_text_sha256"],
                    source_artifact=event.get("source_artifact") or "",
                    row_ids=event.get("row_ids") or [],
                    labels=event.get("labels") or [],
                    current_source=bool(event.get("current_source")),
                    catalogued=bool(event.get("catalogued")),
                    provenance=event.get("provenance") or "",
                    experiment_id=event.get("experiment_id") or "",
                )
            elif kind == "historical":
                ledger.mark_historical(
                    event["normalized_text_sha256"],
                    event["flag"],
                    source_artifact=event.get("source_artifact") or "",
                    provenance=event.get("provenance") or "",
                    experiment_id=event.get("experiment_id") or "",
                )
            elif kind == "transition":
                ledger.transition(
                    event["normalized_text_sha256"],
                    event["to_state"],
                    source_artifact=event.get("source_artifact") or "",
                    provenance=event.get("provenance") or "",
                )
            elif kind == "generation_reset_requested":
                ledger.request_generation_reset(
                    governed_receipt=event.get("source_artifact") or "",
                    confirm=True,
                )
            else:
                raise SystemExit(f"REFUSE: unknown ledger event {kind}")
        # Replay appended a second copy. Replace with the file's events.
        ledger.events = []
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                ledger.events.append(json.loads(line))
        return ledger


def _walk_forbid(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _FORBIDDEN_KEYS:
                raise SystemExit(f"REFUSE: ledger projection contains {key}")
            _walk_forbid(item)
    elif isinstance(value, list):
        for item in value:
            _walk_forbid(item)


def assert_training_disjoint_from_reserve(
    rows: Sequence[Mapping[str, Any]],
    ledger: IdentityLedger,
) -> dict[str, int | bool]:
    """Fail closed when pinned training contains fresh reserve text.

    Spent and abandoned flags do not trip this gate. Those identities may
    already sit inside the historical training export.
    """
    reserved = 0
    for row in rows:
        digest = normalized_text_sha256(str(row.get("text") or ""))
        record = ledger.identity(digest)
        if record is None:
            continue
        if derived_state(record) in ("EVAL_RESERVE", "EVAL_BOUND"):
            reserved += 1
    if reserved:
        raise SystemExit(
            "ADMISSION FAIL: training input contains "
            f"{reserved} EVAL_RESERVE text identities"
        )
    return {
        "eval_reserve_training_overlap": 0,
        "eval_reserve_training_disjoint": True,
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    """Admission, census, and evaluation settlement. Does not train or score."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Hyperlex evaluation-reserve ledger")
    sub = parser.add_subparsers(dest="cmd", required=True)
    admit = sub.add_parser("admit")
    admit.add_argument("--ledger", required=True)
    admit.add_argument("--rows", required=True)
    admit.add_argument("--batch-id", required=True)
    admit.add_argument("--source", required=True)
    admit.add_argument(
        "--train-export",
        default="",
        help="JSONL export. unbind_clean uses soft_ceiling.clean_surface on split=train.",
    )
    census_cmd = sub.add_parser("census")
    census_cmd.add_argument("--ledger", required=True)
    census_cmd.add_argument("--live-hashes", help="Optional JSON list of live text hashes")
    settle = sub.add_parser("settlement-apply")
    settle.add_argument("--stream-rows", required=True)
    settle.add_argument("--sheet", action="append", default=[])
    settle.add_argument("--records", default="")
    settle.add_argument("--operator", required=True)
    settle.add_argument("--provenance", required=True)
    settle.add_argument("--batch-id", required=True)
    settle.add_argument("--receipt", required=True)
    settle.add_argument("--settlement-log", required=True)
    settle.add_argument("--settled-at", required=True)
    settle.add_argument("--stream-run-id", default="")
    settle.add_argument("--activated-family", action="append", default=[])
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.cmd == "settlement-apply":
        from .eval_settlement import run_settlement_apply

        return run_settlement_apply(args)
    if args.cmd == "census":
        ledger = IdentityLedger.load(args.ledger)
        live: set[str] = set()
        if args.live_hashes:
            payload = json.loads(Path(args.live_hashes).read_text(encoding="utf-8"))
            live = set(payload)
        report = ledger.census(live)
        report["acquisition_gap"] = acquisition_gap(ledger.reserve_counts())
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
        return 0
    ledger = IdentityLedger.load(args.ledger)
    prior = len(ledger.events)
    rows = _read_jsonl(Path(args.rows))
    clean_hashes: set[str] = set()
    if args.train_export:
        from .clean_unbind import unbind_clean_hashes

        exported = _read_jsonl(Path(args.train_export))
        clean_hashes, _account = unbind_clean_hashes(rows, exported)
    report = ledger.admit(
        rows,
        batch_id=args.batch_id,
        source_artifact=args.source,
        unbind_clean_hashes=clean_hashes,
    )
    written = ledger.persist_append(args.ledger, prior)
    report["events_appended"] = written
    report["acquisition_gap"] = acquisition_gap(ledger.reserve_counts())
    _walk_forbid(report)
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


def acquisition_gap(reserved: Mapping[str, int] | None = None) -> list[dict[str, Any]]:
    """Planning gaps. Statistical minima stay ``NOT_COMPUTABLE``."""
    counts = dict(reserved or {})
    rows = []
    for key, target in PLANNING_TARGETS.items():
        have = int(counts.get(key, 0))
        rows.append(
            {
                "slice": key,
                "currently_reserved": have,
                "minimum_required": "NOT_COMPUTABLE",
                "planning_target": target,
                "planning_target_class": "PLANNING_TARGET",
                "gap_vs_minimum": "NOT_COMPUTABLE",
                "gap_vs_planning_target": max(target - have, 0),
            }
        )
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
