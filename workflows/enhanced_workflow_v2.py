"""
Enhanced Workflow V2 - Integrates all new agents and features
"""
import uuid
from typing import TypedDict, Annotated
import operator
from datetime import datetime
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI

from agents.coordinator_agent import CoordinatorAgent
from agents.backend_agent import BackendAgent
from agents.frontend_agent import FrontendAgent
from agents.integration_agent import IntegrationAgent
from agents.security_agent import SecurityAgent
from agents.optimization_agent import OptimizationAgent
from agents.documentation_agent import DocumentationAgent
from config.settings import Settings
from services.build_registry import BuildRegistry
from services.code_generation_cache import CodeGenerationCache
from services.enhanced_state_manager import EnhancedStateManager


class EnhancedAppBuilderStateV2(TypedDict):
    """Enhanced state with all new fields"""
    build_id: str
    brief: str
    project_name: str
    requirements: list[str]
    
    # Planning
    features: list[dict]
    entities: list[dict]
    user_flows: list[dict]
    technical_specs: dict
    
    # Development
    backend_tasks: list[dict]
    frontend_tasks: list[dict]
    backend_code: dict
    frontend_code: dict
    
    # Integration
    integrated_code: dict
    docker_config: dict
    
    # New: Security & Optimization
    security_audit: dict
    optimization_results: dict
    documentation: dict
    
    # Status
    build_status: str
    logs: Annotated[list[dict], operator.add]
    current_step: str
    progress: int
    errors: list[str]
    app_url: str
    source_path: str


class EnhancedWorkflowV2:
    """
    Enhanced workflow integrating:
    - Security scanning and auto-fix
    - Performance optimization
    - Comprehensive documentation generation
    - Code quality validation
    - Caching layer
    - CI/CD pipeline generation
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.builds = {}
        
        # Initialize registry and state manager
        repo_root = Path(settings.generated_apps_dir).resolve().parent
        self.build_registry = BuildRegistry(repo_root)
        self.state_manager = EnhancedStateManager(repo_root)
        
        # Initialize cache
        self.cache = CodeGenerationCache()
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            temperature=0.7,
            google_api_key=settings.google_api_key
        )
        
        # Initialize all agents
        self.coordinator = CoordinatorAgent(self.llm, settings)
        self.backend_agent = BackendAgent(self.llm, settings)
        self.frontend_agent = FrontendAgent(self.llm, settings)
        self.integration_agent = IntegrationAgent(self.llm, settings)
        
        # NEW: Initialize specialized agents
        self.security_agent = SecurityAgent(self.llm, settings)
        self.optimization_agent = OptimizationAgent(self.llm, settings)
        self.documentation_agent = DocumentationAgent(self.llm, settings)
    
    async def build_from_brief(
        self,
        description: str,
        name: str = None,
        requirements: list[str] = None
    ) -> dict:
        """
        Build application with all enhancements
        """
        # Validate input
        if not description or not description.strip():
            raise ValueError("Project description cannot be empty")
        
        build_id = str(uuid.uuid4())
        project_name = name or self._generate_project_name(description)
        
        # Initialize state
        state = {
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
            "security_audit": {},
            "optimization_results": {},
            "documentation": {},
            "build_status": "building",
            "logs": [],
            "current_step": "Starting",
            "progress": 0,
            "errors": [],
            "app_url": "",
            "source_path": ""
        }
        
        self.builds[build_id] = state
        
        try:
            # Step 1: Analyze brief
            state = await self._step_analyze_brief(state)
            
            # Step 2: Generate specs
            state = await self._step_generate_specs(state)
            
            # Step 3: Plan tasks
            state = await self._step_plan_tasks(state)
            
            # Step 4: Generate backend (with caching)
            state = await self._step_generate_backend(state)
            
            # Step 5: Generate frontend (with caching)
            state = await self._step_generate_frontend(state)
            
            # Step 6: Security audit
            state = await self._step_security_audit(state)
            
            # Step 7: Optimize code
            state = await self._step_optimize(state)
            
            # Step 8: Generate documentation
            state = await self._step_generate_docs(state)
            
            # Step 9: Integrate code (includes CI/CD)
            state = await self._step_integrate(state)
            
            # Step 10: Validate
            state = await self._step_validate(state)
            
            # Complete
            state["build_status"] = "success"
            state["progress"] = 100
            state["current_step"] = "Complete"
            
            self.builds[build_id] = state
            self._persist_state(build_id, state)
            
            return {
                "status": "success",
                "build_id": build_id,
                "message": "Application built successfully with all enhancements",
                "app_url": state.get("app_url"),
                "source_path": state.get("source_path"),
                "logs": state.get("logs", []),
                "security_score": state["security_audit"].get("severity_score", 0),
                "optimizations_applied": len(state["optimization_results"].get("optimizations", []))
            }
            
        except Exception as e:
            state["build_status"] = "failed"
            state["errors"].append(str(e))
            self.builds[build_id] = state
            self._persist_state(build_id, state)
            raise
    
    async def _step_analyze_brief(self, state: dict) -> dict:
        """Step 1: Analyze brief"""
        self._log(state, "Analyzing project brief...")
        state["current_step"] = "Analyzing brief"
        state["progress"] = 10
        
        analysis = await self.coordinator.analyze_brief(state["brief"])
        state["features"] = analysis["features"]
        state["entities"] = analysis["entities"]
        state["user_flows"] = analysis["user_flows"]
        
        self._log(state, f"Identified {len(state['features'])} features, {len(state['entities'])} entities")
        return state
    
    async def _step_generate_specs(self, state: dict) -> dict:
        """Step 2: Generate technical specs"""
        self._log(state, "Generating technical specifications...")
        state["current_step"] = "Generating specs"
        state["progress"] = 20
        
        specs = await self.coordinator.generate_technical_specs(
            state["features"],
            state["entities"],
            state["user_flows"]
        )
        state["technical_specs"] = specs
        
        return state
    
    async def _step_plan_tasks(self, state: dict) -> dict:
        """Step 3: Plan tasks"""
        self._log(state, "Planning development tasks...")
        state["current_step"] = "Planning tasks"
        state["progress"] = 30
        
        tasks = await self.coordinator.plan_tasks(state["technical_specs"])
        state["backend_tasks"] = tasks["backend"]
        state["frontend_tasks"] = tasks["frontend"]
        
        return state
    
    async def _step_generate_backend(self, state: dict) -> dict:
        """Step 4: Generate backend with caching"""
        self._log(state, "Generating backend code...")
        state["current_step"] = "Generating backend"
        state["progress"] = 40
        
        # Check cache
        cache_key = self.cache.generate_cache_key(
            state["backend_tasks"],
            state["entities"]
        )
        cached = await self.cache.get_cached_code(cache_key)
        
        if cached:
            self._log(state, "Using cached backend code")
            state["backend_code"] = cached
        else:
            backend_code = await self.backend_agent.generate_code(
                state["backend_tasks"],
                state["entities"],
                state["technical_specs"]
            )
            state["backend_code"] = backend_code
            await self.cache.cache_code(cache_key, backend_code)
        
        return state
    
    async def _step_generate_frontend(self, state: dict) -> dict:
        """Step 5: Generate frontend with caching"""
        self._log(state, "Generating frontend code...")
        state["current_step"] = "Generating frontend"
        state["progress"] = 50
        
        # Check cache
        cache_key = self.cache.generate_cache_key(
            state["frontend_tasks"],
            state["user_flows"]
        )
        cached = await self.cache.get_cached_code(cache_key)
        
        if cached:
            self._log(state, "Using cached frontend code")
            state["frontend_code"] = cached
        else:
            frontend_code = await self.frontend_agent.generate_code(
                state["frontend_tasks"],
                state["user_flows"],
                state["technical_specs"],
                state["backend_code"]
            )
            state["frontend_code"] = frontend_code
            await self.cache.cache_code(cache_key, frontend_code)
        
        return state
    
    async def _step_security_audit(self, state: dict) -> dict:
        """Step 6: Security audit and auto-fix"""
        self._log(state, "Running security audit...")
        state["current_step"] = "Security audit"
        state["progress"] = 60
        
        audit = await self.security_agent.audit_code(
            state["backend_code"],
            state["frontend_code"]
        )
        state["security_audit"] = audit
        
        self._log(state, f"Security audit: {audit['total_issues']} issues found")
        
        # Auto-fix critical issues
        if audit["critical_count"] > 0:
            self._log(state, f"Auto-fixing {audit['critical_count']} critical security issues")
            state["backend_code"] = await self.security_agent.apply_security_fixes(
                state["backend_code"],
                audit["issues"]
            )
        
        return state
    
    async def _step_optimize(self, state: dict) -> dict:
        """Step 7: Optimize code"""
        self._log(state, "Optimizing code for performance...")
        state["current_step"] = "Optimizing"
        state["progress"] = 70
        
        # Optimize backend
        backend_opt = await self.optimization_agent.optimize_backend(
            state["backend_code"],
            state["technical_specs"]
        )
        state["backend_code"] = backend_opt["code"]
        
        # Optimize frontend
        frontend_opt = await self.optimization_agent.optimize_frontend(
            state["frontend_code"],
            state["technical_specs"]
        )
        state["frontend_code"] = frontend_opt["code"]
        
        state["optimization_results"] = {
            "backend": backend_opt["optimizations"],
            "frontend": frontend_opt["optimizations"],
            "optimizations": backend_opt["optimizations"] + frontend_opt["optimizations"]
        }
        
        self._log(state, f"Applied {len(state['optimization_results']['optimizations'])} optimizations")
        
        return state
    
    async def _step_generate_docs(self, state: dict) -> dict:
        """Step 8: Generate comprehensive documentation"""
        self._log(state, "Generating documentation...")
        state["current_step"] = "Generating docs"
        state["progress"] = 80
        
        docs = await self.documentation_agent.generate_all_docs(
            state["project_name"],
            state["technical_specs"],
            state["backend_code"],
            state["frontend_code"],
            state["user_flows"]
        )
        state["documentation"] = docs
        
        self._log(state, f"Generated {len(docs)} documentation files")
        
        return state
    
    async def _step_integrate(self, state: dict) -> dict:
        """Step 9: Integrate code (includes CI/CD)"""
        self._log(state, "Integrating code and generating CI/CD pipelines...")
        state["current_step"] = "Integrating"
        state["progress"] = 90
        
        result = await self.integration_agent.integrate(
            state["project_name"],
            state["backend_code"],
            state["frontend_code"],
            state["technical_specs"]
        )
        
        state["integrated_code"] = result["code"]
        state["docker_config"] = result["docker"]
        state["source_path"] = result["path"]
        
        # Write documentation files
        project_path = Path(result["path"])
        docs_dir = project_path / "docs"
        docs_dir.mkdir(exist_ok=True)
        
        for doc_name, doc_content in state["documentation"].items():
            doc_file = docs_dir / f"{doc_name}.md"
            doc_file.write_text(doc_content, encoding='utf-8')
        
        return state
    
    async def _step_validate(self, state: dict) -> dict:
        """Step 10: Validate build"""
        self._log(state, "Validating build...")
        state["current_step"] = "Validating"
        state["progress"] = 95
        
        validation = await self.integration_agent.validate(state["source_path"])
        
        if validation.get("status") == "failed":
            self._log(state, "Validation failed", level="warning")
        else:
            self._log(state, "Validation passed")
        
        return state
    
    def _log(self, state: dict, message: str, level: str = "info"):
        """Add log entry"""
        state["logs"].append({
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def _persist_state(self, build_id: str, state: dict):
        """Persist state"""
        self.build_registry.register_build({
            "build_id": build_id,
            "project_name": state["project_name"],
            "status": state["build_status"],
            "progress": state["progress"],
            "current_step": state["current_step"],
            "source_path": state.get("source_path"),
            "logs": state["logs"]
        })
    
    def _generate_project_name(self, description: str) -> str:
        """Generate project name from description"""
        words = description.lower().split()[:3]
        return "-".join(w for w in words if w.isalnum())
    
    async def get_build_status(self, build_id: str) -> dict:
        """Get build status"""
        if build_id in self.builds:
            build = self.builds[build_id]
            return {
                "build_id": build_id,
                "status": build["build_status"],
                "progress": build["progress"],
                "current_step": build["current_step"],
                "logs": build["logs"]
            }
        return None
    
    async def list_builds(self) -> list[dict]:
        """List all builds"""
        return [
            {
                "build_id": build_id,
                "project_name": build["project_name"],
                "status": build["build_status"],
                "progress": build["progress"],
                "source_path": build.get("source_path")
            }
            for build_id, build in self.builds.items()
        ]
    
    async def delete_build(self, build_id: str) -> dict:
        """Delete a build"""
        if build_id in self.builds:
            del self.builds[build_id]
            self.build_registry.remove(build_id)
            return {"success": True, "message": "Build deleted"}
        return {"success": False, "message": "Build not found"}
