"""Normative T1 head layout. No torch. No Hub."""

HIDDEN = 768
LAYERS = 22
LAST_TRAINABLE = 2
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
        "last_trainable": LAST_TRAINABLE,
        "max_len": MAX_LEN,
        "classify": {"in": HIDDEN, "out": len(FAMILIES), "pool": "token_0"},
        "unbind_role": {"in": HIDDEN, "out": len(maps["role_vocab"]), "reads": "last_hidden_state"},
        "unbind_filler": {"in": HIDDEN, "out": len(maps["filler_vocab"]), "reads": "last_hidden_state"},
        "forbidden": ["refusal_head", "brier_head", "chat_template"],
        "brier": None,
    }
