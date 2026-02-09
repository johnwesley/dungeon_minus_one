"""Prometheus metrics for game telemetry."""

from prometheus_client import Counter, Histogram

LOCATION_ENTRIES = Counter(
    "game_location_entries_total",
    "Total location entries by players",
    ["location"],
)

LOCATION_DWELL_SECONDS = Histogram(
    "game_location_dwell_seconds",
    "Time spent at a location before leaving",
    ["location"],
    buckets=(10, 30, 60, 120, 300, 600, 1800, 3600),
)

VICTORIES = Counter(
    "game_victories_total",
    "Total games completed (all treasures deposited, victory reached)",
)
