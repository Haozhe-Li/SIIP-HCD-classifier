# -*- coding: utf-8 -*-
from difflib import get_close_matches

KNOWN_SPACES = {
    "understand",
    "synthesize",
    "ideate",
    "prototype",
    "implement",
}

KNOWN_SUBSPACES = {
    "explore",
    "observe",
    "empathize",
    "reflect",
    "debrief",
    "organize",
    "interpret",
    "define",
    "brainstorm",
    "propose",
    "plan",
    "narrow concepts",
    "create",
    "engage",
    "evaluate",
    "iterate",
    "support",
    "sustain",
    "evolve",
    "execute",
}


def _normalize_item(item: str, known: set[str]) -> str | None:
    s = (item or "").strip().lower()
    if not s:
        return None
    if s in known:
        return s
    # try to match by removing extra punctuation
    s_clean = "".join(ch for ch in s if ch.isalnum() or ch.isspace())
    if s_clean in known:
        return s_clean
    # fuzzy match
    candidates = get_close_matches(s, list(known), n=1, cutoff=0.75)
    if candidates:
        return candidates[0]
    candidates = get_close_matches(s_clean, list(known), n=1, cutoff=0.75)
    return candidates[0] if candidates else None


def normalize_list(items: list[str], known: set[str]) -> list[str]:
    normalized: list[str] = []
    seen = set()
    for it in items or []:
        norm = _normalize_item(it, known)
        if norm and norm not in seen:
            normalized.append(norm)
            seen.add(norm)
    return normalized
