"""
Monitoring Agent - aggregates basic signals and reports integration readiness.
This avoids external calls but surfaces actionable hints for QA and resolver.
"""
from __future__ import annotations
import os
from datetime import datetime
from typing import Dict, Optional, List
from .base_agent import BaseAgent, ExecutionContext, ExecutionResult, AgentStatus, AgentCapability


class MonitoringAgent(BaseAgent):
    def get_capabilities(self) -> List[AgentCapability]:
        return [AgentCapability.CODE_ANALYSIS]

    def validate_input(self, request_data: Dict) -> tuple[bool, Optional[str]]:
        # For now, no strict requirements; honors env integration if present
        return True, None

    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        shared = context.shared_state or {}
        logs = shared.get("logs", []) or []
        validation = shared.get("validation_results", {}) or {}

        # Detect configured integrations (no external calls)
        integrations: List[str] = []
        if (os.getenv("SENTRY_DSN") or "").strip():
            integrations.append("sentry")
        if (os.getenv("DATADOG_API_KEY") or "").strip():
            integrations.append("datadog")

        # Aggregate events from logs and validation
        events: List[Dict] = []
        ts = datetime.utcnow().isoformat() + "Z"
        for log in logs:
            lvl = (log.get("level") or "").lower()
            if lvl in ("error", "warning"):
                events.append({
                    "source": "workflow",
                    "severity": lvl,
                    "category": "workflow",
                    "message": log.get("message", ""),
                    "timestamp": log.get("timestamp") or ts,
                })
        v_status = (validation or {}).get("overall_status")
        if v_status == "failed":
            events.append({
                "source": "validator",
                "severity": "error",
                "category": "build_validation",
                "message": validation.get("summary") or "Build validation failed",
                "timestamp": ts,
            })

        # Derive QA hints from events
        qa_hints: List[Dict] = []
        for ev in events:
            if ev["severity"] == "error":
                qa_hints.append({
                    "type": "test_suggestion",
                    "area": ev.get("category", "general"),
                    "description": f"Generate tests to reproduce: {ev.get('message','')}",
                })

        # Simple recommendations
        recommendations: List[str] = []
        if events:
            recommendations.append("run_resolver")
        if qa_hints:
            recommendations.append("generate_and_run_tests")
        if integrations:
            recommendations.append("wire_external_monitoring")

        output = {
            "integrations": integrations,
            "events": events,
            "qa_hints": qa_hints,
            "recommendations": recommendations,
        }

        context.add_telemetry("monitoring_summary", {"events": len(events), "hints": len(qa_hints)})
        return ExecutionResult(status=AgentStatus.COMPLETED, output=output)
