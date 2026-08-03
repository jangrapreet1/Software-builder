"""
Enhanced App Builder Workflow - Integrates all robustness improvements
Uses state management, validation, error feedback, and metrics
"""
import os
import json
import uuid
from typing import TypedDict, Annotated, Sequence, Optional, Dict, Any
from datetime import datetime
import operator
import asyncio
from pathlib import Path
import time

from langchain_google_genai import ChatGoogleGenerativeAI

from agents.coordinator_agent import CoordinatorAgent
from agents.frontend_agent import FrontendAgent
from agents.backend_agent import BackendAgent
from agents.integration_agent import IntegrationAgent
from agents.problem_resolver_agent import ProblemResolverAgent
from agents.tester_agent import TesterAgent
from agents.dependency_agent import DependencyAgent
from agents.base_agent import ExecutionContext
from services.preflight_validator import PreflightValidator
from agents.supervisor_orchestrator import SupervisorOrchestrator
from agents.quality_agent import QualityAgent
from agents.monitoring_agent import MonitoringAgent
from config.settings import Settings
from services.enhanced_state_manager import EnhancedStateManager
from services.build_validator import BuildValidator
from services.error_feedback_system import ErrorFeedbackSystem
from services.metrics_collector import get_metrics_collector
from services.activity_notifier import publish as publish_activity
from services.learning_engine import get_learning_engine
from services.persistent_build_storage import get_build_storage


class AppBuilderState(TypedDict):
    """Enhanced state schema with all fields"""
    build_id: str
    brief: str
    project_name: str
    requirements: list[str]
    
    # Planning phase
    features: list[dict]
    entities: list[dict]
    user_flows: list[dict]
    technical_specs: dict
    
    # Development phase
    backend_tasks: list[dict]
    frontend_tasks: list[dict]
    backend_code: dict
    frontend_code: dict
    
    # Integration phase
    integrated_code: dict
    docker_config: dict
    
    # Validation and resolution
    validation_results: dict
    resolution_results: list[dict]
    test_results: dict
    issues_resolved: int
    
    # Status tracking
    build_status: str
    logs: Annotated[list[dict], operator.add]
    current_step: str
    progress: int
    errors: list[str]
    warnings: list[str]
    
    # Output
    app_url: str
    source_path: str


class EnhancedAppBuilderWorkflow:
    """
    Enhanced workflow with:
    - Persistent state management
    - Comprehensive validation
    - Error feedback loops
    - Metrics collection
    - Robust error handling
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Initialize services
        repo_root = Path(settings.generated_apps_dir).resolve().parent
        # Prefer explicit override, then LocalAppData, finally repo-local
        env_dir = os.getenv("SB_STATE_DIR")
        if env_dir and env_dir.strip():
            artifacts_dir = Path(env_dir)
        else:
            localapp = os.getenv("LOCALAPPDATA", "").strip()
            if localapp:
                artifacts_dir = Path(localapp) / "SoftwareBuilder" / ".sb_artifacts"
            else:
                artifacts_dir = repo_root / ".sb_artifacts"
        self.state_manager = EnhancedStateManager(artifacts_dir)
        self.error_feedback = ErrorFeedbackSystem(artifacts_dir / "error_feedback")
        self.metrics = get_metrics_collector()
        self.storage = get_build_storage()
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            temperature=0.7,
            google_api_key=settings.google_api_key
        )
        
        # Initialize agents
        self.coordinator = CoordinatorAgent(self.llm, settings)
        self.backend_agent = BackendAgent(self.llm, settings)
        self.frontend_agent = FrontendAgent(self.llm, settings)
        self.integration_agent = IntegrationAgent(self.llm, settings)
        self.problem_resolver = ProblemResolverAgent(self.llm, settings)
        self.tester_agent = TesterAgent(self.llm, settings)
        self.dependency_agent = DependencyAgent(self.llm, settings)
        self.supervisor = SupervisorOrchestrator()
        self.quality_agent = QualityAgent(self.llm, settings)
        self.monitoring_agent = MonitoringAgent(self.llm, settings)
        
        print(f"[Enhanced Workflow] Initialized with state manager at {artifacts_dir}")
    
    async def build_from_brief(
        self,
        description: str,
        name: str = None,
        requirements: list[str] = None,
        enable_auto_resolution: bool = True,
        run_tests: bool = False
    ) -> dict:
        """
        Build application with enhanced robustness
        
        Features:
        - Persistent state with crash recovery
        - Comprehensive validation at each step
        - Error feedback to planning
        - Metrics collection
        - Automatic problem resolution
        """
        # Validate input
        if not description or not description.strip():
            raise ValueError("Project description cannot be empty")
        
        if len(description.strip()) < 10:
            raise ValueError("Project description is too short. Please provide more details.")
        
        build_id = str(uuid.uuid4())
        project_name = name or self._generate_project_name(description)
        
        # Start metrics tracking
        self.metrics.increment_counter("builds.total")
        # Ensure correct arithmetic with default 0
        self.metrics.set_gauge("builds.active", (self.metrics.get_gauge("builds.active") or 0) + 1)
        build_start_time = time.time()
        
        # Get error feedback for planning
        feedback = self.error_feedback.get_feedback_for_planning()
        
        # Initialize state
        initial_state = self._create_initial_state(
            build_id, description, project_name, requirements or []
        )
        
        # Save initial state
        self.state_manager.save_state(build_id, initial_state)
        # Persist initial record
        try:
            self.storage.save_build(build_id, self._build_record(build_id, initial_state))
        except Exception:
            pass
        
        try:
            # Execute workflow with state persistence
            final_state = await self._execute_workflow(
                build_id,
                initial_state,
                enable_auto_resolution,
                run_tests,
                feedback
            )
            
            # Mark as successful
            final_state["build_status"] = "success"
            final_state["progress"] = 100
            final_state["current_step"] = "Complete"
            
            # Save final state
            self.state_manager.save_state(build_id, final_state)
            # Compute duration before persisting metrics
            build_duration = time.time() - build_start_time
            # Persist final record and metrics
            try:
                self.storage.save_build(build_id, self._build_record(build_id, final_state))
                self.storage.save_metrics(build_id, self._compute_metrics(final_state, build_duration))
            except Exception:
                pass
            
            # Update metrics
            self.metrics.increment_counter("builds.successful")
            self.metrics.record_duration("builds.duration", build_duration)
            
            return {
                "status": "success",
                "build_id": build_id,
                "message": "Application built successfully with enhanced validation",
                "source_path": final_state.get("source_path"),
                "app_url": final_state.get("app_url"),
                "validation_score": final_state.get("validation_results", {}).get("score", 0),
                "issues_resolved": final_state.get("issues_resolved", 0),
                "build_duration": build_duration,
                "logs": final_state.get("logs", [])
            }
            
        except Exception as e:
            # Handle failure with state persistence
            error_msg = f"Build failed: {str(e)}"
            
            # Update state
            state = self.state_manager.get_state(build_id) or initial_state
            state["build_status"] = "failed"
            state["errors"].append(error_msg)
            state["current_step"] = "Failed"
            state["logs"].append({
                "level": "error",
                "message": error_msg,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            
            self.state_manager.save_state(build_id, state)
            # Compute duration before persisting metrics
            build_duration = time.time() - build_start_time
            try:
                self.storage.save_build(build_id, self._build_record(build_id, state))
                self.storage.add_log(build_id, "error", error_msg)
                self.storage.save_metrics(build_id, self._compute_metrics(state, build_duration))
            except Exception:
                pass
            
            # Update metrics
            self.metrics.increment_counter("builds.failed")
            self.metrics.record_duration("builds.duration", build_duration)
            
            # Record error in feedback system
            self.error_feedback.record_error(
                build_id=build_id,
                error_category="workflow_failure",
                error_message=str(e),
                context={"stage": state.get("current_step", "unknown")},
                resolution_attempted=False,
                resolution_successful=False
            )
            
            raise
        
        finally:
            # Update active builds gauge
            active = (self.metrics.get_gauge("builds.active") or 1) - 1
            self.metrics.set_gauge("builds.active", max(0, active))

    async def start_build_from_brief(
        self,
        description: str,
        name: str = None,
        requirements: list[str] = None,
        enable_auto_resolution: bool = True,
        run_tests: bool = False,
        preferred_backend: str | None = None,
        preferred_frontend: str | None = None,
    ) -> dict:
        """Start build asynchronously and return immediately with build_id.
        Saves initial state so progress can stream over WS while background task runs.
        """
        # Validate input
        if not description or not description.strip():
            raise ValueError("Project description cannot be empty")
        if len(description.strip()) < 10:
            raise ValueError("Project description is too short. Please provide more details.")

        build_id = str(uuid.uuid4())
        project_name = name or self._generate_project_name(description)

        # Metrics start
        self.metrics.increment_counter("builds.total")
        self.metrics.set_gauge("builds.active", (self.metrics.get_gauge("builds.active") or 0) + 1)
        build_start_time = time.time()

        # Planning feedback and initial state
        feedback = self.error_feedback.get_feedback_for_planning()
        initial_state = self._create_initial_state(
            build_id,
            description,
            project_name,
            requirements or [],
            preferred_backend,
            preferred_frontend,
        )
        self.state_manager.save_state(build_id, initial_state)

        # Fire background task
        async def _runner():
            await self._run_build(
                build_id=build_id,
                initial_state=initial_state,
                enable_auto_resolution=enable_auto_resolution,
                run_tests=run_tests,
                feedback=feedback,
                build_start_time=build_start_time,
            )

        asyncio.create_task(_runner())

        return {
            "status": "building",
            "build_id": build_id,
            "message": "Build started",
            "source_path": "",
            "app_url": "",
            "logs": initial_state.get("logs", [])
        }

    async def _run_build(
        self,
        build_id: str,
        initial_state: dict,
        enable_auto_resolution: bool,
        run_tests: bool,
        feedback: dict,
        build_start_time: float,
    ) -> None:
        """Internal helper to run the build in the background and persist status."""
        try:
            final_state = await self._execute_workflow(
                build_id,
                initial_state,
                enable_auto_resolution,
                run_tests,
                feedback,
            )

            final_state["build_status"] = "success"
            final_state["progress"] = 100
            final_state["current_step"] = "Complete"
            self.state_manager.save_state(build_id, final_state)
            build_duration = time.time() - build_start_time
            try:
                self.storage.save_build(build_id, self._build_record(build_id, final_state))
                self.storage.save_metrics(build_id, self._compute_metrics(final_state, build_duration))
            except Exception:
                pass

            self.metrics.increment_counter("builds.successful")
            self.metrics.record_duration("builds.duration", build_duration)
        except Exception as e:
            error_msg = f"Build failed: {str(e)}"
            state = self.state_manager.get_state(build_id) or initial_state
            state["build_status"] = "failed"
            state["errors"].append(error_msg)
            state["current_step"] = "Failed"
            state["logs"].append({
                "level": "error",
                "message": error_msg,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })
            self.state_manager.save_state(build_id, state)
            build_duration = time.time() - build_start_time
            try:
                self.storage.save_build(build_id, self._build_record(build_id, state))
                self.storage.add_log(build_id, "error", error_msg)
                self.storage.save_metrics(build_id, self._compute_metrics(state, build_duration))
            except Exception:
                pass

            self.metrics.increment_counter("builds.failed")
            self.metrics.record_duration("builds.duration", build_duration)

            self.error_feedback.record_error(
                build_id=build_id,
                error_category="workflow_failure",
                error_message=str(e),
                context={"stage": state.get("current_step", "unknown")},
                resolution_attempted=False,
                resolution_successful=False,
            )
        finally:
            active = (self.metrics.get_gauge("builds.active") or 1) - 1
            self.metrics.set_gauge("builds.active", max(0, active))
    
    async def _execute_workflow(
        self,
        build_id: str,
        state: dict,
        enable_resolution: bool,
        run_tests: bool,
        feedback: dict
    ) -> dict:
        """Execute complete workflow with checkpointing via Supervisor plan"""
        # Build a plan with flags
        flags = {"enable_resolution": enable_resolution, "run_tests": run_tests}
        plan = self.supervisor.plan({"goal": "build_application"}, flags)
        # Map plan steps to functions
        step_funcs = {
            "analyze_brief": lambda s: self._analyze_brief_enhanced(s, feedback),
            "generate_specs": self._generate_specs,
            "plan_tasks": self._plan_tasks,
            "generate_backend": self._generate_backend,
            "generate_frontend": self._generate_frontend,
            "integrate": self._integrate_code,
            "preflight": self._preflight_check,
            "validate": self._validate_build_comprehensive,
            "monitor": self._monitor_feedback,
            "resolve": self._resolve_problems,
            "test": self._run_tests,
        }
        # Build the concrete ordered list honoring flags
        ordered = [
            "analyze_brief", "generate_specs", "plan_tasks",
            "generate_backend", "generate_frontend", "integrate",
            "preflight", "validate", "monitor",
        ]
        if enable_resolution:
            ordered.append("resolve")
        if run_tests:
            ordered.append("test")

        for step in ordered:
            # Execute only if in supervisor plan
            if any(p.get("step") in (step, step.replace("_code", "")) for p in plan):
                # Conditional routing gate
                if not self.supervisor.should_execute(step, state, flags):
                    continue
                # HITL checkpoint (log only; auto-continue)
                if self.supervisor.requires_hitl(step, state):
                    self._log(state, "info", f"HITL checkpoint for {step}: continuing (auto-approve)")
                # Normalize names to our internal step labels
                label = step if step not in ("integrate", "validate", "resolve", "test") else (
                    "integrate_code" if step == "integrate" else
                    "validate_build" if step == "validate" else
                    "resolve_problems" if step == "resolve" else
                    "run_tests"
                )
                func = step_funcs[step]
                state = await self._checkpoint_step(build_id, state, label, func)
                # Mark completed in blackboard
                try:
                    self.supervisor.mark_completed(step)
                except Exception:
                    pass

        # Automatic repair loop: re-validate and attempt fixes if still failing
        state = await self._auto_repair_until_valid(build_id, state, flags, max_attempts=2)

        return state
    
    async def _checkpoint_step(
        self,
        build_id: str,
        state: dict,
        step_name: str,
        step_func
    ) -> dict:
        """Execute step with state checkpointing"""
        state["current_step"] = step_name
        self._log(state, "info", f"Starting step: {step_name}")
        try:
            self.storage.add_log(build_id, "info", f"Starting step: {step_name}")
            self.storage.save_build(build_id, self._build_record(build_id, state))
        except Exception:
            pass
        self._emit_activity(build_id, "workflow", step_name, f"start:{step_name}", "info", {})
        
        # Save state before step
        self.state_manager.save_state(build_id, state)
        
        step_start = time.time()
        
        try:
            # Execute step
            updated_state = await step_func(state)
            
            # Merge updates
            state.update(updated_state)
            
            # Record success
            step_duration = time.time() - step_start
            self.metrics.record_duration(f"workflow.step.{step_name}", step_duration)
            self._log(state, "success", f"Completed step: {step_name} ({step_duration:.2f}s)")
            try:
                self.storage.add_log(build_id, "success", f"Completed step: {step_name} ({round(step_duration,2)}s)")
                self.storage.save_build(build_id, self._build_record(build_id, state))
            except Exception:
                pass
            self._emit_activity(build_id, "workflow", step_name, f"complete:{step_name}", "success", {"duration": round(step_duration, 2)})
            
        except Exception as e:
            # Record failure
            step_duration = time.time() - step_start
            self.metrics.increment_counter(f"workflow.step.{step_name}.failures")
            
            error_msg = f"Step {step_name} failed: {str(e)}"
            self._log(state, "error", error_msg)
            state["errors"].append(error_msg)
            try:
                self.storage.add_log(build_id, "error", error_msg)
                self.storage.save_build(build_id, self._build_record(build_id, state))
            except Exception:
                pass
            self._emit_activity(build_id, "workflow", step_name, f"error:{step_name}", "error", {"error": str(e)})
            
            # Record in error feedback
            self.error_feedback.record_error(
                build_id=build_id,
                error_category="workflow_step_failure",
                error_message=error_msg,
                context={"step": step_name},
                resolution_attempted=False,
                resolution_successful=False
            )
            
            raise
        
        finally:
            # Save state after step
            self.state_manager.save_state(build_id, state)
            try:
                self.storage.save_build(build_id, self._build_record(build_id, state))
            except Exception:
                pass
        
        return state
    
    async def _analyze_brief_enhanced(self, state: dict, feedback: dict) -> dict:
        """Analyze brief with error feedback"""
        self._update_progress(state, 10)
        build_id = state["build_id"]
        self._emit_activity(build_id, "CoordinatorAgent", "analyze_brief", "Analyzing project brief requirements and domain entities...", "info")
        
        # Add feedback constraints if available
        brief = state["brief"]
        if feedback.get("has_feedback"):
            brief += "\n\nIMPORTANT CONSTRAINTS (based on historical issues):\n"
            for mod in feedback.get("constraint_modifications", []):
                brief += f"- {mod['description']}\n"
        
        result = await self.coordinator.analyze_brief(brief)
        self._emit_activity(
            build_id, 
            "CoordinatorAgent", 
            "analyze_brief", 
            f"Extracted {len(result.get('features', []))} features, {len(result.get('entities', []))} entities & {len(result.get('user_flows', []))} user flows", 
            "success",
            {"features": len(result.get("features", [])), "entities": len(result.get("entities", []))}
        )
        
        return {
            "features": result["features"],
            "entities": result["entities"],
            "user_flows": result["user_flows"],
            "progress": 20
        }
    
    async def _generate_specs(self, state: dict) -> dict:
        """Generate technical specifications"""
        self._update_progress(state, 25)
        build_id = state["build_id"]
        self._emit_activity(build_id, "CoordinatorAgent", "generate_specs", "Generating technical architecture specifications...", "info")
        
        specs = await self.coordinator.generate_technical_specs(
            state["features"],
            state["entities"],
            state["user_flows"]
        )
        # Learning-driven recommendations (best-effort, non-fatal)
        try:
            engine = get_learning_engine()
            recs = engine.get_build_recommendations(state.get("brief", ""), state.get("requirements", []))
            if recs:
                specs["learning_recommendations"] = recs
                if recs.get("best_practices"):
                    specs["best_practices"] = recs.get("best_practices")
        except Exception:
            pass
        # Thread user preferences into specs if provided
        pref_be = (state.get("preferred_backend") or "").strip()
        pref_fe = (state.get("preferred_frontend") or "").strip()
        if pref_be:
            try:
                specs["preferred_backend"] = pref_be
            except Exception:
                pass
        if pref_fe:
            try:
                specs["preferred_frontend"] = pref_fe
            except Exception:
                pass
        
        # Add preventive spec additions
        preventive_additions = self.error_feedback.generate_preventive_spec_additions()
        if preventive_additions:
            specs["preventive_measures"] = preventive_additions
            
        self._emit_activity(build_id, "CoordinatorAgent", "generate_specs", "Technical specifications generated with architecture patterns", "success")
        
        return {
            "technical_specs": specs,
            "progress": 30
        }
    
    async def _plan_tasks(self, state: dict) -> dict:
        """Plan development tasks"""
        self._update_progress(state, 35)
        build_id = state["build_id"]
        self._emit_activity(build_id, "CoordinatorAgent", "plan_tasks", "Planning granular backend and frontend implementation tasks...", "info")
        
        tasks = await self.coordinator.plan_tasks(state["technical_specs"])
        be_cnt = len(tasks.get("backend", []))
        fe_cnt = len(tasks.get("frontend", []))
        self._emit_activity(build_id, "CoordinatorAgent", "plan_tasks", f"Planned {be_cnt} backend tasks and {fe_cnt} frontend tasks", "success", {"backend_tasks": be_cnt, "frontend_tasks": fe_cnt})
        
        return {
            "backend_tasks": tasks["backend"],
            "frontend_tasks": tasks["frontend"],
            "progress": 40
        }
    
    async def _generate_backend(self, state: dict) -> dict:
        """Generate backend code"""
        self._update_progress(state, 45)
        build_id = state["build_id"]
        self._emit_activity(build_id, "BackendAgent", "generate_backend", "Generating backend models, controllers & API schemas...", "info")
        
        backend_code = await self.backend_agent.generate_code(
            state["backend_tasks"],
            state["entities"],
            state["technical_specs"]
        )
        self._emit_activity(build_id, "BackendAgent", "generate_backend", "Backend API services & database code generated", "success")
        
        return {
            "backend_code": backend_code,
            "progress": 55
        }
    
    async def _generate_frontend(self, state: dict) -> dict:
        """Generate frontend code"""
        self._update_progress(state, 60)
        build_id = state["build_id"]
        self._emit_activity(build_id, "FrontendAgent", "generate_frontend", "Generating React UI components, pages & state stores...", "info")
        
        frontend_code = await self.frontend_agent.generate_code(
            state["frontend_tasks"],
            state["user_flows"],
            state["technical_specs"],
            state["backend_code"]
        )
        self._emit_activity(build_id, "FrontendAgent", "generate_frontend", "React UI components & page routes generated", "success")
        
        return {
            "frontend_code": frontend_code,
            "progress": 70
        }
    
    async def _integrate_code(self, state: dict) -> dict:
        """Integrate frontend and backend"""
        self._update_progress(state, 75)
        build_id = state["build_id"]
        self._emit_activity(build_id, "IntegrationAgent", "integrate_code", "Structuring project files and Docker configuration...", "info")
        
        integration = await self.integration_agent.integrate(
            state["project_name"],
            state["backend_code"],
            state["frontend_code"],
            state["technical_specs"]
        )
        self._emit_activity(build_id, "IntegrationAgent", "integrate_code", f"Project files structured in {integration.get('path', '')}", "success")
        
        return {
            "integrated_code": integration["code"],
            "docker_config": integration["docker"],
            "source_path": integration["path"],
            "progress": 80
        }
    
    async def _validate_build_comprehensive(self, state: dict) -> dict:
        """Comprehensive build validation"""
        self._update_progress(state, 85)
        build_id = state["build_id"]
        self._emit_activity(build_id, "BuildValidator", "validate_build", "Running comprehensive build & structural quality validation...", "info")
        
        validator = BuildValidator()
        validation_results = await validator.validate_build(state["source_path"])
        
        # Log validation results
        score = validation_results.get("score", 0)
        status = validation_results.get("overall_status", "unknown")
        
        self._log(state, "info", f"Validation score: {score}/100 - Status: {status}")
        self._emit_activity(build_id, "BuildValidator", "validate_build", f"Quality Score: {score}/100 · Status: {status.upper()}", "success" if status == "passed" else "warning", {"score": score, "status": status})
        
        # Record metrics
        self.metrics.set_gauge("builds.last_validation_score", score)
        
        if status == "failed":
            self._log(state, "warning", f"Validation issues: {validation_results.get('summary')}")
        
        return {
            "validation_results": validation_results,
            "progress": 90
        }

    async def _preflight_check(self, state: dict) -> dict:
        self._update_progress(state, 82)
        build_id = state["build_id"]
        self._emit_activity(build_id, "PreflightValidator", "preflight", "Checking dependencies & preflight environment configuration...", "info")
        validator = PreflightValidator()
        results = await validator.validate(state["source_path"])
        state.setdefault("preflight_results", {})
        state["preflight_results"]["initial"] = results
        if results.get("overall") == "failed":
            self._emit_activity(build_id, "DependencyAgent", "preflight", "Preflight check flagged missing dependencies. Auto-repairing...", "warning")
            ctx = ExecutionContext(
                build_id=state["build_id"],
                request_data={"project_path": state["source_path"]},
                shared_state=state
            )
            dep_result = await self.dependency_agent.execute_safe(ctx)
            state["preflight_results"]["dependency_fixes"] = dep_result.to_dict()
            results2 = await validator.validate(state["source_path"])
            state["preflight_results"]["after_fixes"] = results2
            self.metrics.increment_counter("preflight.issues", len(results.get("issues", [])))
            self._emit_activity(build_id, "DependencyAgent", "preflight", "Dependency auto-repair complete", "success")
        else:
            self.metrics.increment_counter("preflight.passed")
            self._emit_activity(build_id, "PreflightValidator", "preflight", "Preflight checks passed", "success")
        return {"progress": 84}

    async def _monitor_feedback(self, state: dict) -> dict:
        """Pull monitoring signals and attach to state (stub integration)."""
        # Place after validation; lightweight progress bump
        self._update_progress(state, max(90, state.get("progress", 0)))
        ctx = ExecutionContext(
            build_id=state["build_id"],
            request_data={"project_path": state.get("source_path", ""), "mode": "pull-events"},
            shared_state=state,
        )
        mon_result = await self.monitoring_agent.execute_safe(ctx)
        output = mon_result.to_dict()
        events = (output.get("output") or {}).get("events", [])
        state.setdefault("monitoring", {})
        state["monitoring"]["events"] = events
        # Metric
        try:
            self.metrics.increment_counter("monitoring.events", len(events))
        except Exception:
            pass
        return {"progress": max(91, state.get("progress", 0))}
    
    async def _resolve_problems(self, state: dict) -> dict:
        """Auto-resolve problems with error feedback"""
        self._update_progress(state, 92)
        build_id = state["build_id"]
        self._emit_activity(build_id, "ProblemResolverAgent", "resolve_problems", "Diagnosing logs & attempting automated code repairs...", "info")
        
        # Collect error logs
        error_logs = "\n".join([
            log["message"] for log in state.get("logs", [])
            if log.get("level") == "error"
        ])
        
        # Run problem resolver
        resolution = await self.problem_resolver.analyze_and_resolve(
            app_path=state["source_path"],
            error_logs=error_logs,
            context={"build_id": state["build_id"]}
        )
        repairs_cnt = len(resolution.get("resolution_log", []))
        self._emit_activity(build_id, "ProblemResolverAgent", "resolve_problems", f"Problem Resolver completed with {repairs_cnt} repairs applied", "success" if repairs_cnt > 0 else "info")
        
        # Record in error feedback system
        for issue in resolution.get("resolution_log", []):
            self.error_feedback.record_error(
                build_id=state["build_id"],
                error_category=issue.get("category", "unknown"),
                error_message=issue.get("issue", ""),
                context={"resolution_action": issue.get("action")},
                resolution_attempted=True,
                resolution_successful=issue.get("success", False)
            )
            
            if issue.get("success"):
                self.error_feedback.record_resolution(
                    build_id=state["build_id"],
                    error_category=issue.get("category", "unknown"),
                    error_message=issue.get("issue", ""),
                    fix_applied=issue.get("action", ""),
                    successful=True
                )
        
        # Update metrics
        self.metrics.increment_counter(
            "resolver.issues.detected",
            resolution.get("issues_found", 0)
        )
        self.metrics.increment_counter(
            "resolver.issues.resolved",
            resolution.get("issues_resolved", 0)
        )
        
        self._log(state, "info", 
            f"Resolved {resolution.get('issues_resolved', 0)}/{resolution.get('issues_found', 0)} issues")
        
        return {
            "resolution_results": [resolution],
            "issues_resolved": resolution.get("issues_resolved", 0),
            "progress": 95
        }
    
    async def _run_tests(self, state: dict) -> dict:
        """Run tests"""
        self._update_progress(state, 97)
        
        # Use consolidated QualityAgent
        ctx = ExecutionContext(
            build_id=state["build_id"],
            request_data={
                "project_path": state["source_path"],
                "entities": state.get("entities", []),
                "backend_framework": (state.get("preferred_backend") or "fastapi"),
                "frontend_framework": (state.get("preferred_frontend") or "react-vite"),
            },
            shared_state=state,
        )
        qa_result = await self.quality_agent.execute_safe(ctx)
        output = qa_result.to_dict()
        report = (output.get("output") or {}).get("test_report", {})
        summary = report.get("summary", {})
        
        # Update metrics
        self.metrics.increment_counter("tester.runs.total")
        self.metrics.increment_counter("tester.tests.passed", summary.get("passed", 0))
        self.metrics.increment_counter("tester.tests.failed", summary.get("failed", 0))
        
        self._log(state, "info",
            f"Tests: {summary.get('passed', 0)} passed, {summary.get('failed', 0)} failed")
        
        return {
            "quality_results": output,
            "test_results": report,
            "progress": 99
        }

    async def _auto_repair_until_valid(self, build_id: str, state: dict, flags: dict, max_attempts: int = 2) -> dict:
        """Iteratively validate -> preflight(dep fixes) -> resolve until validation passes or attempts exhausted."""
        try:
            attempts = max(0, int(max_attempts))
        except Exception:
            attempts = 2
        for i in range(attempts):
            # Validate
            state = await self._checkpoint_step(build_id, state, "validate_build", self._validate_build_comprehensive)
            status = (state.get("validation_results", {}) or {}).get("overall_status", "unknown")
            if status != "failed":
                break
            # Preflight + dependency fixes
            state = await self._checkpoint_step(build_id, state, "preflight", self._preflight_check)
            # Resolve problems if allowed
            if self.supervisor.should_execute("resolve", state, flags):
                if self.supervisor.requires_hitl("resolve", state):
                    self._log(state, "info", "HITL checkpoint for resolve: continuing (auto-approve)")
                state = await self._checkpoint_step(build_id, state, "resolve_problems", self._resolve_problems)
        return state
    
    def _create_initial_state(
        self,
        build_id: str,
        brief: str,
        project_name: str,
        requirements: list[str],
        preferred_backend: str | None = None,
        preferred_frontend: str | None = None,
    ) -> dict:
        """Create initial workflow state"""
        return {
            "build_id": build_id,
            "brief": brief,
            "project_name": project_name,
            "requirements": requirements,
            "features": [],
            "entities": [],
            "user_flows": [],
            "technical_specs": {},
            "backend_tasks": [],
            "frontend_tasks": [],
            "backend_code": {},
            "frontend_code": {},
            "integrated_code": {},
            "docker_config": {},
            "validation_results": {},
            "resolution_results": [],
            "test_results": {},
            "issues_resolved": 0,
            "build_status": "building",
            "logs": [],
            "current_step": "Initializing",
            "progress": 0,
            "errors": [],
            "warnings": [],
            "app_url": "",
            "source_path": "",
            "agent_activity": [],
            "preferred_backend": preferred_backend or "",
            "preferred_frontend": preferred_frontend or ""
        }
    
    def _generate_project_name(self, description: str) -> str:
        """Generate project name from description"""
        words = description.lower().split()[:3]
        return "-".join(words).replace(",", "").replace(".", "")
    
    def _update_progress(self, state: dict, progress: int):
        """Update progress"""
        state["progress"] = progress
    
    def _log(self, state: dict, level: str, message: str):
        """Add log entry"""
        state["logs"].append({
            "level": level,
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

    def _build_record(self, build_id: str, state: dict) -> dict:
        """Normalize state to storage build record"""
        try:
            return {
                "build_id": build_id,
                "project_name": state.get("project_name", ""),
                "brief": state.get("brief", ""),
                "build_status": state.get("build_status", "building"),
                "progress": state.get("progress", 0),
                "current_step": state.get("current_step", ""),
                "app_url": state.get("app_url", ""),
                "source_path": state.get("source_path", ""),
                "build_data": state,
            }
        except Exception:
            return {"build_id": build_id, "project_name": state.get("project_name", ""), "build_status": state.get("build_status", "building"), "progress": state.get("progress", 0), "current_step": state.get("current_step", "")}

    def _compute_metrics(self, state: dict, duration: float) -> dict:
        """Compute lightweight metrics for storage"""
        try:
            entity_count = len(state.get("entities", []) or [])
            file_count = 0
            try:
                file_count += len((state.get("backend_code") or {}).keys())
            except Exception:
                pass
            try:
                file_count += len((state.get("frontend_code") or {}).keys())
            except Exception:
                pass
            validation = state.get("validation_results", {}) or {}
            val_score = validation.get("score", 0)
            coverage = 0
            tr = state.get("test_results", {}) or {}
            summary = tr.get("summary", {}) if isinstance(tr, dict) else {}
            coverage = summary.get("coverage", 0) if isinstance(summary, dict) else 0
            return {
                "duration_seconds": float(duration or 0),
                "entity_count": int(entity_count or 0),
                "file_count": int(file_count or 0),
                "validation_score": int(val_score or 0),
                "test_coverage": int(coverage or 0),
            }
        except Exception:
            return {"duration_seconds": float(duration or 0)}

    def _emit_activity(self, build_id: str, agent: str, stage: str, message: str, level: str = "info", metadata: dict | None = None):
        evt = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent": agent,
            "stage": stage,
            "message": message,
            "level": level,
            "metadata": metadata or {}
        }
        state = self.state_manager.get_state(build_id) or {}
        if isinstance(state.get("agent_activity"), list):
            state["agent_activity"].append(evt)
        else:
            state["agent_activity"] = [evt]
        self.state_manager.save_state(build_id, state)
        try:
            publish_activity(build_id, evt)
        except Exception:
            pass
    
    async def get_build_status(self, build_id: str) -> Optional[dict]:
        """Get build status from persistent state"""
        state = self.state_manager.get_state(build_id)
        
        if not state:
            return None
        
        return {
            "build_id": build_id,
            "status": state.get("build_status", "unknown"),
            "progress": state.get("progress", 0),
            "current_step": state.get("current_step", ""),
            "logs": state.get("logs", []),
            "source_path": state.get("source_path")
        }
    
    async def list_builds(self) -> list[dict]:
        """List all builds from persistent storage"""
        return self.state_manager.list_all_states()
    
    async def delete_build(self, build_id: str) -> dict:
        """Delete a build"""
        success = self.state_manager.delete_state(build_id)
        self.error_feedback.clear_build_errors(build_id)
        
        return {
            "success": success,
            "message": "Build deleted" if success else "Build not found"
        }
    
    async def recover_build(self, build_id: str) -> Optional[dict]:
        """Recover build from backup"""
        state = self.state_manager.recover_state(build_id)
        
        if state:
            return {
                "success": True,
                "message": "Build recovered from backup",
                "state": state
            }
        
        return None
    
    def get_metrics_summary(self) -> dict:
        """Get metrics summary"""
        return self.metrics.get_performance_report()
    
    def get_error_analytics(self) -> dict:
        """Get error analytics"""
        return self.error_feedback.export_analytics()
