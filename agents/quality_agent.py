"""
Quality Agent - consolidates test generation and execution.
Generates tests (proposal) and runs tests, returning a single cohesive result.
"""
from __future__ import annotations
from typing import Dict, Optional, List
from pathlib import Path
from .base_agent import BaseAgent, ExecutionContext, ExecutionResult, AgentStatus, AgentCapability
from .comprehensive_test_generator import ComprehensiveTestGenerator
from .tester_agent import TesterAgent


class QualityAgent(BaseAgent):
    def __init__(self, llm, settings):
        super().__init__(llm, settings)
        self._generator = ComprehensiveTestGenerator(llm, settings)
        self._tester = TesterAgent(llm, settings)

    def get_capabilities(self) -> List[AgentCapability]:
        return [AgentCapability.TESTING, AgentCapability.CODE_ANALYSIS]

    def validate_input(self, request_data: Dict) -> tuple[bool, Optional[str]]:
        if "project_path" not in request_data:
            return False, "project_path is required"
        return True, None

    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        project_path = context.request_data["project_path"]
        entities = context.request_data.get("entities", [])
        backend_framework = context.request_data.get("backend_framework", "fastapi")
        frontend_framework = context.request_data.get("frontend_framework", "react-vite")

        # Step 1: Propose/generate tests (does not write to disk here)
        gen_ctx = ExecutionContext(
            build_id=context.build_id,
            request_data={
                "project_path": project_path,
                "entities": entities,
                "backend_framework": backend_framework,
                "frontend_framework": frontend_framework,
            },
            shared_state=context.shared_state,
        )
        gen_result = await self._generator.execute_safe(gen_ctx)
        context.add_telemetry("quality_agent.generated_tests", {"files": len(gen_result.output.get("tests", {}))})

        # Step 2: Run unit and integration tests (with auto-generate-missing enabled by TesterAgent)
        test_report = await self._tester.run_tests(
            app_path=project_path,
            test_type="all",
            generate_missing=True,
        )
        context.add_telemetry("quality_agent.ran_tests", {"summary": test_report.get("summary", {})})

        # Step 3: Run Playwright E2E tests if a frontend framework is requested
        e2e_report = None
        has_frontend = (Path(project_path) / "frontend").exists() or (Path(project_path) / "package.json").exists()
        if has_frontend:
            e2e_report = await self._tester.run_tests(
                app_path=project_path,
                test_type="e2e",
                generate_missing=True,
            )
            context.add_telemetry("quality_agent.ran_e2e_tests", {"summary": e2e_report.get("summary", {})})

        output = {
            "proposed_tests": gen_result.output,
            "test_report": test_report,
            "e2e_report": e2e_report
        }

        # Overall validation status depends on both reports
        status = AgentStatus.COMPLETED
        if test_report.get("status") == "error" or (e2e_report and e2e_report.get("status") == "error"):
            status = AgentStatus.FAILED

        return ExecutionResult(
            status=status,
            output=output,
            metadata={
                "proposed_test_files": len(gen_result.output.get("tests", {})),
                "entities": len(entities),
                "has_e2e_tests": e2e_report is not None
            }
        )
