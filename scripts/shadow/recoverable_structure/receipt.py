import json
import uuid
from datetime import datetime, timezone

SCHEMA = "abraxas.recoverable_structure.probe.v0.1"
FORBIDDEN = {"symbolic", "has_symbols"}
PROXIES = {"weakness", "mdl", "unspecified"}
SCHEMES = {"positional", "type_slot"}


class ReceiptError(ValueError):
    pass


def build_receipt(encoder_id, batch_hash, split_hash, role_schemes, selection_proxy, scheme_blocks, source_class="AAL-metric", run_id=None, logged_at=None):
    if selection_proxy not in PROXIES:
        raise ReceiptError("missing or invalid selection_proxy")
    rec = {
        "schema": SCHEMA,
        "run_id": run_id or str(uuid.uuid4()),
        "logged_at": logged_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "encoder_id": encoder_id,
        "batch_hash": batch_hash,
        "split_hash": split_hash,
        "role_schemes": list(role_schemes),
        "selection_proxy": selection_proxy,
        "schemes": scheme_blocks,
        "brier": None,
        "forecast_eligible": False,
        "auto_fire": False,
        "lane": "SHADOW",
        "classification_of_result": "OBSERVED",
        "source_class": source_class,
    }
    validate_receipt(rec)
    return rec


def validate_receipt(rec):
    if rec.get("schema") != SCHEMA:
        raise ReceiptError("bad schema")
    if rec.get("brier") is not None:
        raise ReceiptError("brier must be null")
    if rec.get("forecast_eligible") is not False:
        raise ReceiptError("forecast_eligible must be false")
    if rec.get("auto_fire") is not False:
        raise ReceiptError("auto_fire must be false")
    if rec.get("lane") != "SHADOW":
        raise ReceiptError("lane")
    if rec.get("classification_of_result") != "OBSERVED":
        raise ReceiptError("classification_of_result")
    if rec.get("source_class") not in {"lab-paper", "AAL-metric"}:
        raise ReceiptError("source_class")
    if rec.get("selection_proxy") not in PROXIES:
        raise ReceiptError("selection_proxy")
    overlap = FORBIDDEN.intersection(rec)
    if overlap:
        raise ReceiptError(f"forbidden keys: {overlap}")
    schemes = rec.get("role_schemes") or []
    if not 1 <= len(schemes) <= 2 or any(s not in SCHEMES for s in schemes):
        raise ReceiptError("role_schemes")
    blocks = rec.get("schemes") or []
    if not blocks:
        raise ReceiptError("schemes empty")
    for blk in blocks:
        if blk.get("scheme") not in SCHEMES:
            raise ReceiptError("block scheme")
        inter = blk.get("intervention") or {}
        for k in ("edit", "expected", "observed", "hit"):
            if k not in inter:
                raise ReceiptError("intervention")
    required = ("schema", "run_id", "logged_at", "encoder_id", "batch_hash", "split_hash", "role_schemes", "selection_proxy", "schemes", "brier", "forecast_eligible", "auto_fire", "lane", "classification_of_result", "source_class")
    for k in required:
        if k not in rec:
            raise ReceiptError(f"missing {k}")
    return rec


def render_card(rec):
    validate_receipt(rec)
    lines = [
        "Recoverable-structure probe card",
        "Lane: SHADOW / advisory",
        "Instrumentation only. Not P(structure). Not a fire threshold.",
        "Brier: null. Forecast eligible: no.",
        "Two-scheme cap: positional, type_slot.",
        f"Encoder: {rec['encoder_id']}",
        f"Schemes: {', '.join(rec['role_schemes'])}",
        f"selection_proxy: {rec['selection_proxy']}",
    ]
    for blk in rec["schemes"]:
        lines.append(
            f"- {blk['scheme']}: test_mse={blk['test_mse']:.4f} swap={blk['swap_accuracy']:.3f} edit={blk['intervention']['edit']} hit={blk['intervention']['hit']}"
        )
    return "\n".join(lines)


def dumps(rec):
    validate_receipt(rec)
    return json.dumps(rec, indent=2, sort_keys=True)
