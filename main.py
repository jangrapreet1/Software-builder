"""
Main entry point for the Autonomous App-Building Platform Coordinator
"""
import os
import asyncio
import io
import zipfile
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from rich.console import Console
from pathlib import Path
import json
import re
from datetime import datetime

from workflows.app_builder import AppBuilderWorkflow
from config.settings import Settings
from coordinator.services.permission_manager import PermissionManager
from coordinator.services.session_manager import SessionManager
from coordinator.services.repository_detector import RepositoryDetector
from services.path_policy import PathPolicyError, allowed_roots, ensure_allowed_root, resolve_safe_path
try:
    from services.framework_registry import get_framework_registry, FrameworkType
except ModuleNotFoundError:
    # Allow execution when run as package (e.g., coordinator.main)
    from coordinator.services.framework_registry import get_framework_registry, FrameworkType  # type: ignore

try:
    from api.enhanced_endpoints_v2 import router as v2_router, initialize_enhanced_services as init_v2
except ModuleNotFoundError:
    from coordinator.api.enhanced_endpoints_v2 import (  # type: ignore
        router as v2_router,
        initialize_enhanced_services as init_v2,
    )

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
REPO_ROOT = Path(__file__).resolve().parent
GENERATED_DIR = Path(settings.generated_apps_dir).resolve()
LOCAL_CONTROL_ALLOWED_ROOTS = allowed_roots([REPO_ROOT, GENERATED_DIR])

# Initialize permission manager (used by UI stats panel)
permission_manager = PermissionManager(default_expiry=3600)
session_manager = SessionManager(default_session_duration=3600)

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

# Initialize and mount Enhanced V2 endpoints (non-breaking)
try:
    init_v2(workflow, settings)
    app.include_router(v2_router)
except Exception as e:
    console.print(f"[bold yellow]Skipping Enhanced V2 endpoints: {e}[/bold yellow]")


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


@app.get("/api/v2/frameworks-legacy")
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

# React build from coordinator/ui/dist
react_dist_path = os.path.join(os.path.dirname(__file__), "coordinator", "ui", "dist")
react_assets_path = os.path.join(react_dist_path, "assets")

# Fallback Vue UI
vue_ui_path = os.path.join(os.path.dirname(__file__), "ui")

# Mount assets if React build exists
if os.path.exists(react_assets_path):
    app.mount("/assets", StaticFiles(directory=react_assets_path), name="assets")

@app.get("/ui")
async def serve_ui():
    """Serve the testing UI (React App or Fallback Vue)"""
    # Prefer built React app
    react_index = os.path.join(react_dist_path, "index.html")
    if os.path.exists(react_index):
        return FileResponse(react_index)
    
    # Fallback to Vue UI
    vue_index = os.path.join(vue_ui_path, "index.html")
    if os.path.exists(vue_index):
        return FileResponse(vue_index)
    
    return Response("UI not found", status_code=404)


# ============================================
# FILE SYSTEM ENDPOINTS (from coordinator/main.py)
# ============================================

class FSWriteRequest(BaseModel):
    root: str
    path: str
    content: str


class FSMkdirRequest(BaseModel):
    root: str
    path: str


class FSRenameRequest(BaseModel):
    root: str
    src: str
    dest: str


def _resolve_safe_path(root: str, rel_path: str) -> Path:
    try:
        _, target = resolve_safe_path(root, rel_path, LOCAL_CONTROL_ALLOWED_ROOTS)
        return target
    except PathPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _resolve_allowed_root(root: str) -> Path:
    try:
        return ensure_allowed_root(root, LOCAL_CONTROL_ALLOWED_ROOTS)
    except PathPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _reject_root_target(base: Path, target: Path, operation: str) -> None:
    if target == base:
        raise HTTPException(status_code=400, detail=f"Cannot {operation} the root directory")


def _secret_metadata(value: str) -> dict:
    return {"set": True, "length": len(value)}


def _validate_secret_key(key: str) -> str:
    cleaned = key.strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", cleaned):
        raise HTTPException(status_code=400, detail="Secret key must be a valid environment variable name")
    return cleaned


def _validate_secret_filename(filename: str) -> str:
    cleaned = filename.strip() or ".env"
    if Path(cleaned).name != cleaned or not cleaned.startswith(".env"):
        raise HTTPException(status_code=400, detail="Secrets can only be stored in .env files")
    return cleaned


@app.get("/api/fs/list")
async def fs_list(root: str, path: str = "."):
    base = _resolve_allowed_root(root)
    target = _resolve_safe_path(root, path)
    if not base.exists() or not target.exists():
        return {"root": str(base), "path": str(Path(path)), "items": []}
    if target.is_file():
        stat = target.stat()
        return {
            "type": "file",
            "name": target.name,
            "size": stat.st_size,
            "modified": datetime.utcfromtimestamp(stat.st_mtime).isoformat() + "Z",
            "path": str(target.relative_to(base))
        }
    items = []
    for entry in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        stat = entry.stat()
        items.append({
            "type": "directory" if entry.is_dir() else "file",
            "name": entry.name,
            "size": stat.st_size,
            "modified": datetime.utcfromtimestamp(stat.st_mtime).isoformat() + "Z",
            "path": str(entry.relative_to(base))
        })
    return {"root": str(base), "path": str(target.relative_to(base)), "items": items}


@app.get("/api/fs/read")
async def fs_read(root: str, path: str):
    target = _resolve_safe_path(root, path)
    if not target.exists() or not target.is_file():
        return JSONResponse(status_code=200, content={"error": "file_not_found", "path": path})
    try:
        content = target.read_text(encoding="utf-8")
        return {"path": path, "content": content}
    except UnicodeDecodeError:
        data = target.read_bytes()
        return JSONResponse(status_code=415, content={"error": "binary_file", "size": len(data)})


@app.post("/api/fs/write")
async def fs_write(req: FSWriteRequest):
    target = _resolve_safe_path(req.root, req.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(req.content, encoding="utf-8")
    return {"status": "success", "path": req.path}


@app.post("/api/fs/mkdir")
async def fs_mkdir(req: FSMkdirRequest):
    target = _resolve_safe_path(req.root, req.path)
    target.mkdir(parents=True, exist_ok=True)
    return {"status": "success"}


@app.post("/api/fs/rename")
async def fs_rename(req: FSRenameRequest):
    base = _resolve_allowed_root(req.root)
    src = _resolve_safe_path(req.root, req.src)
    dest = _resolve_safe_path(req.root, req.dest)
    _reject_root_target(base, src, "rename")
    dest.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dest)
    return {"status": "success"}


@app.delete("/api/fs/delete")
async def fs_delete(root: str, path: str):
    base = _resolve_allowed_root(root)
    target = _resolve_safe_path(root, path)
    _reject_root_target(base, target, "delete")
    if target.is_dir():
        for p in sorted(target.rglob("*"), reverse=True):
            if p.is_file():
                p.unlink(missing_ok=True)
            elif p.is_dir():
                p.rmdir()
        target.rmdir()
    else:
        target.unlink(missing_ok=True)
    return {"status": "success"}


# ============================================
# SECRETS ENDPOINTS
# ============================================

class SecretSetRequest(BaseModel):
    root: str
    key: str
    value: str
    filename: str = ".env"


@app.get("/api/secrets/list")
async def secrets_list(root: str, filename: str = ".env"):
    base = _resolve_allowed_root(root)
    env_file = _resolve_safe_path(root, _validate_secret_filename(filename))
    secrets: dict = {}
    if env_file.exists() and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if not line or line.strip().startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                secrets[k.strip()] = _secret_metadata(v.strip())
    return {"path": str(env_file.relative_to(base)), "secrets": secrets}


@app.post("/api/secrets/set")
async def secrets_set(req: SecretSetRequest):
    key = _validate_secret_key(req.key)
    env_file = _resolve_safe_path(req.root, _validate_secret_filename(req.filename))
    lines: list[str] = []
    replaced = False
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.strip().startswith("#") or "=" not in line:
                lines.append(line)
                continue
            existing_key, _ = line.split("=", 1)
            if existing_key.strip() == key:
                lines.append(f"{key}={req.value}")
                replaced = True
            else:
                lines.append(line)
    if not replaced:
        lines.append(f"{key}={req.value}")
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "success"}


# ============================================
# GIT ENDPOINTS
# ============================================

import subprocess


def _run_git(repo_path: str, args: list) -> dict:
    repo = _resolve_allowed_root(repo_path)
    if not repo.exists():
        return {"exit_code": 1, "stdout": "", "stderr": "Repository path not found"}
    try:
        result = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, timeout=120)
        return {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    except FileNotFoundError:
        return {"exit_code": 1, "stdout": "", "stderr": "Git not available"}


@app.get("/api/git/status")
async def git_status(repo_path: str):
    repo = _resolve_allowed_root(repo_path)
    if not repo.exists():
        return {"exit_code": 1, "stdout": "", "stderr": "Repository path not found"}
    res = _run_git(repo_path, ["status", "--porcelain", "-b"])
    return res


# ============================================
# REPO DETECTION ENDPOINT
# ============================================

class RepoDetectRequest(BaseModel):
    path: str = ""
    root: str = ""  # Alternative field name
    repo_path: str = ""  # Another alternative


@app.post("/api/repo/detect")
async def repo_detect(req: RepoDetectRequest):
    # Accept any of these fields
    target_path = req.path or req.root or req.repo_path
    if not target_path:
        raise HTTPException(status_code=400, detail="No path provided")
    candidate = Path(target_path).expanduser()
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    target = _resolve_allowed_root(target_path)

    detector = RepositoryDetector(str(target))
    report = detector.detect_all()
    return {
        "status": "success",
        "detection_report": report,
        # Compatibility fields for older callers.
        "detected": True,
        "path": str(target),
        "has_git": (target / ".git").exists(),
        "has_package_json": (target / "package.json").exists(),
        "has_requirements": (target / "requirements.txt").exists(),
    }


# ============================================
# GENERATED PROJECTS ENDPOINT
# ============================================

@app.get("/api/generated/projects")
async def list_generated_projects():
    generated_dir = Path(settings.generated_apps_dir)
    if not generated_dir.exists():
        return {"projects": []}
    projects = []
    for proj in generated_dir.iterdir():
        if proj.is_dir():
            projects.append({
                "name": proj.name,
                "path": str(proj),
                "has_backend": (proj / "backend").exists(),
                "has_frontend": (proj / "frontend").exists()
            })
    return {"projects": projects}


# ============================================
# CHAT SESSIONS ENDPOINT (placeholder)
# ============================================

@app.get("/api/chat/sessions")
@app.post("/api/chat/sessions")
async def list_chat_sessions():
    # Placeholder - return empty list
    return {"sessions": []}


@app.get("/api/chat/{session_id}/history")
async def get_chat_history(session_id: str):
    # Placeholder - chat history not implemented yet
    return {"session_id": session_id, "messages": []}


# ============================================
# PROBLEM RESOLVER ENDPOINT (placeholder)
# ============================================

class ProblemResolverRequest(BaseModel):
    session_id: str = ""
    app_path: str = ""
    commands: dict = {}
    run_mode: str = "diagnose-only"


@app.post("/api/agent/problem-resolver")
async def problem_resolver(req: ProblemResolverRequest):
    # Placeholder - problem resolver not implemented yet
    return {
        "status": "success",
        "runId": "placeholder-run-id",
        "message": "Problem resolver endpoint placeholder"
    }


# ============================================
# SESSION PERMISSIONS ENDPOINT (placeholder)
# ============================================

class SessionPermissionsRequest(BaseModel):
    session_id: str = ""
    permissions: dict = {}


@app.post("/api/session/permissions")
async def set_session_permissions(req: SessionPermissionsRequest):
    # Placeholder
    return {"status": "success", "permissions": req.permissions}


# ============================================
# PREVIEW / SANDBOX COMPATIBILITY ENDPOINTS
# ============================================

class PreviewRequest(BaseModel):
    app_path: str
    port: int = 3000
    session_duration: int = 3600


@app.post("/api/app/preview")
async def preview_app(req: PreviewRequest):
    candidate = Path(req.app_path).expanduser()
    if not candidate.exists():
        raise HTTPException(status_code=404, detail=f"Application path not found: {req.app_path}")
    app_path = _resolve_allowed_root(req.app_path)

    preview_url = f"http://localhost:{req.port}"
    session = session_manager.create_session(
        instance_id=f"preview-{app_path.name}",
        preview_url=preview_url,
        duration=req.session_duration,
        metadata={"app_path": str(app_path)},
    )

    return {
        "status": "success",
        "preview_url": preview_url,
        "raw_preview_url": preview_url,
        "secure_preview_url": session["preview_url"],
        "session_token": session["session_token"],
        "expires_at": session["expires_at"],
    }


@app.get("/api/sandbox/health")
async def sandbox_health():
    return {"status": "unavailable", "message": "Sandbox orchestrator not initialized"}


@app.get("/api/sandbox/instances")
async def list_sandbox_instances():
    return {"instances": [], "count": 0, "status": "unavailable"}


@app.get("/api/sessions/stats")
@app.get("/api/session/stats")
async def session_stats():
    stats = session_manager.get_stats()
    return {
        "total_sessions": stats.get("total_sessions", len(session_manager.sessions)),
        "active_sessions": stats.get("active_sessions", 0),
        **stats,
    }


@app.get("/api/app/download")
async def download_app(app_path: str):
    candidate = Path(app_path).expanduser()
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="Application path not found")
    source = _resolve_allowed_root(app_path)
    if not source.is_dir():
        raise HTTPException(status_code=404, detail="Application path not found")

    try:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for file_path in source.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(source))
        buffer.seek(0)

        filename = f"{source.name}.zip"
        return StreamingResponse(
            buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================
# APP LAUNCH ENDPOINT (placeholder)
# ============================================

class AppLaunchRequest(BaseModel):
    project_path: str = ""
    project_name: str = ""
    app_path: str = ""
    port: int = 3000


@app.post("/api/app/launch")
async def app_launch(req: AppLaunchRequest):
    raise HTTPException(status_code=503, detail="Sandbox orchestrator not available")


# ============================================
# TERMINAL WEBSOCKET
# ============================================

import asyncio

terminal_processes: dict = {}


def _terminate_process(proc: subprocess.Popen) -> None:
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
    except Exception:
        pass


@app.websocket("/api/term/{term_id}")
async def terminal_ws(websocket: WebSocket, term_id: str, cwd: str):
    try:
        safe_cwd = _resolve_allowed_root(cwd)
    except HTTPException as exc:
        await websocket.close(code=1008, reason=str(exc.detail))
        return
    if not safe_cwd.exists() or not safe_cwd.is_dir():
        await websocket.close(code=1008, reason="Terminal cwd does not exist")
        return

    await websocket.accept()
    proc = terminal_processes.get(term_id)
    if proc is None or proc.poll() is not None:
        shell_cmd = ["bash"] if os.name != "nt" else ["cmd.exe"]
        try:
            proc = subprocess.Popen(
                shell_cmd,
                cwd=str(safe_cwd),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as e:
            await websocket.send_text(f"ERROR: {e}")
            await websocket.close()
            return
        terminal_processes[term_id] = proc

    async def stream_output():
        loop = asyncio.get_event_loop()
        try:
            while True:
                if proc.stdout is None:
                    break
                line = await loop.run_in_executor(None, proc.stdout.readline)
                if not line:
                    break
                try:
                    await websocket.send_text(line)
                except Exception:
                    break
        finally:
            _terminate_process(proc)

    task = asyncio.create_task(stream_output())
    try:
        while True:
            try:
                data = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            if data == "__exit__":
                break
            if proc.stdin:
                proc.stdin.write(data + ("\n" if not data.endswith("\n") else ""))
                proc.stdin.flush()
    finally:
        task.cancel()
        _terminate_process(proc)
        terminal_processes.pop(term_id, None)


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
