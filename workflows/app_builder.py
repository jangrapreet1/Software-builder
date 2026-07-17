"""
Main workflow orchestration using LangGraph for app building
"""
import os
import json
import uuid
from typing import TypedDict, Annotated, Sequence
from datetime import datetime
import operator

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


class AppBuilderWorkflow:
    """
    Main workflow orchestrator using LangGraph
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.builds = {}  # In-memory build storage (use DB in production)
        
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
        
        # Build workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Create workflow graph
        workflow = StateGraph(AppBuilderState)
        
        # Add nodes for each step
        workflow.add_node("analyze_brief", self._analyze_brief)
        workflow.add_node("generate_specs", self._generate_specs)
        workflow.add_node("plan_tasks", self._plan_tasks)
        workflow.add_node("generate_backend", self._generate_backend)
        workflow.add_node("generate_frontend", self._generate_frontend)
        workflow.add_node("integrate_code", self._integrate_code)
        workflow.add_node("validate_build", self._validate_build)
        workflow.add_node("deploy_app", self._deploy_app)
        
        # Define workflow edges
        workflow.set_entry_point("analyze_brief")
        workflow.add_edge("analyze_brief", "generate_specs")
        workflow.add_edge("generate_specs", "plan_tasks")
        workflow.add_edge("plan_tasks", "generate_backend")
        workflow.add_edge("generate_backend", "generate_frontend")
        workflow.add_edge("generate_frontend", "integrate_code")
        workflow.add_edge("integrate_code", "validate_build")
        workflow.add_edge("validate_build", "deploy_app")
        workflow.add_edge("deploy_app", END)
        
        return workflow.compile()
    
    async def build_from_brief(
        self,
        description: str,
        name: str = None,
        requirements: list[str] = None
    ) -> dict:
        """
        Build an application from a project brief
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
            "build_status": "initializing",
            "logs": [],
            "current_step": "analyze_brief",
            "progress": 0,
            "errors": [],
            "app_url": "",
            "source_path": ""
        }
        
        # Store build state
        self.builds[build_id] = initial_state
        
        try:
            # Execute workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            # Update build state
            self.builds[build_id] = final_state
            
            return {
                "status": final_state["build_status"],
                "build_id": build_id,
                "message": "Application built successfully",
                "app_url": final_state.get("app_url"),
                "source_path": final_state.get("source_path"),
                "logs": final_state.get("logs", [])
            }
            
        except ValueError as e:
            # Validation errors
            self.builds[build_id]["build_status"] = "failed"
            self.builds[build_id]["errors"].append(str(e))
            self.builds[build_id]["logs"].append({
                "level": "error",
                "message": f"Validation error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
            raise
        except Exception as e:
            # General errors
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
    
    async def get_build_status(self, build_id: str) -> dict:
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
            return {"success": True, "message": "Build deleted"}
        return {"success": False, "message": "Build not found"}
    
    # Workflow step implementations
    
    async def _analyze_brief(self, state: AppBuilderState) -> dict:
        """Analyze the project brief and extract features"""
        try:
            self._log(state, "info", "Analyzing project brief...")
            state["current_step"] = "Analyzing project brief"
            state["progress"] = 10
            
            result = await self.coordinator.analyze_brief(state["brief"])
            
            self._log(state, "success", f"Identified {len(result.get('features', []))} features and {len(result.get('entities', []))} entities")
            
            return {
                "features": result["features"],
                "entities": result["entities"],
                "user_flows": result["user_flows"],
                "logs": [{"level": "success", "message": "Brief analysis complete", "timestamp": datetime.now().isoformat()}],
                "progress": 20
            }
        except Exception as e:
            self._log(state, "error", f"Failed to analyze brief: {str(e)}")
            raise
    
    async def _generate_specs(self, state: AppBuilderState) -> dict:
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
            
            return {
                "technical_specs": specs,
                "logs": [{"level": "success", "message": "Technical specs generated", "timestamp": datetime.now().isoformat()}],
                "progress": 30
            }
        except Exception as e:
            self._log(state, "error", f"Failed to generate specs: {str(e)}")
            raise
    
    async def _plan_tasks(self, state: AppBuilderState) -> dict:
        """Plan backend and frontend tasks"""
        try:
            self._log(state, "info", "Planning development tasks...")
            state["current_step"] = "Planning development tasks"
            
            tasks = await self.coordinator.plan_tasks(state["technical_specs"])
            
            backend_count = len(tasks.get("backend", []))
            frontend_count = len(tasks.get("frontend", []))
            self._log(state, "success", f"Planned {backend_count} backend and {frontend_count} frontend tasks")
            
            return {
                "backend_tasks": tasks["backend"],
                "frontend_tasks": tasks["frontend"],
                "logs": [{"level": "success", "message": f"Planned {backend_count} backend and {frontend_count} frontend tasks", "timestamp": datetime.now().isoformat()}],
                "progress": 40
            }
        except Exception as e:
            self._log(state, "error", f"Failed to plan tasks: {str(e)}")
            raise
    
    async def _generate_backend(self, state: AppBuilderState) -> dict:
        """Generate backend code"""
        try:
            self._log(state, "info", "Generating backend code (FastAPI + SQLAlchemy)...")
            state["current_step"] = "Generating backend code"
            
            backend_code = await self.backend_agent.generate_code(
                state["backend_tasks"],
                state["entities"],
                state["technical_specs"]
            )
            
            self._log(state, "success", f"Backend code generated ({len(backend_code)} files)")
            
            return {
                "backend_code": backend_code,
                "logs": [{"level": "success", "message": "Backend code generated", "timestamp": datetime.now().isoformat()}],
                "progress": 55
            }
        except Exception as e:
            self._log(state, "error", f"Failed to generate backend: {str(e)}")
            raise
    
    async def _generate_frontend(self, state: AppBuilderState) -> dict:
        """Generate frontend code"""
        try:
            self._log(state, "info", "Generating frontend code (React + TypeScript)...")
            state["current_step"] = "Generating frontend code"
            
            frontend_code = await self.frontend_agent.generate_code(
                state["frontend_tasks"],
                state["user_flows"],
                state["technical_specs"],
                state["backend_code"]
            )
            
            self._log(state, "success", "Frontend code generated with modern UI")
            
            return {
                "frontend_code": frontend_code,
                "logs": [{"level": "success", "message": "Frontend code generated", "timestamp": datetime.now().isoformat()}],
                "progress": 70
            }
        except Exception as e:
            self._log(state, "error", f"Failed to generate frontend: {str(e)}")
            raise
    
    async def _integrate_code(self, state: AppBuilderState) -> dict:
        """Integrate frontend and backend code"""
        try:
            self._log(state, "info", "Integrating application components...")
            state["current_step"] = "Integrating application"
            
            integration = await self.integration_agent.integrate(
                state["project_name"],
                state["backend_code"],
                state["frontend_code"],
                state["technical_specs"]
            )
            
            self._log(state, "success", f"Application integrated at {integration['path']}")
            
            return {
                "integrated_code": integration["code"],
                "docker_config": integration["docker"],
                "source_path": integration["path"],
                "logs": [{"level": "success", "message": "Code integration complete", "timestamp": datetime.now().isoformat()}],
                "progress": 85
            }
        except Exception as e:
            self._log(state, "error", f"Failed to integrate code: {str(e)}")
            raise
    
    async def _validate_build(self, state: AppBuilderState) -> dict:
        """Validate the build"""
        try:
            self._log(state, "info", "Validating build...")
            state["current_step"] = "Validating build"
            
            validation = await self.integration_agent.validate(state["source_path"])
            
            if validation.get("status") == "success":
                self._log(state, "success", "Build validation passed")
            else:
                self._log(state, "warning", "Build validation completed with warnings")
            
            return {
                "test_results": validation,
                "logs": [{"level": "success", "message": "Build validation complete", "timestamp": datetime.now().isoformat()}],
                "progress": 95
            }
        except Exception as e:
            self._log(state, "error", f"Validation failed: {str(e)}")
            # Don't raise - validation failures shouldn't stop deployment
            return {
                "test_results": {"status": "warning", "message": str(e)},
                "logs": [{"level": "warning", "message": f"Validation warning: {str(e)}", "timestamp": datetime.now().isoformat()}],
                "progress": 95
            }
    
    async def _deploy_app(self, state: AppBuilderState) -> dict:
        """Deploy the application"""
        try:
            self._log(state, "info", "Finalizing deployment...")
            state["current_step"] = "Deploying application"
            
            deployment = await self.integration_agent.deploy(
                state["source_path"],
                state["project_name"]
            )
            
            self._log(state, "success", f"✨ Application ready! Run 'docker-compose up' in {state['source_path']}")
            
            return {
                "app_url": deployment["url"],
                "build_status": "success",
                "logs": [{"level": "success", "message": f"🎉 Application deployed successfully!", "timestamp": datetime.now().isoformat()}],
                "progress": 100,
                "current_step": "Complete"
            }
        except Exception as e:
            self._log(state, "error", f"Deployment failed: {str(e)}")
            return {
                "app_url": "",
                "build_status": "failed",
                "logs": [{"level": "error", "message": f"Deployment failed: {str(e)}", "timestamp": datetime.now().isoformat()}],
                "progress": 100,
                "current_step": "Failed"
            }
    
    def _log(self, state: AppBuilderState, level: str, message: str):
        """Add a log entry"""
        log_entry = {
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        if "logs" not in state:
            state["logs"] = []
        state["logs"].append(log_entry)
    
    def _generate_project_name(self, description: str) -> str:
        """Generate a project name from description"""
        words = description.lower().split()[:3]
        return "-".join(words).replace(",", "").replace(".", "")
