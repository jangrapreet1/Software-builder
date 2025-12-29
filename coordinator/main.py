"""
Main entry point for the Autonomous App-Building Platform Coordinator
"""
import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
import time
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST

from rich.console import Console
import re
import subprocess
import httpx
from urllib.parse import urljoin, urlencode, urlparse, parse_qsl
from http.cookies import SimpleCookie

ROOT_DIR = Path(__file__).resolve().parent.parent
# Ensure repo root is at the very front to avoid 'coordinator/services' shadowing top-level 'services'
try:
    root_str = str(ROOT_DIR)
    if root_str in sys.path:
        try:
            sys.path.remove(root_str)
        except ValueError:
            pass
    sys.path.insert(0, root_str)
except Exception:
    # Fallback to os.sys if needed
    if str(ROOT_DIR) not in os.sys.path:
        os.sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
# Load environment variables early
load_dotenv(dotenv_path=ROOT_DIR / ".env")

# Initialize console for rich output
console = Console()

from workflows.app_builder import AppBuilderWorkflow
from config.settings import Settings
from services.repository_detector import RepositoryDetector
from services.sandbox_orchestrator import SandboxOrchestrator
from services.session_manager import SessionManager
from services.permission_manager import PermissionManager
from services.build_registry import BuildRegistry
from services.audit_logger import audit_logger, AuditEventType
from services.run_audit_logger import RunAuditLogger
from services.agent_collaboration_manager import CollaborationManager, LivePreviewBridge
from services.metrics_collector import get_metrics_collector
from services.activity_notifier import subscribe as activity_subscribe, unsubscribe as activity_unsubscribe
from services.error_handler_middleware import add_error_handling
from api.chat_endpoints import router as chat_router, initialize_chat_metrics
from agents.problem_resolver_agent import ProblemResolverAgent
from agents.enhanced_problem_resolver import EnhancedProblemResolverAgent, RunMode
from agents.tester_agent import TesterAgent
# Enhanced features
try:
    from workflows.app_builder_enhanced import EnhancedAppBuilderWorkflow
    from api.enhanced_endpoints_v2 import (
        router as enhanced_router_v2,
        initialize_enhanced_services,
    )
    ENHANCED_FEATURES_AVAILABLE = True
    console.print("[green]✓ Enhanced features available[/green]")
except ImportError as e:
    console.print(f"[yellow]⚠ Enhanced features unavailable: {e}[/yellow]")
    ENHANCED_FEATURES_AVAILABLE = False

from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables


# Initialize FastAPI app
app = FastAPI(
    title="Autonomous App Builder - Coordinator",
    description="AI-driven platform for building web applications from project briefs",
    version="1.0.0",
    default_response_class=ORJSONResponse,
)

# Mount static files for React UI assets
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
_ui_dist = ROOT_DIR / "coordinator" / "ui" / "dist"
_ui_assets = _ui_dist / "assets"
if _ui_assets.exists():
    app.mount("/assets", StaticFiles(directory=str(_ui_assets)), name="assets")

# Serve UI endpoint
@app.get("/ui")
async def serve_ui():
    """Serve the React UI"""
    index_file = _ui_dist / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return Response("UI not found", status_code=404)

# Add enhanced error handling middleware
add_error_handling(app, debug=os.getenv("DEBUG", "false").lower() == "true")


# Include enhanced API router if available
if ENHANCED_FEATURES_AVAILABLE:
    try:
        app.include_router(enhanced_router_v2)
        console.print("[green]✓ Enhanced API endpoints registered[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠ Enhanced API registration failed: {e}[/yellow]")


# Register Chat API router
try:
    app.include_router(chat_router)
    console.print("[green]✓ Chat API endpoints registered[/green]")
except Exception as e:
    console.print(f"[yellow]⚠ Chat API registration failed: {e}[/yellow]")


# Load settings
settings = Settings()

# Add CORS middleware using settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
GENERATED_DIR = Path(settings.generated_apps_dir).resolve()
build_registry = BuildRegistry(REPO_ROOT)
build_registry.bootstrap_from_generated(GENERATED_DIR)
run_audit_logger = RunAuditLogger(str(REPO_ROOT / ".sb_artifacts"))
metrics_collector = get_metrics_collector()

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Prometheus metrics isolated to a custom registry to avoid duplicate registration on reload
prom_registry = CollectorRegistry()
app.state.prom_registry = prom_registry

REQUESTS = Counter(
    "http_requests_total",
    "total http requests",
    ["method", "endpoint", "status_code"],
    registry=prom_registry,
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "request duration seconds",
    ["method", "endpoint", "status_code"],
    buckets=(0.05, 0.1, 0.2, 0.5, 1, 2, 5),
    registry=prom_registry,
)
BUILDS_STARTED = Counter("appbuild_builds_started_total", "builds started", registry=prom_registry)
BUILDS_SUCCESS = Counter("appbuild_builds_success_total", "builds successful", registry=prom_registry)
BUILDS_FAILED = Counter("appbuild_builds_failed_total", "builds failed", registry=prom_registry)
BUILDS_ACTIVE = Gauge("appbuild_builds_active", "active builds", registry=prom_registry)
try:
    initialize_chat_metrics(app.state.prom_registry)
    console.print("[green]✓ Chat metrics initialized[/green]")
except Exception as e:
    console.print(f"[yellow]⚠ Chat metrics initialization failed: {e}[/yellow]")

@app.middleware("http")
async def _metrics_mw(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    method = request.method
    endpoint = request.url.path
    status = str(response.status_code)
    REQUESTS.labels(method=method, endpoint=endpoint, status_code=status).inc()
    LATENCY.labels(method=method, endpoint=endpoint, status_code=status).observe(elapsed)
    return response

# Track last preview token observed per client IP to assist alias routes when
# Referer and cookies are unavailable in some browsers or CSP settings.
LAST_PREVIEW_TOKEN_BY_IP: Dict[str, str] = {}
LAST_PREVIEW_TARGET_BY_IP: Dict[str, str] = {}

# Launch retry governance (per session_id)
LAUNCH_RETRY_STATE: Dict[str, Dict] = {}

# Initialize sandbox services
try:
    sandbox_orchestrator = SandboxOrchestrator(
        network_name=settings.docker_network,
        default_timeout=3600,
        idle_timeout=300,
    )
    session_manager = SessionManager(default_session_duration=3600)
    permission_manager = PermissionManager(default_expiry=3600)
    # Expose managers on app state for other routers/modules
    app.state.session_manager = session_manager
    app.state.permission_manager = permission_manager
    console.print("[green]✓ Sandbox orchestrator initialized[/green]")
except Exception as e:
    console.print(f"[yellow]⚠ Sandbox orchestrator unavailable: {e}[/yellow]")
    sandbox_orchestrator = None
    session_manager = None
    permission_manager = None
    app.state.session_manager = None
    app.state.permission_manager = None

# Initialize Phase 2 agents and managers
try:
    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=0.7,
        google_api_key=settings.google_api_key
    )
    problem_resolver = ProblemResolverAgent(llm, settings)
    enhanced_resolver = EnhancedProblemResolverAgent(llm, settings, sandbox_orchestrator)
    tester_agent = TesterAgent(llm, settings)
    collaboration_manager = CollaborationManager(settings)
    live_preview_bridge = LivePreviewBridge(sandbox_orchestrator, settings) if sandbox_orchestrator else None
    console.print("[green]✓ Phase 2 agents initialized (including enhanced resolver)[/green]")
except Exception as e:
    console.print(f"[yellow]⚠ Phase 2 agents unavailable: {e}[/yellow]")
    problem_resolver = None
    enhanced_resolver = None
    tester_agent = None
    collaboration_manager = None
    live_preview_bridge = None

# ================= Problem Resolver API =================
class ProblemResolverStartRequest(BaseModel):
    session_id: str
    app_path: str
    commands: Dict[str, List[str]] | None = None
    run_mode: str | None = "diagnose-only"


@limiter.limit(settings.rate_limit_problem_resolver)
@app.post("/api/agent/problem-resolver")
async def start_problem_resolver(req: ProblemResolverStartRequest, request: Request):
    if not enhanced_resolver:
        raise HTTPException(status_code=503, detail="Enhanced resolver not available")
    try:
        mode = RunMode.ATTEMPT_FIX if (req.run_mode or "").lower() == RunMode.ATTEMPT_FIX.value else RunMode.DIAGNOSE_ONLY
        run_id = await enhanced_resolver.start_resolver_run(
            session_id=req.session_id,
            app_path=req.app_path,
            commands=req.commands or {"build": [], "run": [], "test": []},
            run_mode=mode,
        )
        return {"status": "success", "runId": run_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/build/{build_id}")
async def build_websocket(websocket: WebSocket, build_id: str):
    await websocket.accept()
    try:
        while True:
            active_workflow = workflow if USE_FAKE_WORKFLOW else (enhanced_workflow if enhanced_workflow else workflow)
            status = await active_workflow.get_build_status(build_id)
            if status:
                await websocket.send_json(status)
            if status and status.get("status") in ["success", "failed"]:
                break
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass

@app.get("/api/agent/problem-resolver/{run_id}/result")
async def get_problem_resolver_result(run_id: str):
    if not enhanced_resolver:
        raise HTTPException(status_code=503, detail="Enhanced resolver not available")
    result = enhanced_resolver.get_run_result(run_id)
    if not result:
        return {"status": "not_found", "runId": run_id}
    return {"status": result.get("status", "unknown"), **result}


@app.get("/api/agent/problem-resolver/{run_id}/logs")
async def get_problem_resolver_logs(run_id: str):
    if not enhanced_resolver:
        raise HTTPException(status_code=503, detail="Enhanced resolver not available")
    logs = enhanced_resolver.get_run_logs(run_id)
    if logs is None:
        return Response(content="Run not found", media_type="text/plain", status_code=404)
    # Return plain text for easy viewing in browser
    text = "\n".join(logs)
    return Response(content=text, media_type="text/plain")


@app.get("/api/agent/problem-resolver/{run_id}/artifacts")
async def get_problem_resolver_artifacts(run_id: str):
    if not enhanced_resolver:
        raise HTTPException(status_code=503, detail="Enhanced resolver not available")
    try:
        artifacts = enhanced_resolver.get_run_artifacts(run_id)
        if artifacts is None:
            return JSONResponse(status_code=404, content={"status": "not_found", "runId": run_id})
        return {"status": "ok", "runId": run_id, "artifacts": artifacts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Optionally use a lightweight fake workflow for testing to avoid external calls
USE_FAKE_WORKFLOW = os.getenv("USE_FAKE_WORKFLOW", "").lower() in ("1", "true", "yes")

if USE_FAKE_WORKFLOW:
    class _FakeWorkflow:
        def __init__(self, registry: BuildRegistry):
            self._builds = {}
            self.build_registry = registry
            for record in self.build_registry.load_all():
                self._builds[record["build_id"]] = {
                    "build_id": record["build_id"],
                    "project_name": record.get("project_name", record["build_id"]),
                    "build_status": record.get("status", "success"),
                    "progress": int(record.get("progress", 100)),
                    "current_step": record.get("current_step", "Complete"),
                    "logs": record.get("logs", []),
                }

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
            self.build_registry.register_build({
                "build_id": bid,
                "project_name": project_name,
                "status": "success",
                "progress": 100,
                "current_step": "Complete",
                "app_url": self._builds[bid]["app_url"],
                "source_path": self._builds[bid]["source_path"],
            })
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
                record = self.build_registry.get(build_id)
                if record:
                    return {
                        "build_id": record["build_id"],
                        "status": record.get("status", "unknown"),
                        "progress": int(record.get("progress", 0)),
                        "current_step": record.get("current_step", ""),
                        "logs": record.get("logs", []),
                    }
                return None
            return {
                "build_id": build_id,
                "status": b["build_status"],
                "progress": b["progress"],
                "current_step": b["current_step"],
                "logs": b["logs"],
            }

        async def list_builds(self) -> list[dict]:
            combined = {record["build_id"]: record for record in self.build_registry.load_all()}
            for b_id, b in self._builds.items():
                combined[b_id] = {
                    "build_id": b_id,
                    "project_name": b.get("project_name", b_id),
                    "status": b.get("build_status", "building"),
                    "progress": b.get("progress", 0),
                    "source_path": b.get("source_path"),
                    "current_step": b.get("current_step", ""),
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
            if build_id in self._builds:
                del self._builds[build_id]
                self.build_registry.remove(build_id)
                return {"success": True, "message": "Build deleted"}
            if self.build_registry.remove(build_id):
                return {"success": True, "message": "Build deleted"}
            return {"success": False, "message": "Build not found"}

    workflow = _FakeWorkflow(build_registry)
else:
    # Initialize FIXED workflow
    from workflows.app_builder_fixed import AppBuilderWorkflowFixed
    workflow = AppBuilderWorkflowFixed(settings, build_registry)

# Initialize enhanced workflow if available and not in fake mode
enhanced_workflow = None
if ENHANCED_FEATURES_AVAILABLE and not USE_FAKE_WORKFLOW:
    try:
        enhanced_workflow = EnhancedAppBuilderWorkflow(settings)
        initialize_enhanced_services(enhanced_workflow, settings)
        console.print("[green]✓ Enhanced workflow initialized[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠ Enhanced workflow initialization failed: {e}[/yellow]")
        enhanced_workflow = None



class ProjectBrief(BaseModel):
    """Project brief input model"""
    description: str
    name: str = None
    requirements: list[str] = []
    preferred_backend: str | None = None
    preferred_frontend: str | None = None


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


class DetectionRequest(BaseModel):
    """Repository detection request"""
    repo_path: str


class PreviewRequest(BaseModel):
    """Preview request model"""
    app_path: str
    port: int = 3000
    session_duration: int = 3600


class LaunchRequest(BaseModel):
    """Launch sandbox instance request"""
    app_path: str
    port: int = 3000
    cpu_limit: float = 1.0
    memory_limit: str = "512m"
    timeout: int = 3600
    environment: dict = {}
    session_id: str | None = None


class StopRequest(BaseModel):
    """Stop instance request"""
    instance_id: str
    force: bool = False


class PermissionRequest(BaseModel):
    """Permission grant request"""
    session_id: str
    actions: list[str]
    commands: list[str]
    duration: int = 3600


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


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(app.state.prom_registry), media_type=CONTENT_TYPE_LATEST)


@limiter.limit(settings.rate_limit_build)
@app.post("/api/build", response_model=BuildResponse)
async def build_app(brief: ProjectBrief, request: Request):
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
        BUILDS_STARTED.inc()
        BUILDS_ACTIVE.inc()
        
        # Select active workflow. Tests set USE_FAKE_WORKFLOW=1 and patch `workflow`.
        active_workflow = (
            workflow
            if USE_FAKE_WORKFLOW
            else (enhanced_workflow if enhanced_workflow else workflow)
        )

        # Start the workflow. If using fake workflow, always call build_from_brief.
        if (not USE_FAKE_WORKFLOW) and enhanced_workflow and hasattr(enhanced_workflow, "start_build_from_brief"):
            result = await enhanced_workflow.start_build_from_brief(
                description=brief.description,
                name=brief.name,
                requirements=brief.requirements,
                preferred_backend=brief.preferred_backend,
                preferred_frontend=brief.preferred_frontend,
            )
        else:
            result = await active_workflow.build_from_brief(
                description=brief.description,
                name=brief.name,
                requirements=brief.requirements,
            )
        
        resp = BuildResponse(
            status=result["status"],
            build_id=result["build_id"],
            message=result["message"],
            app_url=result.get("app_url"),
            source_path=result.get("source_path"),
            logs=result.get("logs", [])
        )
        try:
            if (result.get("status") or "").lower() == "success":
                BUILDS_SUCCESS.inc()
        finally:
            BUILDS_ACTIVE.dec()
        return resp
        
    except Exception as e:
        try:
            BUILDS_FAILED.inc()
        finally:
            try:
                BUILDS_ACTIVE.dec()
            except Exception:
                pass
        console.print(f"[bold red]Error building app:[/bold red] {str(e)}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@limiter.limit(settings.rate_limit_read)
@app.get("/api/build/{build_id}/status", response_model=BuildStatus)
async def get_build_status(build_id: str, request: Request):
    """Get the status of a build"""
    try:
        active_workflow = workflow if USE_FAKE_WORKFLOW else (enhanced_workflow if enhanced_workflow else workflow)
        status = await active_workflow.get_build_status(build_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Build not found")
        
        return BuildStatus(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@limiter.limit(settings.rate_limit_read)
@app.get("/api/builds")
async def list_builds(request: Request):
    """List all builds"""
    try:
        active_workflow = workflow if USE_FAKE_WORKFLOW else (enhanced_workflow if enhanced_workflow else workflow)
        builds = await active_workflow.list_builds()
        return {"builds": builds}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@limiter.limit(settings.rate_limit_read)
@app.get("/api/generated/projects")
async def get_generated_projects(request: Request):
    """List projects available in the generated directory"""
    try:
        projects = []
        if GENERATED_DIR.exists():
            for entry in sorted(GENERATED_DIR.iterdir(), key=lambda p: p.name.lower()):
                if entry.is_dir():
                    stats = entry.stat()
                    projects.append({
                        "name": entry.name,
                        "path": str(entry.resolve()),
                        "created_at": datetime.utcfromtimestamp(stats.st_ctime).isoformat() + "Z",
                        "updated_at": datetime.utcfromtimestamp(stats.st_mtime).isoformat() + "Z",
                        "has_backend": (entry / "backend").exists(),
                        "has_frontend": (entry / "frontend").exists()
                    })
        return {"projects": projects}
    except Exception as e:
        console.print(f"[bold red]Error listing generated projects:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@limiter.limit(settings.rate_limit_write)
@app.delete("/api/build/{build_id}")
async def delete_build(build_id: str, request: Request):
    """Delete a build and its artifacts"""
    try:
        active_workflow = workflow if USE_FAKE_WORKFLOW else (enhanced_workflow if enhanced_workflow else workflow)
        result = await active_workflow.delete_build(build_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PHASE 1: SANDBOX ORCHESTRATION ENDPOINTS
# ============================================================================

@limiter.limit(settings.rate_limit_detect)
@app.post("/api/repo/detect")
async def detect_repository(payload: DetectionRequest, request: Request):
    """
    Auto-detect repository configuration, languages, frameworks, and commands.
    Returns a detection report for user approval. Persists report to .sb_artifacts/.
    """
    try:
        repo_path = Path(payload.repo_path)

        if not repo_path.is_absolute():
            repo_path = (REPO_ROOT / repo_path).resolve()
        else:
            repo_path = repo_path.resolve()
        
        console.print(f"[cyan]Detect request path:[/cyan] {repo_path} (exists={repo_path.exists()})")

        if not repo_path.exists():
            raise HTTPException(status_code=404, detail=f"Repository path not found: {repo_path}")
        
        detector = RepositoryDetector(str(repo_path))
        detection_report = detector.detect_all(persist=True)
        
        return {
            "status": "success",
            "detection_report": detection_report,
            "artifactPath": detection_report.get("artifactPath"),
            "message": "Repository detected successfully. Review and approve commands before execution."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        console.print(f"[bold red]Detection error:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/repo/detect/latest")
async def get_latest_detection(repo_path: str):
    """
    Get the latest detection report for a repository
    """
    try:
        repo_path_obj = Path(repo_path).resolve()
        
        if not repo_path_obj.exists():
            # Avoid 404s: return graceful error payload
            return {"error": "repo_not_found", "repo_path": repo_path}
        
        detector = RepositoryDetector(str(repo_path_obj))
        report = detector.get_latest_detection_report()
        
        if not report:
            # Avoid 404s: return graceful empty response
            return {"status": "success", "detection_report": None}
        
        return {
            "status": "success",
            "detection_report": report
        }
        
    except HTTPException:
        raise
    except Exception as e:
        console.print(f"[bold red]Error retrieving detection:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@limiter.limit(settings.rate_limit_write)
@app.post("/api/session/permissions")
async def grant_permissions(payload: PermissionRequest, request: Request):
    """
    Grant permissions for a session to perform actions.
    User must explicitly approve commands before they can be executed.
    """
    if not permission_manager:
        raise HTTPException(status_code=503, detail="Permission manager not available")
    
    try:
        permission = permission_manager.grant_permission(
            session_id=payload.session_id,
            actions=payload.actions,
            commands=payload.commands,
            duration=payload.duration,
        )
        
        # Audit log
        audit_logger.log_event(
            event_type=AuditEventType.COMMAND_APPROVED,
            details={
                "session_id": payload.session_id,
                "actions": payload.actions,
                "commands": payload.commands,
                "duration": payload.duration,
            },
            user=payload.session_id,
            success=True
        )
        
        return {
            "status": "success",
            "permission": permission,
            "message": "Permissions granted successfully"
        }
        
    except Exception as e:
        console.print(f"[bold red]Permission error:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@limiter.limit(settings.rate_limit_preview)
@app.post("/api/app/preview")
async def preview_app(preview: PreviewRequest, request: Request):
    """
    Prepare and return a secure preview URL with session token and expiry.
    This is a lightweight endpoint that creates a session without launching a container.
    """
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not available")
    
    try:
        app_path = Path(preview.app_path).resolve()
        
        if not app_path.exists():
            raise HTTPException(status_code=404, detail=f"Application path not found: {preview.app_path}")
        
        # For preview, we assume the app is already running or will be launched separately
        # Generate a preview URL placeholder
        preview_url = f"http://localhost:{preview.port}"
        
        # Create session
        session = session_manager.create_session(
            instance_id=f"preview-{app_path.name}",
            preview_url=preview_url,
            duration=preview.session_duration,
            metadata={"app_path": str(app_path)}
        )
        
        base = str(request.base_url).rstrip("/")
        secure_url = f"{base}/preview/bridge/?session={session['session_token']}"
        return {
            "status": "success",
            # Raw sandbox URL for opening in a new tab (button)
            "preview_url": preview_url,
            # Bridged URL for embedding in Live Preview iframe (HTTPS-safe)
            "secure_preview_url": secure_url,
            # Provide raw URL explicitly too
            "raw_preview_url": preview_url,
            "session_token": session["session_token"],
            "expires_at": session["expires_at"],
            "message": "Preview session created. Launch instance to start the application."
        }
        
    except Exception as e:
        console.print(f"[bold red]Preview error:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Live Preview Bridge (HTTPS-friendly proxy over the coordinator)
# ---------------------------------------------------------------------------
@app.api_route("/preview/bridge", methods=["GET"])
@app.api_route("/preview/bridge/{full_path:path}", methods=["GET"])
async def preview_bridge(request: Request, full_path: str = ""):
    """Proxy sandbox preview traffic via coordinator to avoid mixed content.

    Clients must provide ?session=<token>. We validate the session and forward the
    request to the underlying sandbox preview URL, preserving path and query.
    We also forward the session token to the target as a query parameter.
    """
    # Validate session
    token = request.query_params.get("session")
    if not token:
        # Try to extract from Referer for subresource requests
        referer = request.headers.get("referer") or request.headers.get("Referer")
        if referer:
            try:
                ref_q = dict(parse_qsl(urlparse(referer).query))
                token = ref_q.get("session")
            except Exception:
                token = None
    if not token:
        raise HTTPException(status_code=400, detail="Missing session token")
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not available")

    try:
        sess = session_manager.validate_session(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    target_base = sess.get("preview_url")
    if not target_base:
        raise HTTPException(status_code=500, detail="Session missing preview target")

    try:
        parsed_base = urlparse(target_base)
        host = parsed_base.hostname or ""
        if host not in (settings.preview_allowed_hosts or []):
            raise HTTPException(status_code=403, detail="Preview host not allowed")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid preview target URL")

    # Build target URL preserving path and query; ensure session is forwarded
    incoming_q = dict(request.query_params)
    # Remove bridge-level session to avoid duplication
    incoming_q.pop("session", None)
    # Forward token to target
    incoming_q["session"] = token

    # Construct path and query
    # Ensure target_base has no trailing slash issues
    if not target_base.endswith("/"):
        target_base += "/"
    target_url = urljoin(target_base, full_path)
    if incoming_q:
        target_url = f"{target_url}?{urlencode(incoming_q, doseq=True)}"

    # Record token by client IP for alias-route fallback
    try:
        if request.client and request.client.host:
            LAST_PREVIEW_TOKEN_BY_IP[request.client.host] = token
    except Exception:
        pass

    # Forward request to target
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            # Copy selected headers, avoid accept-encoding to prevent gzip transfer issues
            headers = {k: v for k, v in request.headers.items() if k.lower() in ("accept", "user-agent")}
            resp = await client.get(target_url, headers=headers)

            # Stream back response with original content-type
            excluded_headers = {
                "content-encoding",
                "transfer-encoding",
                "connection",
                "content-length",
                # Strip headers that block iframe embedding under the coordinator origin
                "x-frame-options",
                "content-security-policy",
                # COOP/COEP/CORP can break embedding and module loading inside iframe
                "cross-origin-opener-policy",
                "cross-origin-embedder-policy",
                "cross-origin-resource-policy",
            }
            response_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded_headers]

            content_type = resp.headers.get("content-type", "")
            # For HTML, rewrite absolute asset paths (src/href="/...") to go through bridge prefix
            if "text/html" in content_type.lower():
                try:
                    html = resp.text
                    # 0) Remove CSP meta tags that can block embedding
                    html = re.sub(r'<meta[^>]+http-equiv\s*=\s*[\"\']Content-Security-Policy[\"\'][^>]*>', '', html, flags=re.IGNORECASE)
                    # 1) Prefix absolute paths to route via bridge
                    html = re.sub(r'((?:src|href)\s*=\s*[\"\'])/(?!/)', '\\1/preview/bridge/', html)
                    # 1b) Rewrite absolute localhost URLs (http://localhost:PORT/...) to bridge
                    html = re.sub(
                        r'((?:src|href)\s*=\s*[\"\'])https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(?::\d+)?/',
                        r'\1/preview/bridge/',
                        html,
                        flags=re.IGNORECASE,
                    )
                    # 2) Ensure navigations and subresource loads carry session token, so page and assets work
                    def _add_session_param(url: str) -> str:
                        return url + ("&session=" + token if "?" in url else "?session=" + token)
                    # Add to href
                    html = re.sub(r'(href\s*=\s*[\"\']/preview/bridge/[^\"\']*)([\"\"])', lambda m: _add_session_param(m.group(1)) + m.group(2), html)
                    # Add to src
                    html = re.sub(r'(src\s*=\s*[\"\']/preview/bridge/[^\"\']*)(([\"\"]))', lambda m: _add_session_param(m.group(1)) + m.group(2), html)
                    # 2b) Make sure the Vite HMR client carries the session via the bridge
                    html = html.replace('src="/@vite/client"', f'src="/preview/bridge/@vite/client?session={token}"')
                    html = html.replace("src='/@vite/client'", f"src='/preview/bridge/@vite/client?session={token}'")
                    html = html.replace('href="/@vite/client"', f'href="/preview/bridge/@vite/client?session={token}"')
                    html = html.replace("href='/@vite/client'", f"href='/preview/bridge/@vite/client?session={token}'")
                    # Set a cookie so alias routes can retrieve session when Referer is absent.
                    # Use SameSite=None so it is sent from the preview iframe (third-party to the UI dev host).
                    resp_headers = dict(response_headers)
                    cookie = f"preview_session={token}; Path=/; SameSite=None; HttpOnly"
                    if request.url.scheme == "https":
                        cookie += "; Secure"
                    resp_headers["set-cookie"] = cookie
                    # Record token by client IP as an additional fallback
                    try:
                        if request.client and request.client.host:
                            LAST_PREVIEW_TOKEN_BY_IP[request.client.host] = token
                    except Exception:
                        pass
                    return Response(content=html, media_type="text/html", status_code=resp.status_code, headers=resp_headers)
                except Exception:
                    # Fallback to raw content
                    pass
            elif "text/css" in content_type.lower():
                try:
                    css = resp.text
                    # Rewrite url(/...) -> url(/preview/bridge/...?...session=token)
                    def _rewrite_css_url(m):
                        before = m.group(1)  # url(
                        path = m.group(2)    # leading '/...'
                        rest = m.group(3)    # closing ) or quote+)
                        # Prefix bridge and add session token
                        new = "/preview/bridge" + path
                        new = new + ("&session=" + token if "?" in new else "?session=" + token)
                        return f"{before}{new}{rest}"
                    css = re.sub(r"(url\(\s*[\'\"]?)(/(?!/)[^\)\'\"]*)([\'\"]?\s*\))", _rewrite_css_url, css)
                    return Response(content=css, media_type="text/css", status_code=resp.status_code, headers=dict(response_headers))
                except Exception:
                    pass
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(response_headers))
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Preview bridge upstream error: {str(e)}")


# ---------------------------------------------------------------------------
# Alias routes for common dev-server prefixes to keep requests inside bridge
# These rely on the iframe session. Extract token from query, cookies, or Referer.

def _get_preview_token(request: Request):
    # 1) Direct query param on the request
    token = request.query_params.get("session")
    if token:
        return token
    # 2) Cookie set by HTML bridge response
    cookie_header = request.headers.get("cookie") or request.headers.get("Cookie")
    if cookie_header:
        try:
            c = SimpleCookie()
            c.load(cookie_header)
            if "preview_session" in c:
                return c["preview_session"].value
        except Exception:
            pass
    # 3) Referer query (for subresource loads attaching the bridge page URL)
    referer = request.headers.get("referer") or request.headers.get("Referer")
    if referer:
        try:
            return dict(parse_qsl(urlparse(referer).query)).get("session")
        except Exception:
            return None
    # 4) Fallback to last token observed for this client IP
    try:
        if request.client and request.client.host:
            return LAST_PREVIEW_TOKEN_BY_IP.get(request.client.host)
    except Exception:
        pass
    return None
@app.get("/@{full_path:path}")
async def preview_bridge_at_prefix(request: Request, full_path: str):
    token = _get_preview_token(request)
    target_base = None
    if token and session_manager:
        try:
            sess = session_manager.validate_session(token)
            target_base = sess.get("preview_url")
        except ValueError:
            target_base = None
    if not target_base:
        try:
            client_ip = request.client.host if request.client else None
        except Exception:
            client_ip = None
        if client_ip:
            ip_token = LAST_PREVIEW_TOKEN_BY_IP.get(client_ip)
            if ip_token and session_manager:
                try:
                    sess2 = session_manager.validate_session(ip_token)
                    target_base = sess2.get("preview_url")
                except ValueError:
                    target_base = None
    if not target_base:
        raise HTTPException(status_code=400, detail="Missing preview target")
    if not target_base.endswith("/"):
        target_base += "/"
    target_url = urljoin(target_base, "@" + full_path)
    # Preserve original query string (e.g., ?v=, ?import)
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            headers = {k: v for k, v in request.headers.items() if k.lower() in ("accept", "user-agent")}
            resp = await client.get(target_url, headers=headers)
            excluded_headers = {
                "content-encoding",
                "transfer-encoding",
                "connection",
                "content-length",
                "x-frame-options",
                "content-security-policy",
                "cross-origin-opener-policy",
                "cross-origin-embedder-policy",
                "cross-origin-resource-policy",
            }
            response_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded_headers]
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(response_headers))
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Preview bridge upstream error: {str(e)}")


@app.get("/assets/{full_path:path}")
async def preview_bridge_assets(request: Request, full_path: str):
    token = _get_preview_token(request)
    target_base = None
    if token and session_manager:
        try:
            sess = session_manager.validate_session(token)
            target_base = sess.get("preview_url")
        except ValueError:
            target_base = None
    if not target_base:
        try:
            client_ip = request.client.host if request.client else None
        except Exception:
            client_ip = None
        if client_ip:
            target_base = LAST_PREVIEW_TARGET_BY_IP.get(client_ip)
    if not target_base:
        raise HTTPException(status_code=400, detail="Missing preview target")
    if not target_base.endswith("/"):
        target_base += "/"
    target_url = urljoin(target_base, "assets/" + full_path)
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            headers = {k: v for k, v in request.headers.items() if k.lower() in ("accept", "user-agent")}
            resp = await client.get(target_url, headers=headers)
            excluded_headers = {
                "content-encoding",
                "transfer-encoding",
                "connection",
                "content-length",
                "x-frame-options",
                "content-security-policy",
                "cross-origin-opener-policy",
                "cross-origin-embedder-policy",
                "cross-origin-resource-policy",
            }
            response_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded_headers]
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(response_headers))
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Preview bridge upstream error: {str(e)}")


@app.get("/src/{full_path:path}")
async def preview_bridge_src(request: Request, full_path: str):
    token = _get_preview_token(request)
    target_base = None
    if token and session_manager:
        try:
            sess = session_manager.validate_session(token)
            target_base = sess.get("preview_url")
        except ValueError:
            target_base = None
    if not target_base:
        try:
            client_ip = request.client.host if request.client else None
        except Exception:
            client_ip = None
        if client_ip:
            target_base = LAST_PREVIEW_TARGET_BY_IP.get(client_ip)
    if not target_base:
        raise HTTPException(status_code=400, detail="Missing preview target")
    if not target_base.endswith("/"):
        target_base += "/"
    target_url = urljoin(target_base, "src/" + full_path)
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            headers = {k: v for k, v in request.headers.items() if k.lower() in ("accept", "user-agent")}
            resp = await client.get(target_url, headers=headers)
            excluded_headers = {
                "content-encoding",
                "transfer-encoding",
                "connection",
                "content-length",
                "x-frame-options",
                "content-security-policy",
                "cross-origin-opener-policy",
                "cross-origin-embedder-policy",
                "cross-origin-resource-policy",
            }
            response_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded_headers]
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(response_headers))
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Preview bridge upstream error: {str(e)}")


@app.get("/node_modules/{full_path:path}")
async def preview_bridge_node_modules(request: Request, full_path: str):
    token = _get_preview_token(request)
    target_base = None
    if token and session_manager:
        try:
            sess = session_manager.validate_session(token)
            target_base = sess.get("preview_url")
        except ValueError:
            target_base = None
    if not target_base:
        try:
            client_ip = request.client.host if request.client else None
        except Exception:
            client_ip = None
        if client_ip:
            target_base = LAST_PREVIEW_TARGET_BY_IP.get(client_ip)
    if not target_base:
        raise HTTPException(status_code=400, detail="Missing preview target")
    if not target_base.endswith("/"):
        target_base += "/"
    target_url = urljoin(target_base, "node_modules/" + full_path)
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            headers = {k: v for k, v in request.headers.items() if k.lower() in ("accept", "user-agent", "accept-encoding")}
            resp = await client.get(target_url, headers=headers)
            excluded_headers = {
                "content-encoding",
                "transfer-encoding",
                "connection",
                "content-length",
                "x-frame-options",
                "content-security-policy",
                "cross-origin-opener-policy",
                "cross-origin-embedder-policy",
                "cross-origin-resource-policy",
            }
            response_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded_headers]
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(response_headers))
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Preview bridge upstream error: {str(e)}")


@app.get("/__vite_ping")
async def preview_bridge_vite_ping(request: Request):
    token = _get_preview_token(request)
    target_base = None
    if token and session_manager:
        try:
            sess = session_manager.validate_session(token)
            target_base = sess.get("preview_url")
        except ValueError:
            target_base = None
    if not target_base:
        try:
            client_ip = request.client.host if request.client else None
        except Exception:
            client_ip = None
        if client_ip:
            target_base = LAST_PREVIEW_TARGET_BY_IP.get(client_ip)
    if not target_base:
        raise HTTPException(status_code=400, detail="Missing preview target")
    if not target_base.endswith("/"):
        target_base += "/"
    target_url = urljoin(target_base, "__vite_ping")
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {k: v for k, v in request.headers.items() if k.lower() in ("accept", "user-agent")}
            resp = await client.get(target_url, headers=headers)
            excluded_headers = {
                "content-encoding",
                "transfer-encoding",
                "connection",
                "content-length",
                "x-frame-options",
                "content-security-policy",
            }
            response_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded_headers]
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(response_headers))
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Preview bridge upstream error: {str(e)}")


@app.get("/@fs/{full_path:path}")
async def preview_bridge_fs(request: Request, full_path: str):
    token = _get_preview_token(request)
    target_base = None
    if token and session_manager:
        try:
            sess = session_manager.validate_session(token)
            target_base = sess.get("preview_url")
        except ValueError:
            target_base = None
    if not target_base:
        try:
            client_ip = request.client.host if request.client else None
        except Exception:
            client_ip = None
        if client_ip:
            target_base = LAST_PREVIEW_TARGET_BY_IP.get(client_ip)
    if not target_base:
        raise HTTPException(status_code=400, detail="Missing preview target")
    if not target_base.endswith("/"):
        target_base += "/"
    target_url = urljoin(target_base, "@fs/" + full_path)
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {k: v for k, v in request.headers.items() if k.lower() in ("accept", "user-agent")}
            resp = await client.get(target_url, headers=headers)
            excluded_headers = {
                "content-encoding",
                "transfer-encoding",
                "connection",
                "content-length",
                "x-frame-options",
                "content-security-policy",
            }
            response_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded_headers]
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(response_headers))
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Preview bridge upstream error: {str(e)}")

@app.post("/api/app/launch")
async def launch_app(request: LaunchRequest, req: Request):
    """
    Launch a sandboxed application instance with resource limits.
    Returns preview URL, instance ID, expiry, and logs URL.
    Requires explicit permission grant via /api/session/permissions.
    """
    if not sandbox_orchestrator or not session_manager or not permission_manager:
        raise HTTPException(status_code=503, detail="Sandbox orchestrator not available")
    
    try:
        app_path = Path(request.app_path).resolve()
        
        if not app_path.exists():
            raise HTTPException(status_code=404, detail=f"Application path not found: {request.app_path}")
        
        # Generate session ID if not provided
        session_id = request.session_id or f"session-{app_path.name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Retry governance pre-check
        state = LAUNCH_RETRY_STATE.get(session_id, {"count": 0, "exhausted_until": 0})
        now = time.time()
        if state.get("exhausted_until", 0) > now:
            return JSONResponse(
                status_code=429,
                content={
                    "status": "retry_exhausted",
                    "message": "Auto-retry cooldown active. Please wait before launching again.",
                    "nextAllowedAt": datetime.utcfromtimestamp(state["exhausted_until"]).isoformat() + "Z",
                    "sessionId": session_id,
                },
            )
        
        # Check permission
        has_permission = permission_manager.has_permission(session_id, "allow_run")
        console.print(
            f"[yellow]Permission check for {session_id}: allow_run={has_permission}, stored={permission_manager.get_permission(session_id)}[/yellow]"
        )
        if not has_permission:
            # Get detection report to show required commands
            detector = RepositoryDetector(str(app_path))
            report = detector.get_latest_detection_report()
            
            required_commands = []
            if report:
                required_commands.extend(report.get("build_commands", {}).get("confident", []))
                required_commands.extend(report.get("run_commands", {}).get("confident", []))
            
            return JSONResponse(
                status_code=403,
                content={
                    "error": "permission_required",
                    "message": "Please grant permission to run builds/containers.",
                    "requiredCommands": required_commands,
                    "sessionId": session_id
                }
            )
        
        console.print(f"[bold green]Launching sandbox:[/bold green] {app_path.name}")
        
        # Get detection data for context
        detector = RepositoryDetector(str(app_path))
        detection_data = detector.get_latest_detection_report() or {}
        
        # Get approved commands
        approved_commands = permission_manager.get_approved_commands(session_id)
        
        # Extract build and run commands from detection or use defaults
        build_cmd = detection_data.get("build_commands", {}).get("confident", [])
        run_cmd = detection_data.get("run_commands", {}).get("confident", [])
        
        build_command = build_cmd[0] if build_cmd else None
        run_command = run_cmd[0] if run_cmd else None
        
        # Launch instance with command tracking
        auto_fix_meta = None
        try:
            instance = await sandbox_orchestrator.launch_instance(
                app_path=str(app_path),
                port=request.port,
                cpu_limit=request.cpu_limit,
                memory_limit=request.memory_limit,
                timeout=request.timeout,
                environment=request.environment,
                build_command=build_command,
                run_command=run_command,
                approved_commands=approved_commands,
                session_id=session_id,
            )
        except Exception as launch_err:
            err_msg = str(launch_err)
            # Attempt automated resolution on Docker build failures if permitted
            if (("Docker build failed" in err_msg) or ("Fallback (dev) failed" in err_msg)) and enhanced_resolver:
                if permission_manager.has_permission(session_id, "allow_agent_auto_fix"):
                    try:
                        resolution = await enhanced_resolver.analyze_and_resolve(
                            app_path=str(app_path),
                            error_logs=err_msg,
                            context={"session_id": session_id},
                            run_mode=RunMode.ATTEMPT_FIX,
                            timeout_seconds=240,
                        )
                        auto_fix_meta = {
                            "attempted": True,
                            "resolver_run_id": resolution.get("run_id"),
                            "resolution": {
                                "status": resolution.get("status"),
                                "issues_found": resolution.get("issues_found"),
                                "issues_resolved": resolution.get("issues_resolved"),
                            },
                            "resolver_logs_url": f"/api/agent/problem-resolver/{resolution.get('run_id')}/logs" if resolution.get("run_id") else None,
                        }
                        # Retry launch once after fixes
                        instance = await sandbox_orchestrator.launch_instance(
                            app_path=str(app_path),
                            port=request.port,
                            cpu_limit=request.cpu_limit,
                            memory_limit=request.memory_limit,
                            timeout=request.timeout,
                            environment=request.environment,
                            build_command=build_command,
                            run_command=run_command,
                            approved_commands=approved_commands,
                            session_id=session_id,
                        )
                    except Exception as retry_err:
                        raise HTTPException(
                            status_code=500,
                            detail=(
                                f"Auto-fix attempted but launch still failed: {str(retry_err)}. "
                                f"ResolverRunId={auto_fix_meta.get('resolver_run_id') if auto_fix_meta else None}"
                            ),
                        )
                else:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": "permission_required",
                            "message": "Grant 'allow_agent_auto_fix' to let the agent analyze and apply low-risk fixes, then retry launch.",
                            "requiredActions": ["allow_agent_auto_fix"],
                            "sessionId": session_id,
                        },
                    )
            else:
                # Non-build errors: bubble up
                raise
        
        # Create secure session with rich metadata
        session = session_manager.create_session(
            instance_id=instance["instance_id"],
            preview_url=instance["preview_url"],
            duration=request.timeout,
            metadata={"app_path": str(app_path)},
            build_id=None,  # Could link to a build workflow if applicable
            approved_commands=approved_commands,
            detection_data=detection_data,
        )
        
        # Audit log
        audit_logger.log_instance_launch(
            instance_id=instance["instance_id"],
            app_path=str(app_path),
            cpu_limit=request.cpu_limit,
            memory_limit=request.memory_limit,
            timeout=request.timeout,
        )
        
        audit_logger.log_session_created(
            session_token_prefix=session["session_token"],
            instance_id=instance["instance_id"],
            duration=request.timeout,
        )
        
        # Reset retry state on success
        LAUNCH_RETRY_STATE[session_id] = {"count": 0, "exhausted_until": 0}

        base = str(req.base_url).rstrip("/")
        secure_url = f"{base}/preview/bridge/?session={session['session_token']}"
        return {
            "status": "success",
            "instance_id": instance["instance_id"],
            # Raw sandbox URL for opening in a new tab (full page view)
            "preview_url": instance["preview_url"],
            # Bridged URL for embedding inside Live Preview iframe (same-origin)
            "secure_preview_url": secure_url,
            # Also expose raw URL explicitly for open-in-new-tab
            "raw_preview_url": instance["preview_url"],
            "session_token": session["session_token"],
            "expires_at": instance["expires_at"],
            "logs_url": instance["logs_url"],
            "port": instance["port"],
            "message": "Sandbox instance launched successfully",
            "session_id": session_id,
            "auto_fix_attempted": bool(auto_fix_meta and auto_fix_meta.get("attempted")),
            "resolver_run_id": (auto_fix_meta or {}).get("resolver_run_id"),
            "resolver_logs_url": (auto_fix_meta or {}).get("resolver_logs_url"),
        }
        
    except Exception as e:
        console.print(f"[bold red]Launch error:[/bold red] {str(e)}")
        # Update retry state
        try:
            sid = request.session_id or f"session-{Path(request.app_path).name}"
            st = LAUNCH_RETRY_STATE.get(sid, {"count": 0, "exhausted_until": 0})
            st["count"] = st.get("count", 0) + 1
            LAUNCH_RETRY_STATE[sid] = st
            RETRY_LIMIT = 2
            COOLDOWN_SECONDS = 15
            if st["count"] >= RETRY_LIMIT:
                st["exhausted_until"] = time.time() + COOLDOWN_SECONDS
                LAUNCH_RETRY_STATE[sid] = st
                return JSONResponse(
                    status_code=429,
                    content={
                        "status": "retry_exhausted",
                        "message": "Auto-retry limit reached. Please wait before retrying.",
                        "nextAllowedAt": datetime.utcfromtimestamp(st["exhausted_until"]).isoformat() + "Z",
                        "sessionId": sid,
                    },
                )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/app/stop")
async def stop_app(request: StopRequest):
    """
    Stop a running sandbox instance and revoke its sessions.
    """
    if not sandbox_orchestrator or not session_manager:
        raise HTTPException(status_code=503, detail="Sandbox orchestrator not available")
    
    try:
        # Stop instance
        result = await sandbox_orchestrator.stop_instance(
            instance_id=request.instance_id,
            force=request.force
        )
        
        # Revoke sessions
        revoked_count = session_manager.revoke_instance_sessions(request.instance_id)
        
        result["revoked_sessions"] = revoked_count
        if "status" not in result:
            result["status"] = "stopped" if result.get("success") else "unknown"
        
        # Audit log
        audit_logger.log_instance_stop(
            instance_id=request.instance_id,
            forced=request.force,
            reason="User requested" if not request.force else "Forced stop",
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        console.print(f"[bold red]Stop error:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/app/download")
async def download_app(app_path: str):
    """
    Stream a zip archive of the application repository.
    Respects .gitignore patterns.
    """
    try:
        from fastapi.responses import StreamingResponse
        import zipfile
        import io
        import fnmatch
        
        app_path_obj = Path(app_path).resolve()
        
        if not app_path_obj.exists():
            raise HTTPException(status_code=404, detail=f"Application path not found: {app_path}")
        
        # Read .gitignore patterns
        gitignore_patterns = []
        gitignore_file = app_path_obj / ".gitignore"
        if gitignore_file.exists():
            with open(gitignore_file, 'r') as f:
                gitignore_patterns = [
                    line.strip() for line in f
                    if line.strip() and not line.startswith('#')
                ]
        
        # Add common patterns to exclude
        gitignore_patterns.extend([
            "__pycache__",
            "*.pyc",
            ".git",
            "node_modules",
            ".env",
            "*.log",
        ])
        
        def should_exclude(file_path: Path) -> bool:
            """Check if file should be excluded based on gitignore patterns"""
            relative_path = str(file_path.relative_to(app_path_obj))
            for pattern in gitignore_patterns:
                if fnmatch.fnmatch(relative_path, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                    return True
            return False
        
        # Create zip in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in app_path_obj.rglob('*'):
                if file_path.is_file() and not should_exclude(file_path):
                    arcname = file_path.relative_to(app_path_obj.parent)
                    zip_file.write(file_path, arcname)
        
        zip_buffer.seek(0)
        
        app_name = app_path_obj.name
        filename = f"{app_name}.zip"
        
        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        console.print(f"[bold red]Download error:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sandbox/instances")
async def list_instances():
    """List all active sandbox instances"""
    if not sandbox_orchestrator:
        raise HTTPException(status_code=503, detail="Sandbox orchestrator not available")
    
    try:
        instances = sandbox_orchestrator.list_instances()
        return {"instances": instances, "count": len(instances)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sandbox/{instance_id}/status")
async def get_instance_status(instance_id: str):
    """Get status and health of a sandbox instance"""
    if not sandbox_orchestrator:
        raise HTTPException(status_code=503, detail="Sandbox orchestrator not available")
    
    try:
        status = await sandbox_orchestrator.get_instance_status(instance_id)
        return status
    except ValueError as e:
        # Avoid 404s: return graceful error payload
        return {"error": "instance_not_found", "instance_id": instance_id, "message": str(e)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sandbox/{instance_id}/logs")
async def get_instance_logs(instance_id: str, tail: int = 100):
    """Get logs from a sandbox instance"""
    if not sandbox_orchestrator:
        raise HTTPException(status_code=503, detail="Sandbox orchestrator not available")
    
    try:
        logs = await sandbox_orchestrator.get_instance_logs(instance_id, tail=tail)
        return {"instance_id": instance_id, "logs": logs}
    except ValueError as e:
        # Avoid 404s: return graceful error payload
        return {"error": "instance_not_found", "instance_id": instance_id, "message": str(e), "logs": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sandbox/health")
async def sandbox_health():
    """Health check for sandbox orchestrator"""
    if not sandbox_orchestrator:
        return {"status": "unavailable", "message": "Sandbox orchestrator not initialized"}
    
    try:
        health = await sandbox_orchestrator.health_check()
        return health
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/sessions/stats")
async def session_stats():
    """Get session manager statistics"""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not available")
    
    return session_manager.get_stats()


@app.get("/api/audit/recent")
async def get_recent_audit_events(limit: int = 50):
    """Get recent audit events"""
    events = audit_logger.get_recent_events(limit=limit)
    return {"events": events, "count": len(events)}


@app.get("/api/audit/stats")
async def get_audit_stats():
    """Get audit log statistics"""
    return audit_logger.get_stats()


@app.get("/api/audit/query")
async def query_audit_events(
    event_type: str = None,
    instance_id: str = None,
    limit: int = 100
):
    """Query audit events with filters"""
    try:
        event_type_enum = AuditEventType(event_type) if event_type else None
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid event_type: {event_type}")
    
    events = audit_logger.query_events(
        event_type=event_type_enum,
        instance_id=instance_id,
        limit=limit
    )
    
    return {"events": events, "count": len(events)}


@app.get("/api/audit/{run_id}")
async def get_run_audit(run_id: str):
    """Get audit log for a specific run"""
    log = run_audit_logger.get_run_log(run_id)
    if not log:
        raise HTTPException(status_code=404, detail=f"Run audit log not found: {run_id}")
    return {"runId": run_id, "log": log, "steps": len(log)}


@app.get("/api/audit/runs/list")
async def list_run_audits(limit: int = 50):
    """List recent run audits"""
    runs = run_audit_logger.list_runs(limit=limit)
    return {"runs": runs, "count": len(runs)}


# ============================================================================
# PHASE 2: PROBLEM RESOLUTION & TESTING ENDPOINTS
# ============================================================================

class ResolveRequest(BaseModel):
    """Problem resolution request"""
    app_path: str
    error_logs: str = None
    auto_fix: bool = True


class TestRequest(BaseModel):
    """Test execution request"""
    app_path: str
    test_type: str = "all"
    specific_tests: list[str] = []
    generate_missing: bool = True


class LivePreviewRequest(BaseModel):
    """Live preview creation request"""
    build_id: str
    app_path: str
    port: int = 3000
    auto_start: bool = True


@app.post("/api/resolve/analyze")
async def analyze_and_resolve_issues(request: ResolveRequest):
    """
    Analyze and automatically resolve code issues
    Phase 2: Autonomous problem resolution across 12+ error categories
    """
    if not problem_resolver:
        raise HTTPException(status_code=503, detail="Problem resolver not available")
    
    try:
        console.print(f"[bold green]Analyzing issues:[/bold green] {request.app_path}")
        
        result = await problem_resolver.analyze_and_resolve(
            app_path=request.app_path,
            error_logs=request.error_logs
        )
        
        # Log resolution
        audit_logger.log_event(
            event_type=AuditEventType.COMMAND_EXECUTED,
            details={
                "action": "problem_resolution",
                "app_path": request.app_path,
                "issues_found": result.get("issues_found", 0),
                "issues_resolved": result.get("issues_resolved", 0)
            },
            success=result.get("status") in ["success", "partial"]
        )
        
        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        console.print(f"[bold red]Resolution error:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test/run")
async def run_tests(request: TestRequest):
    """
    Run tests on-demand and return structured report
    Phase 2: Tester agent with structured test reports
    """
    if not tester_agent:
        raise HTTPException(status_code=503, detail="Tester agent not available")
    
    try:
        console.print(f"[bold green]Running tests:[/bold green] {request.app_path}")
        
        result = await tester_agent.run_tests(
            app_path=request.app_path,
            test_type=request.test_type,
            specific_tests=request.specific_tests if request.specific_tests else None,
            generate_missing=request.generate_missing
        )
        
        # Log test execution
        audit_logger.log_event(
            event_type=AuditEventType.COMMAND_EXECUTED,
            details={
                "action": "test_execution",
                "app_path": request.app_path,
                "test_type": request.test_type,
                "tests_run": result.get("summary", {}).get("total_tests", 0),
                "tests_passed": result.get("summary", {}).get("passed", 0),
                "tests_failed": result.get("summary", {}).get("failed", 0)
            },
            success=result.get("status") == "passed"
        )
        
        return result
        
    except Exception as e:
        console.print(f"[bold red]Test execution error:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/preview/create")
async def create_live_preview(request: LivePreviewRequest):
    """
    Create a live preview for a build
    Phase 2: Live preview bridge with temporary deployments
    """
    if not live_preview_bridge:
        raise HTTPException(status_code=503, detail="Live preview bridge not available")
    
    try:
        console.print(f"[bold green]Creating live preview:[/bold green] {request.build_id}")
        
        result = await live_preview_bridge.create_live_preview(
            build_id=request.build_id,
            app_path=request.app_path,
            port=request.port,
            auto_start=request.auto_start
        )
        
        return result
        
    except Exception as e:
        console.print(f"[bold red]Preview creation error:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/preview/{build_id}/update")
async def update_live_preview(build_id: str, app_path: str):
    """Update an existing live preview with new code"""
    if not live_preview_bridge:
        raise HTTPException(status_code=503, detail="Live preview bridge not available")
    
    try:
        result = await live_preview_bridge.update_preview(build_id, app_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/preview/{build_id}/stop")
async def stop_live_preview(build_id: str):
    """Stop a live preview"""
    if not live_preview_bridge:
        raise HTTPException(status_code=503, detail="Live preview bridge not available")
    
    try:
        result = await live_preview_bridge.stop_preview(build_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/preview/{build_id}/status")
async def get_preview_status(build_id: str):
    """Get status of a live preview"""
    if not live_preview_bridge:
        raise HTTPException(status_code=503, detail="Live preview bridge not available")
    
    status = live_preview_bridge.get_preview_status(build_id)
    if not status:
        raise HTTPException(status_code=404, detail="Preview not found")
    
    return status


@app.get("/api/preview/list")
async def list_previews():
    """List all active live previews"""
    if not live_preview_bridge:
        raise HTTPException(status_code=503, detail="Live preview bridge not available")
    
    previews = live_preview_bridge.get_all_previews()
    return {"previews": list(previews.values()), "count": len(previews)}


@app.get("/api/collaboration/sessions")
async def list_collaboration_sessions():
    """List all active collaboration sessions"""
    if not collaboration_manager:
        raise HTTPException(status_code=503, detail="Collaboration manager not available")
    
    sessions = collaboration_manager.get_all_active_sessions()
    return {"sessions": list(sessions.values()), "count": len(sessions)}


@app.get("/api/collaboration/history")
async def get_collaboration_history(limit: int = 50):
    """Get collaboration history between agents"""
    if not collaboration_manager:
        raise HTTPException(status_code=503, detail="Collaboration manager not available")
    
    history = collaboration_manager.get_collaboration_history(limit)
    return {"history": history, "count": len(history)}


# ============================================================================
# PHASE 2: ENHANCED PROBLEM RESOLVER ENDPOINTS
# ============================================================================

class ProblemResolverRequest(BaseModel):
    """Phase 2 Problem Resolver request"""
    session_id: str
    app_path: str
    commands: Dict[str, List[str]]  # {"build": [...], "run": [...], "test": [...]}
    run_mode: str = "diagnose-only"  # "diagnose-only" | "attempt-fix"


@app.post("/api/agent/problem-resolver")
async def start_problem_resolver(request: ProblemResolverRequest):
    """
    Start a Phase 2 compliant problem resolver run
    - Permission-first: stops before destructive operations
    - Non-destructive: uses auto/* branches
    - Returns runId for status polling
    """
    if not enhanced_resolver:
        raise HTTPException(status_code=503, detail="Enhanced problem resolver not available")
    
    try:
        # Validate run_mode
        try:
            run_mode = RunMode(request.run_mode)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid run_mode: {request.run_mode}")
        
        console.print(f"[bold green]Starting problem resolver:[/bold green] {request.session_id}")
        
        run_id = await enhanced_resolver.start_resolver_run(
            session_id=request.session_id,
            app_path=request.app_path,
            commands=request.commands,
            run_mode=run_mode
        )
        
        # Log event
        audit_logger.log_event(
            event_type=AuditEventType.COMMAND_EXECUTED,
            details={
                "action": "problem_resolver_started",
                "run_id": run_id,
                "session_id": request.session_id,
                "run_mode": request.run_mode
            },
            success=True
        )
        
        return {
            "status": "success",
            "runId": run_id,
            "statusUrl": f"/api/agent/problem-resolver/{run_id}/result",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        console.print(f"[bold red]Problem resolver error:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agent/problem-resolver/{run_id}/result")
async def get_problem_resolver_result(run_id: str):
    """
    Get the result of a problem resolver run
    Returns structured JSON with issues, fixes, PR links, preview URLs, etc.
    """
    if not enhanced_resolver:
        raise HTTPException(status_code=503, detail="Enhanced problem resolver not available")
    
    result = enhanced_resolver.get_run_result(run_id)
    if not result:
        return {"status": "not_found", "runId": run_id, "result": None}
    return result


@app.get("/api/agent/problem-resolver/{run_id}/logs")
async def get_problem_resolver_logs(run_id: str):
    """Get full logs for a problem resolver run"""
    if not enhanced_resolver:
        raise HTTPException(status_code=503, detail="Enhanced problem resolver not available")
    
    logs = enhanced_resolver.get_run_logs(run_id)
    if logs is None:
        return JSONResponse(status_code=200, content={"status": "not_found", "runId": run_id, "logs": []})
    return logs


# ============================================================================
# CONTEXT AND STATE ENDPOINTS (NEW)
# ============================================================================

@app.get("/api/session/{session_token}/context")
async def get_session_context(session_token: str):
    """Get full session context including metadata, commands, and agent outputs"""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not available")
    
    try:
        context = session_manager.get_session_context(session_token)
        
        if not context:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "status": "success",
            "context": context,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        console.print(f"[bold red]Error getting session context:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflow/{build_id}/state")
async def get_workflow_state(build_id: str):
    """Get persisted workflow state for a build"""
    try:
        if workflow and hasattr(workflow, 'load_state'):
            state = await workflow.load_state(build_id)
            
            if not state:
                raise HTTPException(status_code=404, detail="Workflow state not found")
            
            return {
                "status": "success",
                "build_id": build_id,
                "state": state,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        else:
            raise HTTPException(status_code=503, detail="Workflow state persistence not available")
            
    except HTTPException:
        raise
    except Exception as e:
        console.print(f"[bold red]Error loading workflow state:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/permissions/stats")
async def get_permissions_stats():
    """Get permission statistics"""
    if not permission_manager:
        raise HTTPException(status_code=503, detail="Permission manager not available")
    
    stats = permission_manager.get_stats()
    return {
        "status": "success",
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/api/collaboration/state/{state_key}")
async def get_collaboration_state(state_key: str):
    """Get a specific shared state document"""
    if not collaboration_manager:
        raise HTTPException(status_code=503, detail="Collaboration manager not available")
    
    try:
        state = await collaboration_manager.get_state(state_key)
        
        if not state:
            raise HTTPException(status_code=404, detail="State not found")
        
        return {
            "status": "success",
            "state": state,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        console.print(f"[bold red]Error getting collaboration state:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# OBSERVABILITY & METRICS ENDPOINTS
# ============================================================================

@app.get("/api/metrics")
async def get_metrics():
    """Get all collected metrics in JSON format"""
    try:
        metrics = metrics_collector.get_all_metrics()
        return {
            "status": "success",
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/prometheus")
async def get_prometheus_metrics():
    """Export metrics in Prometheus format"""
    from fastapi.responses import PlainTextResponse
    
    try:
        prometheus_data = metrics_collector.export_prometheus_format()
        return PlainTextResponse(
            content=prometheus_data,
            media_type="text/plain; version=0.0.4"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/performance")
async def get_performance_report():
    """Get comprehensive performance report"""
    try:
        report = metrics_collector.get_performance_report()
        return {
            "status": "success",
            "report": report,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/health")
async def get_system_health():
    """Get system health metrics"""
    try:
        health = metrics_collector.get_system_health()
        return {
            "status": "success",
            "health": health,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/registry/stats")
async def get_registry_stats():
    """Get build registry statistics"""
    try:
        stats = build_registry.get_stats()
        return {
            "status": "success",
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CRASH RECOVERY & STATE MANAGEMENT ENDPOINTS
# ============================================================================

class RecoveryRequest(BaseModel):
    """Build recovery request"""
    build_id: str
    resume_from_step: str = None


@app.post("/api/build/{build_id}/recover")
async def recover_build(build_id: str):
    """
    Recover a crashed or failed build from last checkpoint
    Uses enhanced state manager to restore build state and resume
    """
    try:
        # Check if enhanced workflow is available
        if not enhanced_workflow:
            raise HTTPException(
                status_code=503,
                detail="Enhanced workflow with crash recovery not available"
            )
        
        console.print(f"[bold cyan]Attempting to recover build:[/bold cyan] {build_id}")
        
        # Try to recover the build
        result = await enhanced_workflow.recover_build(build_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="No recoverable state found for this build"
            )
        
        return {
            "status": "success",
            "build_id": build_id,
            "recovered_state": result,
            "message": "Build state recovered successfully",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        # Normalize to 200 on errors for this endpoint
        return {"error": "detection_error"}
    except Exception as e:
        console.print(f"[bold red]Recovery error:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/build/{build_id}/resume")
async def resume_build(build_id: str, resume_from_step: str = None):
    """
    Resume a paused or failed build from a specific step
    """
    try:
        if not enhanced_workflow:
            raise HTTPException(
                status_code=503,
                detail="Enhanced workflow required for build resumption"
            )
        
        console.print(f"[bold cyan]Resuming build:[/bold cyan] {build_id}")
        
        result = await enhanced_workflow.resume_build(
            build_id=build_id,
            from_step=resume_from_step
        )
        
        return {
            "status": "success",
            "build_id": build_id,
            "result": result,
            "message": "Build resumed successfully",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        console.print(f"[bold red]Resume error:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/build/{build_id}/checkpoints")
async def get_build_checkpoints(build_id: str):
    """
    Get all available checkpoints for a build
    Shows recovery points and state history
    """
    try:
        if not enhanced_workflow:
            raise HTTPException(
                status_code=503,
                detail="Enhanced workflow required for checkpoint access"
            )
        
        checkpoints = await enhanced_workflow.get_build_checkpoints(build_id)
        
        if not checkpoints:
            raise HTTPException(
                status_code=404,
                detail="No checkpoints found for this build"
            )
        
        return {
            "status": "success",
            "build_id": build_id,
            "checkpoints": checkpoints,
            "count": len(checkpoints),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Background task to cleanup expired sessions and instances
@app.on_event("startup")
async def startup_cleanup_task():
    """Start background cleanup task"""
    async def cleanup_loop():
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                if sandbox_orchestrator:
                    await sandbox_orchestrator.cleanup_expired()
                if session_manager:
                    session_manager.cleanup_expired()
                if permission_manager:
                    permission_manager.cleanup_expired()
            except Exception as e:
                console.print(f"[yellow]Cleanup error: {e}[/yellow]")
    
    if sandbox_orchestrator and session_manager:
        asyncio.create_task(cleanup_loop())
        console.print("[green]✓ Cleanup task started[/green]")


@app.on_event("shutdown")
async def shutdown_sandbox():
    """Graceful shutdown of sandbox orchestrator"""
    if sandbox_orchestrator:
        console.print("[yellow]Shutting down sandbox orchestrator...[/yellow]")
        await sandbox_orchestrator.shutdown()
        console.print("[green]✓ Sandbox shut down gracefully[/green]")


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
    base = Path(root).resolve()
    target = (base / rel_path).resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(status_code=400, detail="Invalid path")
    return target


@app.get("/api/fs/list")
async def fs_list(root: str, path: str = "."):
    base = Path(root).resolve()
    target = _resolve_safe_path(root, path)
    # If root or target path does not exist, return empty directory listing instead of 404
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
        # Avoid 404s: return a graceful error payload
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


class SecretSetRequest(BaseModel):
    root: str
    key: str
    value: str
    filename: str = ".env"


@app.get("/api/secrets/list")
async def secrets_list(root: str, filename: str = ".env"):
    base = Path(root).resolve()
    env_file = _resolve_safe_path(root, filename)
    secrets: Dict[str, str] = {}
    if env_file.exists() and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if not line or line.strip().startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                secrets[k.strip()] = v.strip()
    return {"path": str(env_file.relative_to(base)), "secrets": secrets}


@app.post("/api/secrets/set")
async def secrets_set(req: SecretSetRequest):
    env_file = _resolve_safe_path(req.root, req.filename)
    existing: Dict[str, str] = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if not line or line.strip().startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()
    existing[req.key] = req.value
    lines = [f"{k}={v}" for k, v in existing.items()]
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "success"}


@app.post("/api/fs/rename")
async def fs_rename(req: FSRenameRequest):
    src = _resolve_safe_path(req.root, req.src)
    dest = _resolve_safe_path(req.root, req.dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dest)
    return {"status": "success"}


@app.delete("/api/fs/delete")
async def fs_delete(root: str, path: str):
    target = _resolve_safe_path(root, path)
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


class GitRepo(BaseModel):
    repo_path: str


class GitCommitRequest(BaseModel):
    repo_path: str
    message: str
    add_all: bool = True


class GitBranchRequest(BaseModel):
    repo_path: str
    name: str
    checkout: bool = True


class GitRemoteRequest(BaseModel):
    repo_path: str
    name: str
    url: str


class GitPullPushRequest(BaseModel):
    repo_path: str
    remote: str = "origin"
    branch: str = "main"
    set_upstream: bool = False


def _run_git(repo_path: str, args: list[str]) -> dict:
    repo = Path(repo_path).resolve()
    if not repo.exists():
        raise HTTPException(status_code=404, detail="Repository path not found")
    try:
        result = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, timeout=120)
        return {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Git not available")


@app.post("/api/git/init")
async def git_init(req: GitRepo):
    res = _run_git(req.repo_path, ["init"])
    return res


@app.get("/api/git/status")
async def git_status(repo_path: str):
    repo = Path(repo_path).resolve()
    if not repo.exists():
        # Graceful response instead of 404 when repo path doesn't exist
        return {"exit_code": 1, "stdout": "", "stderr": "Repository path not found"}
    res = _run_git(repo_path, ["status", "--porcelain", "-b"])
    return res


@app.post("/api/git/commit")
async def git_commit(req: GitCommitRequest):
    if req.add_all:
        _run_git(req.repo_path, ["add", "-A"])
    res = _run_git(req.repo_path, ["commit", "-m", req.message])
    return res


@app.post("/api/git/branch")
async def git_branch(req: GitBranchRequest):
    if req.checkout:
        res = _run_git(req.repo_path, ["checkout", "-B", req.name])
    else:
        res = _run_git(req.repo_path, ["branch", req.name])
    return res


@app.post("/api/git/remote")
async def git_remote(req: GitRemoteRequest):
    res = _run_git(req.repo_path, ["remote", "add", req.name, req.url])
    if res["exit_code"] != 0:
        res = _run_git(req.repo_path, ["remote", "set-url", req.name, req.url])
    return res


@app.post("/api/git/pull")
async def git_pull(req: GitPullPushRequest):
    res = _run_git(req.repo_path, ["pull", req.remote, req.branch, "--ff-only"])
    return res


@app.post("/api/git/push")
async def git_push(req: GitPullPushRequest):
    args = ["push", req.remote, req.branch]
    if req.set_upstream:
        args = ["push", "-u", req.remote, req.branch]
    res = _run_git(req.repo_path, args)
    return res


terminal_processes: Dict[str, subprocess.Popen] = {}


@app.websocket("/api/term/{term_id}")
async def terminal_ws(websocket: WebSocket, term_id: str, cwd: str):
    await websocket.accept()
    proc = terminal_processes.get(term_id)
    if proc is None or proc.poll() is not None:
        shell_cmd = ["bash"] if os.name != "nt" else ["cmd.exe"]
        try:
            proc = subprocess.Popen(
                shell_cmd,
                cwd=str(Path(cwd).resolve()),
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
            try:
                if proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass

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
        try:
            if proc.poll() is None:
                proc.terminate()
        except Exception:
            pass
        terminal_processes.pop(term_id, None)


@app.websocket("/ws/build/{build_id}")
async def build_progress_ws(websocket: WebSocket, build_id: str):
    """WebSocket that streams build status periodically to the client"""
    await websocket.accept()
    try:
        # Stream until completion or client disconnect
        while True:
            try:
                active_workflow = enhanced_workflow if enhanced_workflow else workflow
                status = await active_workflow.get_build_status(build_id)
            except Exception:
                status = None

            if status:
                try:
                    await websocket.send_json(status)
                except Exception:
                    break
                # Stop when finished
                st = (status.get("status") or "").lower()
                prog = int(status.get("progress", 0) or 0)
                if st in ("success", "failed", "error") or prog >= 100:
                    break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/api/build/{build_id}/activity")
async def get_build_activity(build_id: str, limit: int = 200, after: Optional[str] = None):
    """Return persisted agent activity events for a build."""
    try:
        if not enhanced_workflow:
            return {"status": "unavailable", "events": []}
        state = enhanced_workflow.state_manager.get_state(build_id) or {}
        events = state.get("agent_activity", [])
        if after:
            try:
                events = [e for e in events if e.get("timestamp", "") > after]
            except Exception:
                pass
        if limit and isinstance(limit, int) and limit > 0:
            events = events[-limit:]
        return {"status": "success", "build_id": build_id, "events": events}
    except Exception as e:
        return JSONResponse(status_code=200, content={"status": "error", "error": str(e), "events": []})


@app.websocket("/ws/agent-activity/{build_id}")
async def agent_activity_ws(websocket: WebSocket, build_id: str):
    """WebSocket that streams per-build agent activity events."""
    await websocket.accept()
    q = None
    try:
        if not enhanced_workflow:
            await websocket.send_json({"status": "unavailable"})
            return
        # Send recent backlog
        state = enhanced_workflow.state_manager.get_state(build_id) or {}
        for evt in (state.get("agent_activity", [])[-200:]):
            try:
                await websocket.send_json(evt)
            except Exception:
                break
        # Subscribe to live events
        q = activity_subscribe(build_id)
        while True:
            try:
                evt = await q.get()
                await websocket.send_json(evt)
            except WebSocketDisconnect:
                break
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        try:
            if q is not None:
                activity_unsubscribe(build_id, q)
            await websocket.close()
        except Exception:
            pass

collab_rooms: Dict[str, set[WebSocket]] = {}


@app.websocket("/api/collab/ws/{doc_id}")
async def collab_ws(websocket: WebSocket, doc_id: str):
    await websocket.accept()
    room = collab_rooms.setdefault(doc_id, set())
    room.add(websocket)
    try:
        while True:
            try:
                msg = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            dead = []
            for peer in room:
                if peer is websocket:
                    continue
                try:
                    await peer.send_text(msg)
                except Exception:
                    dead.append(peer)
            for d in dead:
                room.discard(d)
    finally:
        room.discard(websocket)


# Serve UI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

ui_path = Path(os.path.join(os.path.dirname(__file__), "ui"))
dist_path = ui_path / "dist"

# Mount assets if they exist (React build)
if dist_path.exists() and (dist_path / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(dist_path / "assets")), name="assets")

@app.get("/ui")
async def serve_ui():
    """Serve the testing UI (React App or Fallback)"""
    # Prefer built React app
    if dist_path.exists() and (dist_path / "index.html").exists():
        return FileResponse(str(dist_path / "index.html"))
    
    # Fallback to simple UI
    if ui_path.exists() and (ui_path / "index.html").exists():
        return FileResponse(str(ui_path / "index.html"))
    
    return Response("UI not found", status_code=404)


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

    # Resolve TLS certificate paths from environment (optional for HTTPS)
    cert_env = os.getenv("COORDINATOR_CERT_FILE")
    key_env = os.getenv("COORDINATOR_KEY_FILE")

    def _resolve_abs(path_str):
        if not path_str:
            return None
        p = Path(path_str)
        if not p.is_absolute():
            p = (ROOT_DIR / p).resolve()
        return str(p)

    cert_file = _resolve_abs(cert_env)
    key_file = _resolve_abs(key_env)
    use_ssl = bool(cert_file and key_file and Path(cert_file).exists() and Path(key_file).exists())
    if use_ssl:
        console.print(f"[green]✓ TLS enabled[/green] cert={cert_file}")
    else:
        console.print("[yellow]⚠ TLS not enabled (cert/key not set or not found) — serving HTTP[/yellow]")

    # Simple uvicorn configuration without problematic parameters
    # Disable reload to avoid file system loop errors with node_modules symlinks
    # Alternative: Use reload with exclusions if you need hot-reload during development
    uvicorn.run(
        "coordinator.main:app",
        host=settings.coordinator_host,
        port=settings.coordinator_port,
        reload=False,  # Set to True for dev, False for production
        reload_excludes=["**/node_modules/**", "**/generated/**", "**/.git/**"] if False else None,
        log_level="info",
        ssl_certfile=cert_file if use_ssl else None,
        ssl_keyfile=key_file if use_ssl else None,
    )
