"""Canonical ingest source catalog, aliases, and route presets.

Single source of truth for CLI `sources`, `ingest --route`, and
`resolve_source` used by `ingest_signal` / `fetch_ingest`.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

# Canonical source id → metadata
SOURCE_CATALOG: Dict[str, Dict[str, Any]] = {
    "mock": {
        "kind": "deterministic",
        "network": False,
        "description": "No network; deterministic query-aware fixture",
        "default": True,
    },
    "glossary": {
        "kind": "web",
        "network": True,
        "description": "Action Network betting glossary",
    },
    "glossary_expanded": {
        "kind": "web",
        "network": True,
        "description": "Multi-glossary pack (AN + wiki slang + urban)",
    },
    "reddit": {
        "kind": "web",
        "network": True,
        "description": "Reddit keyword search (old.reddit)",
    },
    "urban": {
        "kind": "web",
        "network": True,
        "description": "Urban Dictionary public API",
    },
    "wikipedia": {
        "kind": "web",
        "network": True,
        "description": "Wikipedia page summary",
    },
    "x_search": {
        "kind": "social",
        "network": True,
        "description": "X/Twitter via API bearer, xurl CLI, or structured stub",
    },
    "crawl4ai": {
        "kind": "web",
        "network": True,
        "description": "Crawl4AI-backed web crawl signal",
    },
    "combined": {
        "kind": "composed",
        "network": True,
        "description": "glossary→urban→reddit→wiki→x→crawl4ai with graceful fallback",
    },
}

# User-facing aliases → canonical id
SOURCE_ALIASES: Dict[str, str] = {
    "mock": "mock",
    "offline": "mock",
    "local": "mock",
    "test": "mock",
    "fixture": "mock",
    "glossary": "glossary",
    "real": "glossary",
    "web": "glossary",
    "an": "glossary",
    "actionnetwork": "glossary",
    "glossary_expanded": "glossary_expanded",
    "glossaries": "glossary_expanded",
    "expanded": "glossary_expanded",
    "reddit": "reddit",
    "urban": "urban",
    "ud": "urban",
    "wikipedia": "wikipedia",
    "wiki": "wikipedia",
    "x_search": "x_search",
    "x": "x_search",
    "twitter": "x_search",
    "crawl4ai": "crawl4ai",
    "firecrawl": "crawl4ai",
    "crawl": "crawl4ai",
    "combined": "combined",
    "all": "combined",
    "multi": "combined",
    "live": "combined",
}

# Named operator routes (pick a source without memorizing adapters)
ROUTE_PRESETS: Dict[str, Dict[str, Any]] = {
    "offline": {
        "source": "mock",
        "description": "Force mock (no network). Same as HYPERLEX_OFFLINE=1 for non-mock requests.",
        "network": False,
    },
    "mock": {
        "source": "mock",
        "description": "Deterministic fixture only",
        "network": False,
    },
    "default": {
        "source": "mock",
        "description": "Safe default for operators and cron burn-in",
        "network": False,
    },
    "live": {
        "source": "combined",
        "description": "Network multi-source merge (needs network + optional deps)",
        "network": True,
    },
    "glossary": {
        "source": "glossary",
        "description": "Primary betting glossary only",
        "network": True,
    },
    "social": {
        "source": "x_search",
        "description": "X/Twitter path (bearer / xurl / stub)",
        "network": True,
    },
}


def offline_mode() -> bool:
    flag = str(os.environ.get("HYPERLEX_OFFLINE", "")).strip().lower()
    return flag in {"1", "true", "yes", "on"}


def resolve_source(
    name: Optional[str] = None,
    *,
    route: Optional[str] = None,
    force_offline: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Resolve a user source name or route preset to a canonical source.

    Returns:
      {
        source, requested, route, network, known, aliases_of,
        offline_forced, description, kind
      }
    """
    requested = (name or "").strip() or None
    route_name = (route or "").strip().lower() or None
    offline = offline_mode() if force_offline is None else bool(force_offline)

    # Route wins over raw source when both given (route is operator intent)
    if route_name:
        preset = ROUTE_PRESETS.get(route_name)
        if preset is None:
            return {
                "ok": False,
                "error": f"unknown route={route_name!r}; use offline|mock|default|live|glossary|social",
                "source": "mock",
                "requested": requested,
                "route": route_name,
                "known": False,
                "offline_forced": offline,
                "available_routes": sorted(ROUTE_PRESETS.keys()),
            }
        canonical = preset["source"]
        if offline and preset.get("network"):
            return {
                "ok": True,
                "source": "mock",
                "requested": requested or route_name,
                "route": route_name,
                "network": False,
                "known": True,
                "kind": "deterministic",
                "description": SOURCE_CATALOG["mock"]["description"],
                "offline_forced": True,
                "note": f"route={route_name} requested network source; offline forced → mock",
            }
        meta = SOURCE_CATALOG[canonical]
        return {
            "ok": True,
            "source": canonical,
            "requested": requested or route_name,
            "route": route_name,
            "network": bool(meta.get("network")),
            "known": True,
            "kind": meta.get("kind"),
            "description": preset.get("description") or meta.get("description"),
            "offline_forced": offline,
        }

    raw = (requested or "mock").lower().strip()
    canonical = SOURCE_ALIASES.get(raw)
    known = canonical is not None
    if not known:
        # Unknown → fail closed to mock with warning
        return {
            "ok": False,
            "source": "mock",
            "requested": raw,
            "route": None,
            "network": False,
            "known": False,
            "kind": "deterministic",
            "description": f"Unknown source {raw!r}; falling back to mock",
            "offline_forced": offline,
            "error": f"unknown source={raw!r}",
            "available": sorted(SOURCE_CATALOG.keys()),
            "aliases": sorted(SOURCE_ALIASES.keys()),
        }

    meta = SOURCE_CATALOG[canonical]
    if offline and meta.get("network"):
        return {
            "ok": True,
            "source": "mock",
            "requested": raw,
            "route": None,
            "network": False,
            "known": True,
            "kind": "deterministic",
            "description": SOURCE_CATALOG["mock"]["description"],
            "offline_forced": True,
            "note": f"source={raw}→{canonical} is network; offline forced → mock",
            "intended_source": canonical,
        }

    return {
        "ok": True,
        "source": canonical,
        "requested": raw,
        "route": None,
        "network": bool(meta.get("network")),
        "known": True,
        "kind": meta.get("kind"),
        "description": meta.get("description"),
        "offline_forced": offline,
    }


def list_sources(*, include_aliases: bool = True) -> Dict[str, Any]:
    """Operator-facing catalog for `sources` CLI."""
    sources = []
    for name, meta in SOURCE_CATALOG.items():
        aliases = sorted(a for a, c in SOURCE_ALIASES.items() if c == name and a != name)
        entry = {
            "name": name,
            "kind": meta.get("kind"),
            "network": bool(meta.get("network")),
            "description": meta.get("description"),
            "default": bool(meta.get("default")),
        }
        if include_aliases:
            entry["aliases"] = aliases
        sources.append(entry)
    routes = [
        {"name": k, "source": v["source"], "network": v["network"], "description": v["description"]}
        for k, v in sorted(ROUTE_PRESETS.items())
    ]
    return {
        "schema": "hyperlex.sources_catalog.v1",
        "default_source": "mock",
        "offline_env": "HYPERLEX_OFFLINE=1",
        "sources": sources,
        "routes": routes,
        "note": "Prefer --route offline|live over raw adapter names when unsure.",
    }


def pick_source(
    source: Optional[str] = None,
    route: Optional[str] = None,
    *,
    force_offline: Optional[bool] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Return (canonical_source, resolve_packet). Always returns a usable source string."""
    packet = resolve_source(source, route=route, force_offline=force_offline)
    return str(packet.get("source") or "mock"), packet
