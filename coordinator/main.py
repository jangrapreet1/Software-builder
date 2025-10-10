"""
Main entry point for the Autonomous App-Building Platform Coordinator
"""
import os
import asyncio
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from rich.console import Console

from workflows.app_builder import AppBuilderWorkflow
from config.settings import Settings

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

BASE_DIR = Path(__file__).resolve().parent
GENERATED_DIR = Path(settings.generated_apps_dir).resolve()

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
    import os
    
    # Configure file watcher settings using environment variables
    os.environ["WATCHFILES_FORCE_POLLING"] = "1"  # More reliable on Windows
    os.environ["WATCHFILES_IGNORE_PATTERNS"] = "*generated*"  # Ignore any path with 'generated'
    
    # Get absolute paths
    base_path = str(BASE_DIR.absolute())
    generated_path = str(GENERATED_DIR.absolute())
    
    # Print configuration for debugging
    console.print("\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]  Autonomous App-Building Platform - Coordinator  [/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════[/bold cyan]\n")
    console.print(f"[CONFIG] Watching directory: {base_path}")
    console.print(f"[CONFIG] Excluding pattern: *generated*")
    console.print(f"[CONFIG] Using polling: Yes\n")
    
    # Simple uvicorn configuration without problematic parameters
    uvicorn.run(
        "main:app",
        host=settings.coordinator_host,
        port=settings.coordinator_port,
        reload=True,
        log_level="info"
    )
