"""Fail-closed operator gates (settle, URL, cloud write, receipt digest).

Additive hardening. Does not invent Brier, auto-settle, or log secrets.
"""

from __future__ import annotations

import os
import sys
from typing import Optional
from urllib.parse import urlparse


SETTLE_CONFIRM_PHRASE = "SETTLE"
X_API_ALLOWED_HOSTS = frozenset({"api.twitter.com", "api.x.com"})
HTTP_SCHEMES = frozenset({"http", "https"})


class SettleGateError(ValueError):
    """Scored settlement refused (missing token / TTY / authority)."""


class CloudWriteError(PermissionError):
    """Cloud vector write refused (missing HYPERLEX_CLOUD_WRITE / TTY ack)."""


class UrlGateError(ValueError):
    """URL refused by allowlist / scheme / userinfo / port rules."""


def _truthy(raw: Optional[str]) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


def settle_token_from_env() -> str:
    return str(os.environ.get("HYPERLEX_SETTLE_TOKEN") or "").strip()


def require_scored_settle_gate(
    *,
    settlement_decision: str,
    authority_kind: str,
    authority_ref: Optional[str],
    settle_token: Optional[str] = None,
    stdin=None,
    stdout=None,
) -> None:
    """Gate scored TRUE/FALSE settlements. VOID/CONFLICT skip this gate.

    Token is never returned or logged. Piped / non-TTY stdin cannot confirm.
    """
    decision = str(settlement_decision or "").upper()
    if decision not in {"TRUE", "FALSE"}:
        return

    kind = str(authority_kind or "").strip().lower()
    if kind == "advisory":
        raise SettleGateError("scored settlement refuses authority.kind=advisory")

    ref = str(authority_ref or "").strip()
    if not ref:
        raise SettleGateError("scored settlement requires non-empty authority.ref")

    token = str(settle_token or "").strip() or settle_token_from_env()
    if token:
        return

    in_stream = stdin if stdin is not None else sys.stdin
    out_stream = stdout if stdout is not None else sys.stdout
    is_tty = bool(getattr(in_stream, "isatty", lambda: False)())
    if not is_tty:
        raise SettleGateError(
            "scored settlement requires HYPERLEX_SETTLE_TOKEN / --settle-token "
            "(non-TTY stdin cannot confirm; piped yes is refused)"
        )

    if out_stream is not None and hasattr(out_stream, "write"):
        out_stream.write(
            f"Confirm scored settlement: type {SETTLE_CONFIRM_PHRASE} and press Enter\n"
        )
        try:
            out_stream.flush()
        except Exception:
            pass
    try:
        typed = str(in_stream.readline() if hasattr(in_stream, "readline") else "").strip()
    except Exception as exc:
        raise SettleGateError("scored settlement TTY confirm failed") from exc
    if typed != SETTLE_CONFIRM_PHRASE:
        raise SettleGateError(
            f"scored settlement TTY confirm refused (expected {SETTLE_CONFIRM_PHRASE})"
        )


def x_api_custom_allowed(*, allow_custom: Optional[bool] = None) -> bool:
    if allow_custom is True:
        return True
    return _truthy(os.environ.get("HYPERLEX_X_API_BASE_ALLOW_CUSTOM"))


def validate_x_api_base(
    raw: str,
    *,
    allow_custom: Optional[bool] = None,
) -> str:
    """Return a sanitized https X API base or raise UrlGateError. No request."""
    base = str(raw or "").strip()
    if not base:
        raise UrlGateError("X API base is empty")
    parsed = urlparse(base)
    if parsed.scheme != "https":
        raise UrlGateError("X API base must be https")
    if parsed.username or parsed.password:
        raise UrlGateError("X API base must not include userinfo")
    host = (parsed.hostname or "").lower()
    if not host:
        raise UrlGateError("X API base host is empty")
    port = parsed.port
    if port is not None and port != 443:
        raise UrlGateError("X API base must use the default https port")
    custom = x_api_custom_allowed(allow_custom=allow_custom)
    if host not in X_API_ALLOWED_HOSTS and not custom:
        raise UrlGateError(
            f"X API host not allowlisted: {host} "
            "(set HYPERLEX_X_API_BASE_ALLOW_CUSTOM=1 to override)"
        )
    path = parsed.path.rstrip("/")
    return f"https://{host}{path}"


def require_http_url(raw: str, *, name: str = "url") -> str:
    """Allow only http/https (reject file:// and other schemes)."""
    text = str(raw or "").strip()
    if not text:
        raise UrlGateError(f"{name} is empty")
    parsed = urlparse(text)
    if parsed.scheme not in HTTP_SCHEMES:
        raise UrlGateError(f"{name} must be http or https (refusing {parsed.scheme or 'missing'}://)")
    if not parsed.netloc:
        raise UrlGateError(f"{name} host is empty")
    return text


_TTY_CLOUD_WRITE_ACK = False


def set_tty_cloud_write_ack(value: bool, *, stdin=None) -> None:
    """CLI --i-understand-cloud-write: honor only when stdin is a TTY."""
    global _TTY_CLOUD_WRITE_ACK
    in_stream = stdin if stdin is not None else sys.stdin
    _TTY_CLOUD_WRITE_ACK = bool(value) and bool(getattr(in_stream, "isatty", lambda: False)())


def cloud_write_permitted(*, i_understand: bool = False, stdin=None) -> bool:
    if _truthy(os.environ.get("HYPERLEX_CLOUD_WRITE")):
        return True
    in_stream = stdin if stdin is not None else sys.stdin
    if _TTY_CLOUD_WRITE_ACK and bool(getattr(in_stream, "isatty", lambda: False)()):
        return True
    if i_understand and bool(getattr(in_stream, "isatty", lambda: False)()):
        return True
    return False


def require_cloud_write(*, i_understand: bool = False, stdin=None) -> None:
    if cloud_write_permitted(i_understand=i_understand, stdin=stdin):
        return
    raise CloudWriteError(
        "cloud vector write refused: set HYPERLEX_CLOUD_WRITE=1 "
        "or pass --i-understand-cloud-write on a TTY "
        "(auto-loaded ~/.hermes/.env / ~/.hyperlex/.env keys are not write permission)"
    )


def receipt_legacy_integrity_enabled() -> bool:
    return _truthy(os.environ.get("HYPERLEX_RECEIPT_LEGACY_INTEGRITY"))


__all__ = [
    "SETTLE_CONFIRM_PHRASE",
    "X_API_ALLOWED_HOSTS",
    "SettleGateError",
    "CloudWriteError",
    "UrlGateError",
    "require_scored_settle_gate",
    "validate_x_api_base",
    "require_http_url",
    "cloud_write_permitted",
    "require_cloud_write",
    "receipt_legacy_integrity_enabled",
    "x_api_custom_allowed",
]
