"""Prometheus metrics definitions for LLM instrumentation."""

from prometheus_client import Counter, Histogram, Gauge

# Latency buckets tailored for LLM response times (in seconds)
# Range from 0.5s to 60s+ to capture streaming tool loops
LATENCY_BUCKETS = (0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 20.0, 30.0, 45.0, 60.0, float("inf"))

# Session metrics
LLM_SESSIONS_TOTAL = Counter(
    "llm_sessions_total",
    "Total game sessions started",
    ["model"],
)

LLM_SESSION_ACTIVE = Gauge(
    "llm_session_active",
    "Currently active SSE connections",
)

# API call metrics
LLM_API_REQUESTS_TOTAL = Counter(
    "llm_api_requests_total",
    "Total Anthropic API calls",
    ["model", "has_tools"],
)

LLM_API_DURATION_SECONDS = Histogram(
    "llm_api_duration_seconds",
    "Anthropic API call duration in seconds",
    ["model", "tool_loop_iteration"],
    buckets=LATENCY_BUCKETS,
)

# Token metrics
LLM_TOKENS_INPUT_TOTAL = Counter(
    "llm_tokens_input_total",
    "Total input tokens consumed",
    ["model"],
)

LLM_TOKENS_OUTPUT_TOTAL = Counter(
    "llm_tokens_output_total",
    "Total output tokens generated",
    ["model"],
)

LLM_TOKENS_CACHE_READ_TOTAL = Counter(
    "llm_tokens_cache_read_total",
    "Total cache read tokens (prompt caching)",
    ["model"],
)

LLM_TOKENS_CACHE_CREATION_TOTAL = Counter(
    "llm_tokens_cache_creation_total",
    "Total cache creation tokens (prompt caching)",
    ["model"],
)

# Tool metrics
LLM_TOOL_CALLS_TOTAL = Counter(
    "llm_tool_calls_total",
    "Total tool executions",
    ["tool_name", "status"],
)

# Error metrics
LLM_ERRORS_TOTAL = Counter(
    "llm_errors_total",
    "Total LLM errors",
    ["model", "error_type"],
)

# Thinking metrics
LLM_THINKING_REQUESTS_TOTAL = Counter(
    "llm_thinking_requests_total",
    "Total requests that used extended thinking",
    ["model"],
)

# Game metrics
DWELL_TIME_BUCKETS = (5, 15, 30, 60, 120, 300, 600, 900, 1800, float("inf"))

LOCATION_DWELL_SECONDS = Histogram(
    "game_location_dwell_seconds",
    "Time players spend in each location before moving",
    ["location_id"],
    buckets=DWELL_TIME_BUCKETS,
)

# Session duration buckets: 30s, 1m, 2m, 5m, 10m, 15m, 30m, 1h, 1.5h, 2h
SESSION_DURATION_BUCKETS = (30, 60, 120, 300, 600, 900, 1800, 3600, 5400, 7200, float("inf"))

GAME_SESSION_DURATION_SECONDS = Histogram(
    "game_session_duration_seconds",
    "Duration of player game sessions in seconds",
    buckets=SESSION_DURATION_BUCKETS,
)

GAME_VICTORIES_TOTAL = Counter(
    "game_victories_total",
    "Total game victories",
)

GAME_RESTARTS_TOTAL = Counter(
    "game_restarts_total",
    "Total game restarts",
    ["reason"],
)

GAME_DEATHS_TOTAL = Counter(
    "game_deaths_total",
    "Total player deaths",
    ["death_type"],
)
