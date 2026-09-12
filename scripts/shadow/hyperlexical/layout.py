"""Normative T1 head layout. No torch. No Hub."""

import os

HIDDEN = 768
LAYERS = 22
LAST_TRAINABLE = 2
LAST_TRAINABLE_MAX = 8
LAST_TRAINABLE_ENV = "HYPERLEX_LAST_TRAINABLE"
MAX_LEN = 64
TRUNK = "answerdotai/ModernBERT-base"
MODEL_ID_SEED = "hyperlex-encoder-modernbert-base-seed"

FAMILIES = (
    "betting-sharp",
    "crypto-degen",
    "ai-native",
    "brainrot-aura",
    "kinship-address",
    "political-status",
    "gaming-meta",
    "workplace-corp",
    "none",
)

UNK = "<unk>"


def _last_trainable_cap(layer_count: int | None) -> int:
    if layer_count is None:
        return min(LAST_TRAINABLE_MAX, LAYERS)
    return min(LAST_TRAINABLE_MAX, max(1, int(layer_count)))


def resolve_last_trainable(
    raw: str | int | None = None,
    *,
    layer_count: int | None = None,
) -> int:
    """Effective last-N. Default 2. Env HYPERLEX_LAST_TRAINABLE; clamp to layer cap."""
    cap = _last_trainable_cap(layer_count)
    if raw is None:
        raw = os.environ.get(LAST_TRAINABLE_ENV)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return min(LAST_TRAINABLE, cap)
    try:
        n = int(str(raw).strip(), 10)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{LAST_TRAINABLE_ENV} must be a positive int, got {raw!r}") from exc
    if n < 1:
        raise ValueError(f"{LAST_TRAINABLE_ENV} must be a positive int, got {n}")
    return min(n, cap)


def label_maps(unbind_rows: list[dict]) -> dict:
    roles = sorted({r for row in unbind_rows for r in (row.get("roles") or [])})
    fillers = sorted({f for row in unbind_rows for f in (row.get("fillers") or [])})
    role_vocab = [UNK] + roles
    filler_vocab = [UNK] + fillers
    return {
        "families": list(FAMILIES),
        "family_of": {f: i for i, f in enumerate(FAMILIES)},
        "role_vocab": role_vocab,
        "filler_vocab": filler_vocab,
        "role_of": {r: i for i, r in enumerate(role_vocab)},
        "filler_of": {f: i for i, f in enumerate(filler_vocab)},
    }


def describe(maps: dict) -> dict:
    return {
        "trunk": TRUNK,
        "hidden": HIDDEN,
        "layers": LAYERS,
        "last_trainable": resolve_last_trainable(),
        "max_len": MAX_LEN,
        "classify": {"in": HIDDEN, "out": len(FAMILIES), "pool": "token_0"},
        "unbind_role": {"in": HIDDEN, "out": len(maps["role_vocab"]), "reads": "last_hidden_state"},
        "unbind_filler": {"in": HIDDEN, "out": len(maps["filler_vocab"]), "reads": "last_hidden_state"},
        "forbidden": ["refusal_head", "brier_head", "chat_template"],
        "brier": None,
    }
