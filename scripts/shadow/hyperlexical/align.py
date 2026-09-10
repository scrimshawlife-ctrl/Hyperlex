"""Map surface atoms onto tokenizer spans. No torch. No Hub."""

from __future__ import annotations


def char_span(text: str, atom: str) -> tuple[int, int] | None:
    if not text or not atom:
        return None
    i = text.find(atom)
    if i < 0:
        i = text.lower().find(atom.lower())
    if i < 0:
        return None
    return i, i + len(atom)


def whitespace_offsets(text: str) -> list[tuple[int, int]]:
    spans = []
    i = 0
    while i < len(text):
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text):
            break
        j = i
        while j < len(text) and not text[j].isspace():
            j += 1
        spans.append((i, j))
        i = j
    return spans


def token_indices_for_span(offsets: list[tuple[int, int]], start: int, end: int) -> list[int]:
    hit = []
    for i, (s, e) in enumerate(offsets):
        if e <= s:
            continue
        if e <= start or s >= end:
            continue
        hit.append(i)
    return hit


def atom_token_index(text: str, atom: str, offsets: list[tuple[int, int]] | None = None) -> list[int]:
    span = char_span(text, atom)
    if span is None:
        return []
    offs = offsets if offsets is not None else whitespace_offsets(text)
    return token_indices_for_span(offs, span[0], span[1])


def offsets_from_tokenizer(tokenizer, text: str, max_len: int = 64) -> list[tuple[int, int]]:
    enc = tokenizer(
        text,
        truncation=True,
        max_length=max_len,
        return_offsets_mapping=True,
        add_special_tokens=True,
    )
    raw = enc["offset_mapping"]
    return [(int(s), int(e)) for s, e in raw]


def pool_indices(n_tokens: int, indices: list[int]) -> list[int]:
    if indices:
        return [i for i in indices if 0 <= i < n_tokens]
    if n_tokens <= 2:
        return [min(1, n_tokens - 1)]
    return [1]
