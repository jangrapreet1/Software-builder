"""
Main entry point for the Autonomous App-Building Platform Coordinator
"""
import os
import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from rich.console import Console
from pathlib import Path
import json

from workflows.app_builder import AppBuilderWorkflow
from config.settings import Settings
from services.permission_manager import PermissionManager
from services.framework_registry import get_framework_registry, FrameworkType

# Load environment variables
load_dotenv()

# Initialize console for rich output
console = Console()

# Initialize FastAPI app
app = FastAPI(
    title="Autonomous App Builder - Coordinator",
    description="AI-driven platform for building web applications from project briefs",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load settings
settings = Settings()

# Initialize permission manager (used by UI stats panel)
permission_manager = PermissionManager(default_expiry=3600)

# Optionally use a lightweight fake workflow for testing to avoid external calls
USE_FAKE_WORKFLOW = os.getenv("USE_FAKE_WORKFLOW", "").lower() in ("1", "true", "yes")

if USE_FAKE_WORKFLOW:
    class _FakeWorkflow:
        def __init__(self):
            self._builds = {}

        async def build_from_brief(self, description: str, name: str | None = None, requirements: list[str] | None = None) -> dict:
            if not description or not description.strip():
                raise ValueError("Project description cannot be empty")
            import uuid
            bid = str(uuid.uuid4())
            project_name = name or "test-app"
            self._builds[bid] = {
                "build_id": bid,
                "project_name": project_name,
                "build_status": "success",
                "progress": 100,
                "current_step": "Complete",
                "logs": [{"level": "success", "message": "Completed", "timestamp": "2025-01-01T00:00:00"}],
                "app_url": f"http://localhost:3000/{project_name}",
                "source_path": f"./generated/{project_name}",
            }
            return {
                "status": "success",
                "build_id": bid,
                "message": "Application built successfully",
                "app_url": self._builds[bid]["app_url"],
                "source_path": self._builds[bid]["source_path"],
                "logs": self._builds[bid]["logs"],
            }

        async def get_build_status(self, build_id: str) -> dict | None:
            b = self._builds.get(build_id)
            if not b:
                return None
            return {
                "build_id": build_id,
                "status": b["build_status"],
                "progress": b["progress"],
                "current_step": b["current_step"],
                "logs": b["logs"],
            }

        async def list_builds(self) -> list[dict]:
            return [
                {
                    "build_id": b_id,
                    "project_name": b["project_name"],
                    "status": b["build_status"],
                    "progress": b["progress"],
                }
                for b_id, b in self._builds.items()
            ]

        async def delete_build(self, build_id: str) -> dict:
            if build_id in self._builds:
                del self._builds[build_id]
                return {"success": True, "message": "Build deleted"}
            return {"success": False, "message": "Build not found"}

    workflow = _FakeWorkflow()
else:
    # Initialize FIXED workflow
    from workflows.app_builder_fixed import AppBuilderWorkflowFixed
    workflow = AppBuilderWorkflowFixed(settings)


class ProjectBrief(BaseModel):
    """Project brief input model"""
    description: str
    name: str = None
    requirements: list[str] = []


class BuildResponse(BaseModel):
    """Build response model"""
    status: str
    build_id: str
    message: str
    app_url: str = None
    source_path: str = None
    logs: list[dict] = []


class BuildStatus(BaseModel):
    """Build status model"""
    build_id: str
    status: str
    progress: int
    current_step: str
    logs: list[dict]


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Autonomous App Builder - Coordinator",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/api/build", response_model=BuildResponse)
async def build_app(brief: ProjectBrief):
    """
    Build an application from a project brief
    
    This endpoint orchestrates the entire app-building process:
    1. Parse and analyze the brief
    2. Generate technical specifications
    3. Coordinate specialized agents
    4. Integrate generated code
    5. Validate and deploy
    """
    try:
        console.print(f"\n[bold green]Received build request:[/bold green] {brief.description}")
        
        # Start the workflow
        result = await workflow.build_from_brief(
            description=brief.description,
            name=brief.name,
            requirements=brief.requirements
        )
        
        return BuildResponse(
            status=result["status"],
            build_id=result["build_id"],
            message=result["message"],
            app_url=result.get("app_url"),
            source_path=result.get("source_path"),
            logs=result.get("logs", [])
        )
        
    except Exception as e:
        console.print(f"[bold red]Error building app:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/build/{build_id}/status", response_model=BuildStatus)
async def get_build_status(build_id: str):
    """Get the status of a build"""
    try:
        status = await workflow.get_build_status(build_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Build not found")
        
        return BuildStatus(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/builds")
async def list_builds():
    """List all builds"""
    try:
        builds = await workflow.list_builds()
        return {"builds": builds}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/build/{build_id}")
async def delete_build(build_id: str):
    """Delete a build and its artifacts"""
    try:
        result = await workflow.delete_build(build_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/build/{build_id}")
async def build_websocket(websocket: WebSocket, build_id: str):
    """Stream build progress in real-time"""
    await websocket.accept()
    try:
        while True:
            status = await workflow.get_build_status(build_id)
            if status:
                await websocket.send_json(status)
            
            if status and status.get("status") in ["success", "failed"]:
                break
            
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass


@app.get("/api/metrics/dashboard")
async def get_metrics_dashboard():
    """Get comprehensive metrics for monitoring"""
    try:
        from services.metrics_collector import get_metrics_collector
        metrics = get_metrics_collector()
        
        return {
            "builds": {
                "total": metrics.get_counter("builds.total"),
                "successful": metrics.get_counter("builds.successful"),
                "failed": metrics.get_counter("builds.failed"),
            },
            "agents": {
                "coordinator": {"avg_time": metrics.get_avg("agent.coordinator.duration")},
                "backend": {"avg_time": metrics.get_avg("agent.backend.duration")},
                "frontend": {"avg_time": metrics.get_avg("agent.frontend.duration")}
            }
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/permissions/stats")
async def permissions_stats():
    """Return permission system statistics for UI display"""
    try:
        stats = permission_manager.get_stats()
        return {"stats": stats}
    except Exception as e:
        return {"stats": {"total_permissions": 0, "active_permissions": 0, "total_executions": 0}, "error": str(e)}


@app.get("/api/v2/frameworks")
async def list_frameworks(framework_type: str | None = None):
    """List available frameworks filtered by type (backend|frontend)"""
    try:
        registry = get_framework_registry()
        if framework_type == "backend":
            fws = registry.get_all(FrameworkType.BACKEND)
        elif framework_type == "frontend":
            fws = registry.get_all(FrameworkType.FRONTEND)
        else:
            fws = registry.get_all()
        return {"frameworks": [fw.to_dict() for fw in fws]}
    except Exception as e:
        return {"frameworks": [], "error": str(e)}


# ============================================
# LIVE PREVIEW ENDPOINTS
# ============================================

@app.post("/api/preview/start")
async def start_live_preview(request: dict):
    """Start live preview for a project"""
    try:
        from services.live_preview_service import get_live_preview_service
        
        project_name = request.get("project_name")
        project_path = request.get("project_path")
        
        if not project_name or not project_path:
            raise HTTPException(status_code=400, detail="project_name and project_path required")
        
        preview_service = get_live_preview_service()
        result = await preview_service.start_preview(project_path, project_name)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/preview/stop")
async def stop_live_preview(request: dict):
    """Stop a running preview"""
    try:
        from services.live_preview_service import get_live_preview_service
        
        project_name = request.get("project_name")
        if not project_name:
            raise HTTPException(status_code=400, detail="project_name required")
        
        preview_service = get_live_preview_service()
        result = await preview_service.stop_preview(project_name)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/preview/active")
async def get_active_previews():
    """Get all active previews"""
    try:
        from services.live_preview_service import get_live_preview_service
        
        preview_service = get_live_preview_service()
        previews = preview_service.get_active_previews()
        
        return {"previews": previews}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/preview/health/{project_name}")
async def check_preview_health(project_name: str):
    """Check health of a running preview"""
    try:
        from services.live_preview_service import get_live_preview_service
        
        preview_service = get_live_preview_service()
        health = await preview_service.check_preview_health(project_name)
        
        return health
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/preview/resolve-error")
async def resolve_preview_error(request: dict):
    """Auto-resolve preview errors"""
    try:
        from services.live_preview_service import get_live_preview_service
        
        project_name = request.get("project_name")
        error = request.get("error")
        
        if not project_name or not error:
            raise HTTPException(status_code=400, detail="project_name and error required")
        
        preview_service = get_live_preview_service()
        result = await preview_service.auto_resolve_error(project_name, error)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# TESTER ENDPOINTS
# ============================================

@app.post("/api/test/run")
async def run_tests(request: dict):
    """Run tests on a project"""
    try:
        from agents.tester_agent import TesterAgent
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        project_path = request.get("project_path")
        test_type = request.get("test_type", "all")
        generate_missing = request.get("generate_missing", True)
        
        if not project_path:
            raise HTTPException(status_code=400, detail="project_path required")
        
        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key
        )
        
        tester = TesterAgent(llm, settings)
        result = await tester.run_tests(
            app_path=project_path,
            test_type=test_type,
            generate_missing=generate_missing
        )
        
        # If tests failed, trigger auto-fix
        if result["status"] == "failed" and result["summary"]["failed"] > 0:
            await trigger_auto_fix(project_path, result)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/test/history")
async def get_test_history():
    """Get test history"""
    try:
        from agents.tester_agent import TesterAgent
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key
        )
        
        tester = TesterAgent(llm, settings)
        history = tester.get_test_history()
        
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test/generate-suggestions")
async def generate_test_suggestions(request: dict):
    """Generate test suggestions for a project"""
    try:
        from agents.tester_agent import TesterAgent
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        project_path = request.get("project_path")
        if not project_path:
            raise HTTPException(status_code=400, detail="project_path required")
        
        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key
        )
        
        tester = TesterAgent(llm, settings)
        suggestions = await tester.generate_test_suggestions(project_path)
        
        return suggestions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def trigger_auto_fix(project_path: str, test_results: dict):
    """Trigger auto-fix workflow for test failures"""
    try:
        # Analyze failures and route to appropriate agents
        failures = test_results.get("failures", [])
        
        for failure in failures:
            # Determine which agent should handle the fix
            if "backend" in failure.get("test", "").lower():
                # Route to backend agent
                pass
            elif "frontend" in failure.get("test", "").lower() or "component" in failure.get("test", "").lower():
                # Route to frontend agent
                pass
            else:
                # Route to integration agent
                pass
    except Exception as e:
        print(f"Auto-fix failed: {e}")


# ============================================
# PROJECT MANAGEMENT ENDPOINTS
# ============================================

@app.get("/api/projects")
async def list_all_projects():
    """List all projects for current user"""
    try:
        import os
        from pathlib import Path
        
        generated_dir = Path(settings.generated_apps_dir)
        
        if not generated_dir.exists():
            return {"projects": []}
        
        projects = []
        for project_dir in generated_dir.iterdir():
            if project_dir.is_dir():
                # Get project metadata
                metadata_file = project_dir / ".project_metadata.json"
                metadata = {}
                
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                    except:
                        pass
                
                projects.append({
                    "name": project_dir.name,
                    "path": str(project_dir),
                    "created_at": metadata.get("created_at"),
                    "last_modified": metadata.get("last_modified"),
                    "description": metadata.get("description"),
                    "status": metadata.get("status", "ready"),
                    "has_backend": (project_dir / "backend").exists(),
                    "has_frontend": (project_dir / "frontend").exists()
                })
        
        return {"projects": projects}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/{project_name}")
async def get_project_details(project_name: str):
    """Get detailed information about a project"""
    try:
        from pathlib import Path
        
        project_path = Path(settings.generated_apps_dir) / project_name
        
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Read metadata
        metadata_file = project_path / ".project_metadata.json"
        metadata = {}
        
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        
        # Get file structure
        structure = {
            "backend": list_directory_structure(project_path / "backend") if (project_path / "backend").exists() else None,
            "frontend": list_directory_structure(project_path / "frontend") if (project_path / "frontend").exists() else None
        }
        
        return {
            "name": project_name,
            "path": str(project_path),
            "metadata": metadata,
            "structure": structure
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def list_directory_structure(path: Path, max_depth: int = 2, current_depth: int = 0) -> dict:
    """List directory structure up to max_depth"""
    if current_depth >= max_depth:
        return {"type": "directory", "children": []}
    
    result = {"type": "directory", "children": []}
    
    try:
        for item in path.iterdir():
            if item.name.startswith(".") or item.name == "node_modules" or item.name == "__pycache__":
                continue
            
            if item.is_file():
                result["children"].append({
                    "name": item.name,
                    "type": "file",
                    "size": item.stat().st_size
                })
            elif item.is_dir():
                result["children"].append({
                    "name": item.name,
                    "type": "directory",
                    "children": list_directory_structure(item, max_depth, current_depth + 1).get("children", [])
                })
    except Exception:
        pass
    
    return result


# Serve UI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

ui_path = os.path.join(os.path.dirname(__file__), "ui")
if os.path.exists(ui_path):
    @app.get("/ui")
    async def serve_ui():
        """Serve the testing UI"""
        return FileResponse(os.path.join(ui_path, "index.html"))


if __name__ == "__main__":
    import uvicorn
    
    console.print("\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]  Autonomous App-Building Platform - Coordinator  [/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════[/bold cyan]\n")
    
    uvicorn.run(
        "main:app",
        host=settings.coordinator_host,
        port=settings.coordinator_port,
        reload=True,
        log_level="info"
    )
