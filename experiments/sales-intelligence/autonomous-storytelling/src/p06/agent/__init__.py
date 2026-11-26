"""Gói điều phối đồ thị LangGraph 8 node cho luồng kể chuyện tự động P06 (`agent/`)."""

from __future__ import annotations

from p06.agent.deps import AgentTurnResult, GraphRuntimeDeps, TurnExecutionContext
from p06.agent.graph import build_storytelling_graph, run_storytelling_turn
from p06.agent.routing import (
    NODE_BOUNDED_REWRITE,
    NODE_CHECK_REPETITION,
    NODE_DRAFT_CHUNK,
    NODE_FINALIZE_CANDIDATE,
    NODE_LOAD_CONTEXT,
    NODE_PLAN_CHUNK,
    NODE_SAFE_FALLBACK,
    NODE_VERIFY_P05,
    route_after_bounded_rewrite,
    route_after_check_repetition,
    route_after_draft_chunk,
    route_after_load_context,
    route_after_plan_chunk,
    route_after_verify_p05,
)

__all__ = [
    "AgentTurnResult",
    "GraphRuntimeDeps",
    "TurnExecutionContext",
    "build_storytelling_graph",
    "run_storytelling_turn",
    "NODE_LOAD_CONTEXT",
    "NODE_PLAN_CHUNK",
    "NODE_DRAFT_CHUNK",
    "NODE_CHECK_REPETITION",
    "NODE_VERIFY_P05",
    "NODE_BOUNDED_REWRITE",
    "NODE_SAFE_FALLBACK",
    "NODE_FINALIZE_CANDIDATE",
    "route_after_load_context",
    "route_after_plan_chunk",
    "route_after_draft_chunk",
    "route_after_check_repetition",
    "route_after_verify_p05",
    "route_after_bounded_rewrite",
]
