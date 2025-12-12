from __future__ import annotations

import contextlib
import contextvars
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import get_close_matches
from typing import Any, Iterator

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


class _CloudRunJsonFormatter(logging.Formatter):
    """Emit JSON logs that Cloud Run / Cloud Logging can parse from stdout.

    Cloud Logging recognizes a JSON payload with fields like:
    - severity: INFO/WARNING/ERROR
    - message
    - time (RFC3339)
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "logger": record.name,
        }

        # Common convenience fields
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        # Include extra keys provided via logger.*(..., extra={...})
        # Filter out standard LogRecord attributes.
        standard = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
        }
        for k, v in record.__dict__.items():
            if k in standard:
                continue
            payload[k] = v

        return json.dumps(payload, ensure_ascii=False, default=str)


_LOGGING_CONFIGURED = False


def configure_logging(level: str | int | None = None) -> logging.Logger:
    """Configure a JSON-to-stdout logger suitable for Google Cloud Run.

    This intentionally configures only the project logger ("siip") to avoid
    fighting Uvicorn's logging configuration.
    """

    global _LOGGING_CONFIGURED
    logger = logging.getLogger("siip")

    if _LOGGING_CONFIGURED:
        return logger

    resolved_level: int
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")

    if isinstance(level, int):
        resolved_level = level
    else:
        resolved_level = getattr(logging, str(level).upper(), logging.INFO)

    logger.setLevel(resolved_level)
    logger.propagate = False

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(resolved_level)
    handler.setFormatter(_CloudRunJsonFormatter())
    logger.addHandler(handler)

    _LOGGING_CONFIGURED = True
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a configured project logger.

    Names are nested under "siip" so handlers/levels stay consistent.
    """

    configure_logging()
    if not name:
        return logging.getLogger("siip")
    if name == "siip" or name.startswith("siip."):
        return logging.getLogger(name)
    return logging.getLogger(f"siip.{name}")


@dataclass
class _TimingStat:
    count: int = 0
    total_s: float = 0.0
    min_s: float = float("inf")
    max_s: float = 0.0

    def add(self, elapsed_s: float) -> None:
        self.count += 1
        self.total_s += elapsed_s
        if elapsed_s < self.min_s:
            self.min_s = elapsed_s
        if elapsed_s > self.max_s:
            self.max_s = elapsed_s

    def to_dict(self) -> dict[str, float | int]:
        avg = self.total_s / self.count if self.count else 0.0
        min_v = 0.0 if self.min_s == float("inf") else self.min_s
        return {
            "count": self.count,
            "total_s": round(self.total_s, 6),
            "avg_s": round(avg, 6),
            "min_s": round(min_v, 6),
            "max_s": round(self.max_s, 6),
        }


class TimingCollector:
    """Accumulate timings by name for a single request/run."""

    def __init__(self) -> None:
        self._stats: dict[str, _TimingStat] = {}

    def add(self, name: str, elapsed_s: float) -> None:
        stat = self._stats.get(name)
        if stat is None:
            stat = _TimingStat()
            self._stats[name] = stat
        stat.add(elapsed_s)

    def breakdown(self) -> dict[str, dict[str, float | int]]:
        items = sorted(self._stats.items(), key=lambda kv: kv[1].total_s, reverse=True)
        return {k: v.to_dict() for k, v in items}

    def to_log_extra(self) -> dict[str, Any]:
        return {"breakdown": self.breakdown()}


_timing_collector_var: contextvars.ContextVar[TimingCollector | None] = (
    contextvars.ContextVar("siip_timing_collector", default=None)
)


@contextlib.contextmanager
def timing_session() -> Iterator[TimingCollector]:
    """Create a per-request/per-run TimingCollector and bind it to the context."""

    collector = TimingCollector()
    token = _timing_collector_var.set(collector)
    try:
        yield collector
    finally:
        _timing_collector_var.reset(token)


@contextlib.contextmanager
def timed(name: str, *, collector: TimingCollector | None = None) -> Iterator[None]:
    """Time a block using time.perf_counter() and record into the active collector."""

    active = collector if collector is not None else _timing_collector_var.get()
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        if active is not None:
            active.add(name, elapsed)


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
