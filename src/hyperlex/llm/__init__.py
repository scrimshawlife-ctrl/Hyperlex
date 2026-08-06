"""Optional governed LLM helpers for Hyperlex.

Default: disabled. Never required for skill operation.
"""

from .governed import (
    llm_enabled,
    enrich_neologisms,
    enrich_mutation_candidates,
    GovernedLLMError,
)

__all__ = [
    "llm_enabled",
    "enrich_neologisms",
    "enrich_mutation_candidates",
    "GovernedLLMError",
]
