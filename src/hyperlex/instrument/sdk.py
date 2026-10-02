"""SDK for HYPERLEX_INSTRUMENT_V1 — in-process and HTTP clients share observe()."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Optional, Sequence

from .runtime import get_capabilities, get_manifest, health, observe


class InstrumentClient:
    """In-process client (preferred for Abraxas same-host use)."""

    def observe(
        self,
        text: str,
        *,
        requested: Optional[Sequence[str]] = None,
    ) -> dict[str, Any]:
        return observe(text, requested=requested)

    def health(self) -> dict[str, Any]:
        return health()

    def manifest(self) -> dict[str, Any]:
        return get_manifest()

    def capabilities(self) -> dict[str, Any]:
        return get_capabilities()


class InstrumentHttpClient:
    """HTTP client for the minimal /v1 interface."""

    def __init__(self, base_url: str = "http://127.0.0.1:8741") -> None:
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str) -> dict[str, Any]:
        req = urllib.request.Request(f"{self.base_url}{path}", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def observe(
        self,
        text: str,
        *,
        requested: Optional[Sequence[str]] = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"text": text}
        if requested is not None:
            body["requested"] = list(requested)
        return self._post("/v1/observe", body)

    def health(self) -> dict[str, Any]:
        return self._get("/v1/health")

    def manifest(self) -> dict[str, Any]:
        return self._get("/v1/manifest")

    def capabilities(self) -> dict[str, Any]:
        return self._get("/v1/capabilities")
