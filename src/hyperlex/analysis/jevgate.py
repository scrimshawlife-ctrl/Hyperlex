"""Opt-in jevgate-1 family classifier.

Cascade (flag off is the default):

1. Lexical ``match_lineage`` (vector re-rank off). If it fires, that family decides.
2. Otherwise, if ``HYPERLEX_JEVGATE`` / ``--jevgate`` is off, return ``none``.
3. Otherwise call TypeSafe Jev, model pinned to ``jev-1.13.0``, three identical
   passes. Emit a family only when mean ``P(none)`` is strictly below tau.
   Tau ``0.30333`` is frozen by prereg v5.

Jev failures fail closed to ``none`` after one identical retry. They do not raise
into callers. ``jev_best_guess`` is low-confidence and never decides.

The prompt object is frozen. ``sha256(JSON.stringify(QUESTIONS))`` is checked at
import; a mismatch refuses the Jev path.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import socket
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Mapping

# Frozen by prereg v5. Do not tune.
TAU = 0.30333
MODEL_ID = "jev-1.13.0"
PASSES = 3
REQUEST_TIMEOUT_S = 55.0
FROZEN_PROMPT_SHA256 = "0dab58787402cb6e5aadc92e3123a65f09d281444e100b8485ede273c7d9af53"
JEVGATE_ENV = "HYPERLEX_JEVGATE"
DEFAULT_BASE_URL = "https://api.typesafe.ai/v1"

CLASSIFY_CONFIG = {
    "gate": "jevgate-1",
    "env": JEVGATE_ENV,
    "default": False,
    "model": MODEL_ID,
    "tau": TAU,
    "passes": PASSES,
    "prompt_sha256": FROZEN_PROMPT_SHA256,
}

_FAMILY: tuple[tuple[str, str], ...] = (
    (
        "betting-sharp",
        "Sports-betting, gambling and poker bettor jargon (odds, lines, wagers, bankroll, handicapping culture).",
    ),
    (
        "crypto-degen",
        "Cryptocurrency, DeFi, NFT and speculative-trading community slang.",
    ),
    (
        "ai-native",
        "AI / LLM / machine-learning and AI-builder vernacular (models, prompting, agents, training, evals, AI-era coinages).",
    ),
    (
        "brainrot-aura",
        'Gen-Z / Gen-Alpha internet "brainrot" slang: status, vibe, aura, meme and TikTok-era coinages.',
    ),
    (
        "kinship-address",
        "Forms of address and pseudo-kinship terms used for friends or strangers (bro/sis-style, family-style address).",
    ),
    (
        "political-status",
        "Online political, ideological and status-signalling discourse slang.",
    ),
    (
        "gaming-meta",
        "Video-game, esports and gamer-community jargon (game mechanics, balance, competitive play).",
    ),
    (
        "workplace-corp",
        "Corporate, office and workplace jargon and career-culture coinages.",
    ),
)

_NONE_CRITERION = (
    "Not slang/jargon of any listed community: ordinary English, a proper name, "
    "noise, a fragment, or slang from an unlisted community."
)

_EIGHT: tuple[str, ...] | None = None


class JevCallError(Exception):
    """One failed Jev attempt. Callers of ``classify_term`` do not see this."""

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(reason)


def _js_stringify(obj: Any) -> str:
    """Match JavaScript ``JSON.stringify`` (no spaces, insertion order)."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _build_questions() -> dict[str, Any]:
    family = dict(_FAMILY)
    famlist = "\n".join(f"- {key}: {value}" for key, value in family.items())
    in_scope = (
        "STATE.text is a short term or phrase (often a single word or stem, sometimes lowercased or truncated). "
        "Answer yes only if STATE.text is slang, jargon or vernacular that clearly belongs to at least one of these eight communities:\n"
        f"{famlist}\n"
        "Answer no if it is: ordinary standard English in its everyday dictionary sense; a proper name, brand, place or hashtag with no community-slang sense; a fragment, typo, number or noise; or slang/informal language that belongs to some OTHER community or general informal English not listed above. When unsure, answer no."
    )
    any_slang = (
        "STATE.text is a short term or phrase. Is it slang, jargon, internet vernacular or an informal coinage of ANY kind (any community, any era), as opposed to ordinary standard English, a proper name, or noise?"
    )
    family_q = (
        "STATE.text is a short term or phrase. Which single community does it belong to as slang/jargon? Choose none if it is not slang of any of the listed communities (ordinary English, a name, noise, or slang of another community)."
    )
    criteria = dict(family)
    criteria["none"] = _NONE_CRITERION
    return {
        "in_scope": {"type": "boolean", "instructions": in_scope},
        "any_slang": {"type": "boolean", "instructions": any_slang},
        "family": {"type": "choice", "instructions": family_q, "criteria": criteria},
    }


QUESTIONS = _build_questions()
CRITERIA_KEYS = tuple(QUESTIONS["family"]["criteria"].keys())


def prompt_sha256() -> str:
    return hashlib.sha256(_js_stringify(QUESTIONS).encode("utf-8")).hexdigest()


def assert_prompt_sha() -> None:
    """Load-time and call-time check. Raises AssertionError if the prompt drifted."""
    digest = prompt_sha256()
    assert digest == FROZEN_PROMPT_SHA256, digest


def prompt_is_frozen() -> bool:
    try:
        assert_prompt_sha()
    except AssertionError:
        return False
    return True


def _prompt_ok_at_load() -> bool:
    """Check the frozen prompt when the module loads.

    A mismatch does not raise here: the registry cascade must still import.
    ``classify_term`` refuses the Jev path, and ``assert_prompt_sha`` raises.
    """
    try:
        assert_prompt_sha()
    except AssertionError:
        return False
    return True


PROMPT_SHA_OK = _prompt_ok_at_load()
PROMPT_SHA256 = prompt_sha256()


def _truthy(raw: str | None) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


def jevgate_enabled(flag: bool | None = None) -> bool:
    """Explicit bool wins. Otherwise ``HYPERLEX_JEVGATE`` (default off)."""
    if flag is not None:
        return bool(flag)
    return _truthy(os.environ.get(JEVGATE_ENV))


def jevgate_from_args(args: Any) -> bool | None:
    """``--no-jevgate`` forces the cascade off; ``--jevgate`` forces it on."""
    if bool(getattr(args, "no_jevgate", False)):
        return False
    if bool(getattr(args, "jevgate", False)):
        return True
    return None


def scrub_text(text: str, key: str = "") -> str:
    """Drop the API key and bearer tokens from anything we might surface."""
    cleaned = str(text if text is not None else "")
    if key:
        cleaned = cleaned.replace(key, "[R]")
    cleaned = re.sub(r"Bearer\s+\S+", "Bearer [R]", cleaned, flags=re.IGNORECASE)
    return cleaned[:200]


def _offline() -> bool:
    return _truthy(os.environ.get("HYPERLEX_OFFLINE"))


def load_api_key() -> str:
    """Key from the environment only. No default path and no hardcoded key."""
    key = os.environ.get("JEV_API_KEY", "").strip()
    if key:
        return key
    key = os.environ.get("TYPESAFE_AI_API_KEY", "").strip()
    if key:
        return key
    path = os.environ.get("JEV_KEY_FILE", "").strip()
    if not path:
        raise JevCallError("missing_key", "JEV_API_KEY is not set")
    try:
        key = Path(path).expanduser().read_text(encoding="utf-8").strip()
    except OSError:
        raise JevCallError("missing_key", "JEV_KEY_FILE could not be read") from None
    if not key:
        raise JevCallError("missing_key", "JEV_KEY_FILE is empty")
    return key


def _is_prob(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def wire_questions(questions: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """SDK sends boolean questions as TypeSafe ``noul``. Does not mutate QUESTIONS."""
    source = QUESTIONS if questions is None else questions
    wired: dict[str, Any] = {}
    for key, question in source.items():
        copied = dict(question)
        if copied.get("type") == "boolean":
            copied["type"] = "noul"
        criteria = copied.get("criteria")
        if isinstance(criteria, dict):
            copied["criteria"] = dict(criteria)
        wired[key] = copied
    return wired


def _layout_module():
    import importlib
    import importlib.util

    try:
        return importlib.import_module("hyperlexical.layout")
    except ImportError:
        path = Path(__file__).resolve().parents[3] / "scripts" / "shadow" / "hyperlexical" / "layout.py"
        if not path.is_file():
            raise JevCallError("layout_unavailable", "hyperlexical.layout is not importable") from None
        spec = importlib.util.spec_from_file_location("hyperlexical.layout", path)
        if spec is None or spec.loader is None:
            raise JevCallError("layout_unavailable", "hyperlexical.layout is not importable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


def eight_families() -> tuple[str, ...]:
    """Family order from ``hyperlexical.layout.FAMILIES``, excluding ``none``."""
    global _EIGHT
    if _EIGHT is not None:
        return _EIGHT
    layout = _layout_module()
    order = tuple(name for name in layout.FAMILIES if name != "none")
    if len(order) != 8:
        raise JevCallError("layout_unavailable", "FAMILIES must list 8 families plus none")
    _EIGHT = order
    return order


def _normalize_answer(answer: Any) -> dict[str, Any]:
    if not isinstance(answer, dict):
        raise JevCallError("parse_error", "answer is not an object")
    kind = answer.get("type")
    if kind == "noul":
        return {"type": "boolean", "probability": answer.get("noul")}
    if kind == "boolean":
        return {"type": "boolean", "probability": answer.get("probability")}
    if kind == "choice":
        return {
            "type": "choice",
            "choice": answer.get("choice"),
            "probabilities": answer.get("probabilities"),
        }
    raise JevCallError("parse_error", "unsupported answer type")


def normalize_evaluate_payload(payload: Any) -> dict[str, Any]:
    """Map a ``/systemone`` body onto the SDK answer shape.

    ``model`` must be present and equal ``jev-1.13.0``. A missing id is a
    mismatch, not the requested model filled in after the fact.
    """
    if not isinstance(payload, dict):
        raise JevCallError("parse_error", "response is not an object")
    answers_raw = payload.get("answers")
    if not isinstance(answers_raw, dict):
        raise JevCallError("parse_error", "answers missing")
    answers = {key: _normalize_answer(value) for key, value in answers_raw.items()}
    return {"model_id": payload.get("model"), "answers": answers}


def _validate_pass(result: Mapping[str, Any]) -> dict[str, Any]:
    model_id = result.get("model_id")
    if model_id != MODEL_ID:
        raise JevCallError("model_mismatch", f"model_id={model_id}")
    answers = result.get("answers")
    if not isinstance(answers, dict):
        raise JevCallError("parse_error", "answers missing")
    in_scope = answers.get("in_scope")
    any_slang = answers.get("any_slang")
    family = answers.get("family")
    if not isinstance(in_scope, dict) or in_scope.get("type") != "boolean":
        raise JevCallError("parse_error", "in_scope")
    if not isinstance(any_slang, dict) or any_slang.get("type") != "boolean":
        raise JevCallError("parse_error", "any_slang")
    if not _is_prob(in_scope.get("probability")) or not _is_prob(any_slang.get("probability")):
        raise JevCallError("parse_error", "boolean probability")
    if not isinstance(family, dict):
        raise JevCallError("parse_error", "family")
    choice = family.get("choice")
    if choice not in CRITERIA_KEYS:
        raise JevCallError("parse_error", "family choice")
    probs = family.get("probabilities")
    if not isinstance(probs, dict) or any(not _is_prob(probs.get(key)) for key in CRITERIA_KEYS):
        raise JevCallError("parse_error", "family probabilities")
    return {
        "model_id": model_id,
        "choice": choice,
        "in_scope": float(in_scope["probability"]),
        "any_slang": float(any_slang["probability"]),
        "probabilities": {key: float(probs[key]) for key in CRITERIA_KEYS},
    }


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _argmax(means: Mapping[str, float], order: tuple[str, ...]) -> str:
    """First family in ``order`` wins ties (strict ``>``)."""
    best = order[0]
    best_p = float(means[best])
    for name in order[1:]:
        score = float(means[name])
        if score > best_p:
            best = name
            best_p = score
    return best


def _flat_family_means(means: Mapping[str, float], order: tuple[str, ...]) -> bool:
    """True when every family mean is the same, including all zeros.

    Argmax would be only the layout tie-break, so there is no family signal.
    """
    if not order:
        return True
    first = float(means[order[0]])
    return all(float(means[name]) == first for name in order)


def decide_family(passes: list[Mapping[str, Any]], order: tuple[str, ...]) -> dict[str, Any]:
    """Aggregate pass means. Choice / in_scope / any_slang are logged only."""
    p_none = _mean([float(item["probabilities"]["none"]) for item in passes])
    means = {
        name: _mean([float(item["probabilities"][name]) for item in passes])
        for name in order
    }
    ranked = _argmax(means, order)
    family = ranked if p_none < TAU else "none"
    best = None if _flat_family_means(means, order) else ranked
    return {
        "family": family,
        "jev_best_guess": best,
        "jev_p_none": p_none,
        "jev_family_means": means,
        "jev_log": {
            "choice": [item["choice"] for item in passes],
            "in_scope": [item["in_scope"] for item in passes],
            "any_slang": [item["any_slang"] for item in passes],
        },
    }


class JevHttpClient:
    """POST ``{base}/systemone``, the same body ``@ai-sdk/typesafe-ai`` sends."""

    def __init__(self, *, timeout: float = REQUEST_TIMEOUT_S) -> None:
        self.timeout = timeout

    def evaluate(self, state: Mapping[str, Any]) -> dict[str, Any]:
        if _offline():
            raise JevCallError("offline", "HYPERLEX_OFFLINE refuses the Jev call")
        key = load_api_key()
        base = os.environ.get("JEV_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
        try:
            from hyperlex.guards import require_http_url

            base = require_http_url(base, name="JEV_BASE_URL").rstrip("/")
        except Exception as exc:
            raise JevCallError("provider_error", scrub_text(str(exc), key)) from None
        body = {
            "model": MODEL_ID,
            "state": {"text": state.get("text")},
            "questions": wire_questions(),
        }
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{base}/systemone",
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "hyperlex-jevgate/1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", "replace")
            except Exception:
                detail = ""
            raise JevCallError("provider_error", scrub_text(detail or str(exc), key)) from None
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            message = str(getattr(exc, "reason", None) or exc)
            reason = "timeout" if re.search(r"timed out|timeout|aborted", message, re.I) else "provider_error"
            raise JevCallError(reason, scrub_text(message, key)) from None
        except Exception as exc:
            raise JevCallError("provider_error", scrub_text(str(exc), key)) from None
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            raise JevCallError("parse_error", "response was not json") from None
        try:
            return normalize_evaluate_payload(parsed)
        except JevCallError:
            raise
        except Exception as exc:
            raise JevCallError("parse_error", scrub_text(str(exc), key)) from None


def _error_payload(exc: JevCallError, key: str = "") -> dict[str, Any]:
    detail = scrub_text(exc.detail, key)
    payload: dict[str, Any] = {"flag": True, "reason": exc.reason}
    if detail:
        payload["detail"] = detail
    return payload


def _blank(
    term: str,
    *,
    family: str,
    source: str,
    enabled: bool,
    lineage: dict[str, Any] | None = None,
    jev_error: dict[str, Any] | None = None,
    gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": "hyperlex.classify.v1",
        "gate": "jevgate-1",
        "term": term,
        "family": family,
        "source": source,
        "jevgate_enabled": enabled,
        "tau": TAU,
        "model": MODEL_ID,
        "prompt_sha256": FROZEN_PROMPT_SHA256,
        "lineage": lineage,
        "jev_best_guess": None if gate is None else gate.get("jev_best_guess"),
        "jev_p_none": None if gate is None else gate.get("jev_p_none"),
        "jev_family_means": None if gate is None else gate.get("jev_family_means"),
        "jev_log": None if gate is None else gate.get("jev_log"),
        "jev_error": jev_error,
        "brier": None,
    }


def _one_pass(client: Any, state: dict[str, str], key: str) -> dict[str, Any]:
    """One request, then one identical retry. The second failure propagates."""
    last: JevCallError | None = None
    for _attempt in (0, 1):
        try:
            raw = client.evaluate(state)
            if not isinstance(raw, Mapping):
                raise JevCallError("parse_error", "evaluate did not return an object")
            # Accept either a wire payload or the already-normalized SDK shape.
            if "answers" in raw and "model_id" not in raw:
                raw = normalize_evaluate_payload(raw)
            return _validate_pass(raw)
        except JevCallError as exc:
            last = JevCallError(exc.reason, scrub_text(exc.detail, key))
        except Exception as exc:
            last = JevCallError("provider_error", scrub_text(str(exc), key))
    assert last is not None
    raise last


def _current_key() -> str:
    """Best-effort key for scrubbing errors. Empty if none is configured."""
    key = os.environ.get("JEV_API_KEY", "").strip() or os.environ.get("TYPESAFE_AI_API_KEY", "").strip()
    if key:
        return key
    path = os.environ.get("JEV_KEY_FILE", "").strip()
    if not path:
        return ""
    try:
        return Path(path).expanduser().read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def classify_term(
    term: str,
    *,
    jevgate: bool | None = None,
    client: Any = None,
    match_fn: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Classify one short term. Never raises for Jev failures."""
    text = str(term or "").strip()
    enabled = jevgate_enabled(jevgate)
    if not text:
        return _blank(text, family="none", source="cascade", enabled=enabled)

    if match_fn is None:
        from hyperlex.analysis import match_lineage

        match_fn = match_lineage
    try:
        hit = match_fn(text, use_vector=False)
    except TypeError:
        hit = match_fn(text)
    if isinstance(hit, dict) and hit.get("family_id"):
        return _blank(
            text,
            family=str(hit["family_id"]),
            source="match_lineage",
            enabled=enabled,
            lineage=dict(hit),
        )
    if not enabled:
        return _blank(text, family="none", source="cascade", enabled=False)

    if not PROMPT_SHA_OK or not prompt_is_frozen():
        return _blank(
            text,
            family="none",
            source="jevgate",
            enabled=True,
            jev_error={"flag": True, "reason": "prompt_sha_mismatch"},
        )

    caller = client if client is not None else JevHttpClient()
    state = {"text": text}
    key = _current_key()
    passes: list[dict[str, Any]] = []
    try:
        for _ in range(PASSES):
            passes.append(_one_pass(caller, state, key))
        try:
            order = eight_families()
        except JevCallError as exc:
            return _blank(
                text,
                family="none",
                source="jevgate",
                enabled=True,
                jev_error=_error_payload(exc, key),
            )
        gate = decide_family(passes, order)
    except JevCallError as exc:
        return _blank(
            text,
            family="none",
            source="jevgate",
            enabled=True,
            jev_error=_error_payload(exc, key),
        )
    except Exception as exc:
        return _blank(
            text,
            family="none",
            source="jevgate",
            enabled=True,
            jev_error=_error_payload(JevCallError("provider_error", scrub_text(str(exc), key)), key),
        )
    return _blank(
        text,
        family=str(gate["family"]),
        source="jevgate",
        enabled=True,
        gate=gate,
    )
