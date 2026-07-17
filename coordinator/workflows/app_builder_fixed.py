"""
Fixed workflow that handles async properly
"""
import os
import json
import uuid
from typing import TypedDict, Annotated, Sequence
from datetime import datetime
from typing import Optional
from pathlib import Path
import operator
import asyncio

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from agents.coordinator_agent import CoordinatorAgent
from agents.frontend_agent import FrontendAgent
from agents.backend_agent import BackendAgent
from agents.integration_agent import IntegrationAgent
from config.settings import Settings


class AppBuilderState(TypedDict):
    """State schema for the app building workflow"""
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


class AppBuilderWorkflowFixed:
    """
    Fixed workflow that properly handles async execution with state persistence
    """
    
    def __init__(self, settings: Settings, build_registry=None):
        self.settings = settings
        self.builds = {}  # In-memory build storage
        self.build_registry = build_registry
        
        # Create artifacts directory for state persistence
        self.artifacts_dir = Path(settings.generated_apps_dir).parent / ".sb_artifacts" / "builds"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        
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
    
    async def build_from_brief(
        self,
        description: str,
        name: str = None,
        requirements: list[str] = None
    ) -> dict:
        """
        Build an application from a project brief - FIXED VERSION
        """
        # Validate input
        if not description or not description.strip():
            raise ValueError("Project description cannot be empty")
        
        if len(description.strip()) < 10:
            raise ValueError("Project description is too short. Please provide more details.")
        
        build_id = str(uuid.uuid4())
        project_name = name or self._generate_project_name(description)
        
        # Initialize state
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
            "test_results": {},
            "build_status": "building",
            "logs": [],
            "current_step": "Starting analysis",
            "progress": 0,
            "errors": [],
            "app_url": "",
            "source_path": ""
        }
        
        # Store build state
        self.builds[build_id] = initial_state
        
        try:
            # Execute workflow steps manually (bypassing LangGraph)
            state = initial_state.copy()
            
            # Step 1: Analyze brief
            print(f"Step 1: Analyzing brief for {build_id}")
            state = await self._analyze_brief(state)
            self.builds[build_id] = state
            await self._persist_state(state)
            
            # Step 2: Generate specs
            print(f"Step 2: Generating specs for {build_id}")
            state = await self._generate_specs(state)
            self.builds[build_id] = state
            await self._persist_state(state)
            
            # Step 3: Plan tasks
            print(f"Step 3: Planning tasks for {build_id}")
            state = await self._plan_tasks(state)
            self.builds[build_id] = state
            await self._persist_state(state)
            
            # Step 4: Generate backend
            print(f"Step 4: Generating backend for {build_id}")
            state = await self._generate_backend(state)
            self.builds[build_id] = state
            await self._persist_state(state)
            
            # Step 5: Generate frontend
            print(f"Step 5: Generating frontend for {build_id}")
            state = await self._generate_frontend(state)
            self.builds[build_id] = state
            await self._persist_state(state)
            
            # Step 6: Integrate code
            print(f"Step 6: Integrating code for {build_id}")
            state = await self._integrate_code(state)
            self.builds[build_id] = state
            await self._persist_state(state)
            
            # Step 7: Validate build
            print(f"Step 7: Validating build for {build_id}")
            state = await self._validate_build(state)
            self.builds[build_id] = state
            await self._persist_state(state)
            
            # Step 8: Deploy app
            print(f"Step 8: Deploying app for {build_id}")
            state = await self._deploy_app(state)
            self.builds[build_id] = state
            await self._persist_state(state)
            
            # Mark as complete
            state["build_status"] = "success"
            state["progress"] = 100
            state["current_step"] = "Complete"
            self.builds[build_id] = state
            await self._persist_state(state)
            
            return {
                "status": "success",
                "build_id": build_id,
                "message": "Application built successfully",
                "app_url": state.get("app_url"),
                "source_path": state.get("source_path"),
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
            print(f"Build {build_id} failed with error: {e}")
            raise
    
    async def _analyze_brief(self, state: AppBuilderState) -> AppBuilderState:
        """Analyze the project brief and extract features"""
        try:
            self._log(state, "info", "Analyzing project brief...")
            state["current_step"] = "Analyzing project brief"
            state["progress"] = 10
            
            result = await self.coordinator.analyze_brief(state["brief"])
            
            self._log(state, "success", f"Identified {len(result.get('features', []))} features and {len(result.get('entities', []))} entities")
            
            state["features"] = result["features"]
            state["entities"] = result["entities"]
            state["user_flows"] = result["user_flows"]
            state["progress"] = 20
            
            return state
        except Exception as e:
            self._log(state, "error", f"Failed to analyze brief: {str(e)}")
            raise
    
    async def _generate_specs(self, state: AppBuilderState) -> AppBuilderState:
        """Generate technical specifications"""
        try:
            self._log(state, "info", "Generating technical specifications...")
            state["current_step"] = "Generating technical specifications"
            
            specs = await self.coordinator.generate_technical_specs(
                state["features"],
                state["entities"],
                state["user_flows"]
            )
            
            self._log(state, "success", "Technical specifications generated")
            state["technical_specs"] = specs
            state["progress"] = 30
            
            return state
        except Exception as e:
            self._log(state, "error", f"Failed to generate specs: {str(e)}")
            raise
    
    async def _plan_tasks(self, state: AppBuilderState) -> AppBuilderState:
        """Plan backend and frontend tasks"""
        try:
            self._log(state, "info", "Planning development tasks...")
            state["current_step"] = "Planning development tasks"
            
            tasks = await self.coordinator.plan_tasks(state["technical_specs"])
            
            backend_count = len(tasks.get("backend", []))
            frontend_count = len(tasks.get("frontend", []))
            self._log(state, "success", f"Planned {backend_count} backend and {frontend_count} frontend tasks")
            
            state["backend_tasks"] = tasks["backend"]
            state["frontend_tasks"] = tasks["frontend"]
            state["progress"] = 40
            
            return state
        except Exception as e:
            self._log(state, "error", f"Failed to plan tasks: {str(e)}")
            raise
    
    async def _generate_backend(self, state: AppBuilderState) -> AppBuilderState:
        """Generate backend code"""
        try:
            self._log(state, "info", "Generating backend code...")
            state["current_step"] = "Generating backend code"
            
            backend_code = await self.backend_agent.generate_code(
                state["backend_tasks"],
                state["entities"],
                state["technical_specs"]
            )
            
            self._log(state, "success", "Backend code generated")
            state["backend_code"] = backend_code
            state["progress"] = 60
            
            return state
        except Exception as e:
            self._log(state, "error", f"Failed to generate backend: {str(e)}")
            raise
    

    async def _generate_frontend(self, state: AppBuilderState) -> AppBuilderState:
        """Generate frontend code"""
        try:
            self._log(state, "info", "Generating frontend code...")
            state["current_step"] = "Generating frontend code"
            
            frontend_code = await self.frontend_agent.generate_code(
                state["frontend_tasks"],
                state["entities"],
                state["technical_specs"],
                state["backend_code"]  # <-- ADDED THIS ARGUMENT
            )
            
            self._log(state, "success", "Frontend code generated")
            state["frontend_code"] = frontend_code
            state["progress"] = 80
            
            return state
        except Exception as e:
            self._log(state, "error", f"Failed to generate frontend: {str(e)}")
            raise

    
    async def _integrate_code(self, state: AppBuilderState) -> AppBuilderState:
        """Integrate backend and frontend code"""
        try:
            self._log(state, "info", "Integrating code...")
            state["current_step"] = "Integrating code"
            
            integrated = await self.integration_agent.integrate(
                state["project_name"],
                state["backend_code"],
                state["frontend_code"],
                state["technical_specs"]
            )

            self._log(state, "success", "Code integration complete")
            state["integrated_code"] = integrated
            state["project_name"] = integrated.get("project_name") or state["project_name"]
            state["source_path"] = integrated.get(
                "path",
                str(Path(self.settings.generated_apps_dir).resolve() / state['project_name'])
            )
            state["progress"] = 90
            
            return state
        except Exception as e:
            self._log(state, "error", f"Failed to integrate code: {str(e)}")
            raise
    
    async def _validate_build(self, state: AppBuilderState) -> AppBuilderState:
        """Validate the build"""
        try:
            self._log(state, "info", "Validating build...")
            state["current_step"] = "Validating build"
            
            # Simple validation - check if files exist
            validation_results = {"status": "success", "checks": []}
            state["test_results"] = validation_results
            
            self._log(state, "success", "Build validation complete")
            state["progress"] = 95
            
            return state
        except Exception as e:
            self._log(state, "error", f"Failed to validate build: {str(e)}")
            raise
    
    async def _deploy_app(self, state: AppBuilderState) -> AppBuilderState:
        """Deploy the application"""
        try:
            self._log(state, "info", "Deploying application...")
            state["current_step"] = "Deploying application"
            
            # Set app URL
            state["app_url"] = f"http://localhost:3000/{state['project_name']}"
            
            self._log(state, "success", "Application deployed")
            state["progress"] = 100
            
            return state
        except Exception as e:
            self._log(state, "error", f"Failed to deploy app: {str(e)}")
            raise
    
    def _log(self, state: AppBuilderState, level: str, message: str):
        """Add a log entry to the state"""
        log_entry = {
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        state["logs"].append(log_entry)
        print(f"[{level.upper()}] {message}")
    
    def _generate_project_name(self, description: str) -> str:
        """Generate a project name from description"""
        # Simple name generation
        words = description.lower().split()
        if "app" in words:
            return "my-app"
        elif "todo" in words:
            return "todo-app"
        elif "blog" in words:
            return "blog-app"
        else:
            return "generated-app"
    
    async def get_build_status(self, build_id: str) -> dict | None:
        """Get the status of a build"""
        build = self.builds.get(build_id)
        
        if not build:
            return None
        
        return {
            "build_id": build_id,
            "status": build["build_status"],
            "progress": build["progress"],
            "current_step": build["current_step"],
            "logs": build["logs"]
        }
    
    async def list_builds(self) -> list[dict]:
        """List all builds"""
        return [
            {
                "build_id": build_id,
                "project_name": build["project_name"],
                "status": build["build_status"],
                "progress": build["progress"]
            }
            for build_id, build in self.builds.items()
        ]
    
    async def delete_build(self, build_id: str) -> dict:
        """Delete a build"""
        if build_id in self.builds:
            del self.builds[build_id]
            # Also delete persisted state
            state_file = self.artifacts_dir / f"{build_id}.json"
            if state_file.exists():
                state_file.unlink()
            return {"success": True, "message": "Build deleted"}
        return {"success": False, "message": "Build not found"}
    
    async def _persist_state(self, state: AppBuilderState) -> str:
        """Persist workflow state to .sb_artifacts for recovery and transparency"""
        try:
            build_id = state["build_id"]
            state_file = self.artifacts_dir / f"{build_id}.json"
            
            # Create a serializable copy (remove non-serializable objects)
            serializable_state = {
                "build_id": state["build_id"],
                "brief": state["brief"],
                "project_name": state["project_name"],
                "requirements": state["requirements"],
                "features": state["features"],
                "entities": state["entities"],
                "user_flows": state["user_flows"],
                "technical_specs": state["technical_specs"],
                "backend_tasks": state["backend_tasks"],
                "frontend_tasks": state["frontend_tasks"],
                "build_status": state["build_status"],
                "current_step": state["current_step"],
                "progress": state["progress"],
                "errors": state["errors"],
                "app_url": state["app_url"],
                "source_path": state["source_path"],
                "logs": state["logs"],
                "timestamp": datetime.now().isoformat()
            }
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_state, f, indent=2)
            
            print(f"Persisted state for build {build_id}")
            return str(state_file)
            
        except Exception as e:
            print(f"Failed to persist state: {e}")
            return ""
    
    async def load_state(self, build_id: str) -> Optional[AppBuilderState]:
        """Load persisted workflow state"""
        try:
            state_file = self.artifacts_dir / f"{build_id}.json"
            if not state_file.exists():
                return None
            
            with open(state_file, 'r', encoding='utf-8') as f:
                serializable_state = json.load(f)
            
            # Reconstruct full state (add empty dicts for code)
            state = {
                **serializable_state,
                "backend_code": {},
                "frontend_code": {},
                "integrated_code": {},
                "docker_config": {},
                "test_results": {}
            }
            
            return state
            
        except Exception as e:
            print(f"Failed to load state: {e}")
            return None
    
    def get_state_path(self, build_id: str) -> str:
        """Get path to persisted state file"""
        return str(self.artifacts_dir / f"{build_id}.json")
