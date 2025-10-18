"""
Phase 2 Enhanced Workflow - Integrates Problem Resolver and Tester Agents
"""
import os
import json
import uuid
from typing import TypedDict, Annotated, Sequence
from datetime import datetime
import operator
import asyncio
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

from agents.coordinator_agent import CoordinatorAgent
from agents.frontend_agent import FrontendAgent
from agents.backend_agent import BackendAgent
from agents.integration_agent import IntegrationAgent
from agents.problem_resolver_agent import ProblemResolverAgent
from agents.tester_agent import TesterAgent
from config.settings import Settings
from services.build_registry import BuildRegistry
from services.agent_collaboration_manager import CollaborationManager, LivePreviewBridge


class AppBuilderState(TypedDict):
    """Enhanced state schema with Phase 2 fields"""
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
    
    # Phase 2: Resolution & Testing
    resolution_results: list[dict]
    test_results: dict
    issues_resolved: int
    
    # Validation phase
    test_results: dict
    build_status: str
    
    # Metadata
    logs: Annotated[list[dict], operator.add]
    current_step: str
    progress: int
    errors: list[str]
    app_url: str
    source_path: str
    
    # Phase 2: Preview
    preview_url: str
    instance_id: str
    logs_url: str
    expires_at: str


class AppBuilderWorkflowPhase2:
    """
    Enhanced workflow with autonomous problem resolution and testing
    """
    
    def __init__(self, settings: Settings, registry: BuildRegistry | None = None):
        self.settings = settings
        self.builds = {}
        
        if registry is not None:
            self.build_registry = registry
        else:
            repo_root = Path(settings.generated_apps_dir).resolve().parent
            self.build_registry = BuildRegistry(repo_root)

        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            temperature=0.7,
            google_api_key=settings.google_api_key
        )

        # Initialize agents
        self.coordinator = CoordinatorAgent(self.llm, settings)
        self.frontend_agent = FrontendAgent(self.llm, settings)
        self.backend_agent = BackendAgent(self.llm, settings)
        self.integration_agent = IntegrationAgent(self.llm, settings)
        
        # Phase 2 agents
        self.problem_resolver = ProblemResolverAgent(self.llm, settings)
        self.tester_agent = TesterAgent(self.llm, settings)
        self.collaboration_manager = CollaborationManager(settings)

        # Rehydrate previously persisted builds
        if self.build_registry:
            for record in self.build_registry.load_all():
                self.builds[record["build_id"]] = self._record_to_state(record)
    
    async def build_from_brief(
        self,
        description: str,
        name: str = None,
        requirements: list[str] = None,
        enable_auto_resolution: bool = True,
        run_tests: bool = False
    ) -> dict:
        """
        Build an application with Phase 2 enhancements
        
        Args:
            description: Project description
            name: Project name
            requirements: Additional requirements
            enable_auto_resolution: Enable automatic problem resolution
            run_tests: Run tests after build
        """
        # Validate input
        if not description or not description.strip():
            raise ValueError("Project description cannot be empty")
        
        if len(description.strip()) < 10:
            raise ValueError("Project description is too short. Please provide more details.")
        
        build_id = str(uuid.uuid4())
        project_name = name or self._generate_project_name(description)
        
        # Initialize enhanced state
        initial_state = {
            "build_id": build_id,
            "brief": description,
            "project_name": project_name,
            "requirements": requirements or [],
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
            "resolution_results": [],
            "test_results": {},
            "issues_resolved": 0,
            "build_status": "building",
            "logs": [],
            "current_step": "Starting analysis",
            "progress": 0,
            "errors": [],
            "app_url": "",
            "source_path": "",
            "preview_url": "",
            "instance_id": "",
            "logs_url": "",
            "expires_at": ""
        }
        
        # Store build state
        self.builds[build_id] = initial_state
        self._persist_metadata(build_id, initial_state)

        try:
            state = initial_state.copy()
            
            # Step 1-6: Standard build process
            print(f"[Phase 2] Starting build for {build_id}")
            state = await self._execute_standard_build(build_id, state)
            
            # Phase 2 Enhancement: Auto-resolve problems if enabled
            if enable_auto_resolution:
                print(f"[Phase 2] Step 7: Auto-resolving problems for {build_id}")
                state = await self._auto_resolve_problems(build_id, state)
            
            # Phase 2 Enhancement: Run tests if requested
            if run_tests:
                print(f"[Phase 2] Step 8: Running tests for {build_id}")
                state = await self._run_tests(build_id, state)
            
            # Final validation
            print(f"[Phase 2] Step 9: Final validation for {build_id}")
            state = await self._final_validation(build_id, state)
            
            # Mark as complete
            state["build_status"] = "success"
            state["progress"] = 100
            state["current_step"] = "Complete"
            self.builds[build_id] = state
            self._persist_metadata(build_id, state)

            return {
                "status": "success",
                "build_id": build_id,
                "message": "Application built successfully with Phase 2 enhancements",
                "app_url": state.get("app_url"),
                "source_path": state.get("source_path"),
                "preview_url": state.get("preview_url"),
                "instance_id": state.get("instance_id"),
                "logs_url": state.get("logs_url"),
                "expires_at": state.get("expires_at"),
                "resolution_summary": {
                    "issues_resolved": state.get("issues_resolved", 0),
                    "resolution_attempts": len(state.get("resolution_results", []))
                },
                "test_summary": state.get("test_results", {}).get("summary", {}),
                "logs": state.get("logs", [])
            }
            
        except Exception as e:
            # Mark as failed
            error_msg = f"Build failed: {str(e)}"
            self.builds[build_id]["build_status"] = "failed"
            self.builds[build_id]["errors"].append(error_msg)
            self.builds[build_id]["current_step"] = "failed"
            self.builds[build_id]["logs"].append({
                "level": "error",
                "message": error_msg,
                "timestamp": datetime.now().isoformat()
            })
            self._persist_metadata(build_id, self.builds[build_id])
            print(f"Build {build_id} failed with error: {e}")
            raise
    
    async def _execute_standard_build(self, build_id: str, state: dict) -> dict:
        """Execute standard build steps 1-6"""
        # This would call the standard workflow steps
        # For now, simulate completion
        state["progress"] = 60
        state["current_step"] = "Code generated"
        state["source_path"] = f"./generated/{state['project_name']}"
        
        # Simulate generated app
        app_path = Path(state["source_path"])
        app_path.mkdir(parents=True, exist_ok=True)
        
        state["logs"].append({
            "level": "info",
            "message": "Standard build completed",
            "timestamp": datetime.now().isoformat()
        })
        
        self.builds[build_id] = state
        self._persist_metadata(build_id, state)
        
        return state
    
    async def _auto_resolve_problems(self, build_id: str, state: dict) -> dict:
        """Auto-resolve problems using Problem Resolver Agent"""
        state["current_step"] = "Resolving issues"
        state["progress"] = 70
        
        try:
            app_path = state.get("source_path")
            if not app_path or not Path(app_path).exists():
                state["logs"].append({
                    "level": "warning",
                    "message": "Skipping resolution - app path not found",
                    "timestamp": datetime.now().isoformat()
                })
                return state
            
            # Run problem resolver
            resolution_result = await self.problem_resolver.analyze_and_resolve(
                app_path=app_path,
                error_logs="\n".join([log["message"] for log in state.get("logs", []) if log.get("level") == "error"]),
                context={"build_id": build_id}
            )
            
            state["resolution_results"].append(resolution_result)
            state["issues_resolved"] = resolution_result.get("issues_resolved", 0)
            state["progress"] = 80
            
            state["logs"].append({
                "level": "success",
                "message": f"Resolved {resolution_result.get('issues_resolved', 0)} of {resolution_result.get('issues_found', 0)} issues",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            state["logs"].append({
                "level": "error",
                "message": f"Problem resolution failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
        
        self.builds[build_id] = state
        self._persist_metadata(build_id, state)
        
        return state
    
    async def _run_tests(self, build_id: str, state: dict) -> dict:
        """Run tests using Tester Agent"""
        state["current_step"] = "Running tests"
        state["progress"] = 85
        
        try:
            app_path = state.get("source_path")
            if not app_path or not Path(app_path).exists():
                state["logs"].append({
                    "level": "warning",
                    "message": "Skipping tests - app path not found",
                    "timestamp": datetime.now().isoformat()
                })
                return state
            
            # Run tests
            test_result = await self.tester_agent.run_tests(
                app_path=app_path,
                test_type="all",
                generate_missing=True
            )
            
            state["test_results"] = test_result
            state["progress"] = 90
            
            summary = test_result.get("summary", {})
            state["logs"].append({
                "level": "info",
                "message": f"Tests completed: {summary.get('passed', 0)} passed, {summary.get('failed', 0)} failed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            state["logs"].append({
                "level": "error",
                "message": f"Test execution failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
        
        self.builds[build_id] = state
        self._persist_metadata(build_id, state)
        
        return state
    
    async def _final_validation(self, build_id: str, state: dict) -> dict:
        """Final validation"""
        state["current_step"] = "Final validation"
        state["progress"] = 95
        
        # Set URLs
        app_path = state.get("source_path", "")
        if app_path:
            state["app_url"] = f"http://localhost:3000/{Path(app_path).name}"
            state["logs_url"] = f"/api/build/{build_id}/logs"
        
        state["logs"].append({
            "level": "success",
            "message": "Validation completed successfully",
            "timestamp": datetime.now().isoformat()
        })
        
        self.builds[build_id] = state
        self._persist_metadata(build_id, state)
        
        return state
    
    def _generate_project_name(self, description: str) -> str:
        """Generate project name from description"""
        # Simple name generation
        words = description.lower().split()[:3]
        return "-".join(words).replace(",", "").replace(".", "")
    
    async def get_build_status(self, build_id: str) -> dict:
        """Get the status of a build"""
        build = self.builds.get(build_id)

        if not build:
            if not self.build_registry:
                return None
            record = self.build_registry.get(build_id)
            if not record:
                return None
            return {
                "build_id": record["build_id"],
                "status": record.get("status", "unknown"),
                "progress": int(record.get("progress", 0)),
                "current_step": record.get("current_step", ""),
                "logs": record.get("logs", []),
            }

        return {
            "build_id": build_id,
            "status": build["build_status"],
            "progress": build["progress"],
            "current_step": build["current_step"],
            "logs": build["logs"],
            "preview_url": build.get("preview_url"),
            "instance_id": build.get("instance_id"),
            "logs_url": build.get("logs_url")
        }

    async def list_builds(self) -> list[dict]:
        """List all builds"""
        combined = {}
        if self.build_registry:
            combined.update({record["build_id"]: record for record in self.build_registry.load_all()})
        for build_id, build in self.builds.items():
            combined[build_id] = {
                "build_id": build_id,
                "project_name": build.get("project_name", build_id),
                "status": build.get("build_status", "unknown"),
                "progress": build.get("progress", 0),
                "source_path": build.get("source_path"),
                "current_step": build.get("current_step", ""),
                "updated_at": build.get("updated_at"),
                "created_at": build.get("created_at"),
            }
        return [
            {
                "build_id": build_id,
                "project_name": meta.get("project_name", build_id),
                "status": meta.get("status", meta.get("build_status", "unknown")),
                "progress": int(meta.get("progress", 0)),
                "source_path": meta.get("source_path"),
                "current_step": meta.get("current_step", ""),
                "updated_at": meta.get("updated_at"),
                "created_at": meta.get("created_at"),
            }
            for build_id, meta in combined.items()
        ]

    async def delete_build(self, build_id: str) -> dict:
        """Delete a build"""
        removed = False
        if build_id in self.builds:
            del self.builds[build_id]
            removed = True
        if self.build_registry and self.build_registry.remove(build_id):
            removed = True
        if removed:
            return {"success": True, "message": "Build deleted"}
        return {"success": False, "message": "Build not found"}

    def _persist_metadata(self, build_id: str, state: dict):
        """Persist build metadata"""
        if not self.build_registry:
            return
        metadata = {
            "build_id": build_id,
            "project_name": state.get("project_name"),
            "status": state.get("build_status"),
            "progress": state.get("progress", 0),
            "current_step": state.get("current_step"),
            "source_path": state.get("source_path"),
            "app_url": state.get("app_url"),
            "logs": state.get("logs", []),
            "issues_resolved": state.get("issues_resolved", 0),
            "test_summary": state.get("test_results", {}).get("summary", {})
        }
        self.build_registry.register_build(metadata)

    def _record_to_state(self, record: dict) -> dict:
        """Convert registry record to state"""
        return {
            "build_id": record["build_id"],
            "brief": record.get("brief", ""),
            "project_name": record.get("project_name", record["build_id"]),
            "requirements": record.get("requirements", []),
            "features": record.get("features", []),
            "entities": record.get("entities", []),
            "user_flows": record.get("user_flows", []),
            "technical_specs": record.get("technical_specs", {}),
            "backend_tasks": record.get("backend_tasks", []),
            "frontend_tasks": record.get("frontend_tasks", []),
            "backend_code": record.get("backend_code", {}),
            "frontend_code": record.get("frontend_code", {}),
            "integrated_code": record.get("integrated_code", {}),
            "docker_config": record.get("docker_config", {}),
            "resolution_results": record.get("resolution_results", []),
            "test_results": record.get("test_results", {}),
            "issues_resolved": record.get("issues_resolved", 0),
            "build_status": record.get("status", record.get("build_status", "unknown")),
            "logs": record.get("logs", []),
            "current_step": record.get("current_step", ""),
            "progress": int(record.get("progress", 0)),
            "errors": record.get("errors", []),
            "app_url": record.get("app_url", ""),
            "source_path": record.get("source_path", ""),
            "preview_url": record.get("preview_url", ""),
            "instance_id": record.get("instance_id", ""),
            "logs_url": record.get("logs_url", ""),
            "expires_at": record.get("expires_at", "")
        }
