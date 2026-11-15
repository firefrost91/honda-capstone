"""Stakeholder perspectives and the metric tools that serve them.

    from rag.tools import run_tools, STAKEHOLDERS, METRICS

    results, stakeholder = run_tools("Where do trucks conflict with cyclists in Columbus?")
    for r in results:
        print(r.to_passage().text)

Today every tool is a deterministic stub returning plausible synthetic values
(see ``synthetic.py``). The metric catalogue (``metrics.py``) is the contract a
live tool must honour when it replaces a stub.
"""
from .metrics import METRICS, METRIC_LIST, MetricSpec, metrics_for
from .registry import (TOOL_KIND, TOOLS, ToolResult, build_context_for, catalog,
                       infer_location, run_tool, run_tools, select_tools, tool_hits)
from .stakeholders import STAKEHOLDERS, Stakeholder, detect_stakeholder, framing
from .synthetic import MetricValue, ToolContext

__all__ = [
    "METRICS", "METRIC_LIST", "MetricSpec", "metrics_for",
    "TOOL_KIND", "TOOLS", "ToolResult", "build_context_for", "catalog", "infer_location",
    "run_tool", "run_tools", "select_tools", "tool_hits",
    "STAKEHOLDERS", "Stakeholder", "detect_stakeholder", "framing",
    "MetricValue", "ToolContext",
]
