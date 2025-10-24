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
from config.settings import Settings
from services.enhanced_state_manager import EnhancedStateManager
from services.build_validator import BuildValidator
from services.error_feedback_system import ErrorFeedbackSystem
from services.metrics_collector import get_metrics_collector
from services.activity_notifier import publish as publish_activity


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
        self.metrics.set_gauge("builds.active", self.metrics.get_gauge("builds.active") or 0 + 1)
        build_start_time = time.time()
        
        # Get error feedback for planning
        feedback = self.error_feedback.get_feedback_for_planning()
        
        # Initialize state
        initial_state = self._create_initial_state(
            build_id, description, project_name, requirements or []
        )
        
        # Save initial state
        self.state_manager.save_state(build_id, initial_state)
        
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
            
            # Update metrics
            build_duration = time.time() - build_start_time
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
            
            # Update metrics
            build_duration = time.time() - build_start_time
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
        """Execute complete workflow with checkpointing"""
        
        # Step 1: Analyze brief with feedback
        state = await self._checkpoint_step(
            build_id, state, "analyze_brief",
            lambda s: self._analyze_brief_enhanced(s, feedback)
        )
        
        # Step 2: Generate specifications
        state = await self._checkpoint_step(
            build_id, state, "generate_specs",
            self._generate_specs
        )
        
        # Step 3: Plan tasks
        state = await self._checkpoint_step(
            build_id, state, "plan_tasks",
            self._plan_tasks
        )
        
        # Step 4: Generate backend
        state = await self._checkpoint_step(
            build_id, state, "generate_backend",
            self._generate_backend
        )
        
        # Step 5: Generate frontend
        state = await self._checkpoint_step(
            build_id, state, "generate_frontend",
            self._generate_frontend
        )
        
        # Step 6: Integrate code
        state = await self._checkpoint_step(
            build_id, state, "integrate_code",
            self._integrate_code
        )
        
        # Step 7: Comprehensive validation
        state = await self._checkpoint_step(
            build_id, state, "validate_build",
            self._validate_build_comprehensive
        )
        
        # Step 8: Auto-resolve problems if enabled
        if enable_resolution:
            state = await self._checkpoint_step(
                build_id, state, "resolve_problems",
                self._resolve_problems
            )
        
        # Step 9: Run tests if requested
        if run_tests:
            state = await self._checkpoint_step(
                build_id, state, "run_tests",
                self._run_tests
            )
        
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
            self._emit_activity(build_id, "workflow", step_name, f"complete:{step_name}", "success", {"duration": round(step_duration, 2)})
            
        except Exception as e:
            # Record failure
            step_duration = time.time() - step_start
            self.metrics.increment_counter(f"workflow.step.{step_name}.failures")
            
            error_msg = f"Step {step_name} failed: {str(e)}"
            self._log(state, "error", error_msg)
            state["errors"].append(error_msg)
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
        
        return state
    
    async def _analyze_brief_enhanced(self, state: dict, feedback: dict) -> dict:
        """Analyze brief with error feedback"""
        self._update_progress(state, 10)
        
        # Add feedback constraints if available
        brief = state["brief"]
        if feedback.get("has_feedback"):
            brief += "\n\nIMPORTANT CONSTRAINTS (based on historical issues):\n"
            for mod in feedback.get("constraint_modifications", []):
                brief += f"- {mod['description']}\n"
        
        result = await self.coordinator.analyze_brief(brief)
        
        return {
            "features": result["features"],
            "entities": result["entities"],
            "user_flows": result["user_flows"],
            "progress": 20
        }
    
    async def _generate_specs(self, state: dict) -> dict:
        """Generate technical specifications"""
        self._update_progress(state, 25)
        
        specs = await self.coordinator.generate_technical_specs(
            state["features"],
            state["entities"],
            state["user_flows"]
        )
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
        
        return {
            "technical_specs": specs,
            "progress": 30
        }
    
    async def _plan_tasks(self, state: dict) -> dict:
        """Plan development tasks"""
        self._update_progress(state, 35)
        
        tasks = await self.coordinator.plan_tasks(state["technical_specs"])
        
        return {
            "backend_tasks": tasks["backend"],
            "frontend_tasks": tasks["frontend"],
            "progress": 40
        }
    
    async def _generate_backend(self, state: dict) -> dict:
        """Generate backend code"""
        self._update_progress(state, 45)
        
        backend_code = await self.backend_agent.generate_code(
            state["backend_tasks"],
            state["entities"],
            state["technical_specs"]
        )
        
        return {
            "backend_code": backend_code,
            "progress": 55
        }
    
    async def _generate_frontend(self, state: dict) -> dict:
        """Generate frontend code"""
        self._update_progress(state, 60)
        
        frontend_code = await self.frontend_agent.generate_code(
            state["frontend_tasks"],
            state["user_flows"],
            state["technical_specs"],
            state["backend_code"]
        )
        
        return {
            "frontend_code": frontend_code,
            "progress": 70
        }
    
    async def _integrate_code(self, state: dict) -> dict:
        """Integrate frontend and backend"""
        self._update_progress(state, 75)
        
        integration = await self.integration_agent.integrate(
            state["project_name"],
            state["backend_code"],
            state["frontend_code"],
            state["technical_specs"]
        )
        
        return {
            "integrated_code": integration["code"],
            "docker_config": integration["docker"],
            "source_path": integration["path"],
            "progress": 80
        }
    
    async def _validate_build_comprehensive(self, state: dict) -> dict:
        """Comprehensive build validation"""
        self._update_progress(state, 85)
        
        validator = BuildValidator()
        validation_results = await validator.validate_build(state["source_path"])
        
        # Log validation results
        score = validation_results.get("score", 0)
        status = validation_results.get("overall_status", "unknown")
        
        self._log(state, "info", f"Validation score: {score}/100 - Status: {status}")
        
        # Record metrics
        self.metrics.set_gauge("builds.last_validation_score", score)
        
        if status == "failed":
            self._log(state, "warning", f"Validation issues: {validation_results.get('summary')}")
        
        return {
            "validation_results": validation_results,
            "progress": 90
        }
    
    async def _resolve_problems(self, state: dict) -> dict:
        """Auto-resolve problems with error feedback"""
        self._update_progress(state, 92)
        
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
        
        test_results = await self.tester_agent.run_tests(
            app_path=state["source_path"],
            test_type="all",
            generate_missing=True
        )
        
        # Update metrics
        summary = test_results.get("summary", {})
        self.metrics.increment_counter("tester.runs.total")
        self.metrics.increment_counter("tester.tests.passed", summary.get("passed", 0))
        self.metrics.increment_counter("tester.tests.failed", summary.get("failed", 0))
        
        self._log(state, "info",
            f"Tests: {summary.get('passed', 0)} passed, {summary.get('failed', 0)} failed")
        
        return {
            "test_results": test_results,
            "progress": 99
        }
    
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
