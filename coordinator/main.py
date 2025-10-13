"""
Main entry point for the Autonomous App-Building Platform Coordinator
"""
import os
import asyncio
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from rich.console import Console

from workflows.app_builder import AppBuilderWorkflow
from config.settings import Settings
from services.repository_detector import RepositoryDetector
from services.sandbox_orchestrator import SandboxOrchestrator
from services.session_manager import SessionManager
from services.permission_manager import PermissionManager
from services.audit_logger import audit_logger, AuditEventType

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

# Initialize sandbox services
try:
    sandbox_orchestrator = SandboxOrchestrator(
        network_name=settings.docker_network,
        default_timeout=3600,
        idle_timeout=300,
    )
    session_manager = SessionManager(default_session_duration=3600)
    permission_manager = PermissionManager(default_expiry=3600)
    console.print("[green]✓ Sandbox orchestrator initialized[/green]")
except Exception as e:
    console.print(f"[yellow]⚠ Sandbox orchestrator unavailable: {e}[/yellow]")
    sandbox_orchestrator = None
    session_manager = None
    permission_manager = None

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


# ============================================================================
# PHASE 1: SANDBOX ORCHESTRATION ENDPOINTS
# ============================================================================

@app.post("/api/repo/detect")
async def detect_repository(request: DetectionRequest):
    """
    Auto-detect repository configuration, languages, frameworks, and commands.
    Returns a detection report for user approval. Persists report to .sb_artifacts/.
    """
    try:
        repo_path = Path(request.repo_path).resolve()
        
        if not repo_path.exists():
            raise HTTPException(status_code=404, detail=f"Repository path not found: {request.repo_path}")
        
        detector = RepositoryDetector(str(repo_path))
        detection_report = detector.detect_all(persist=True)
        
        return {
            "status": "success",
            "detection_report": detection_report,
            "artifactPath": detection_report.get("artifactPath"),
            "message": "Repository detected successfully. Review and approve commands before execution."
        }
        
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
            raise HTTPException(status_code=404, detail=f"Repository path not found: {repo_path}")
        
        detector = RepositoryDetector(str(repo_path_obj))
        report = detector.get_latest_detection_report()
        
        if not report:
            raise HTTPException(status_code=404, detail="No detection report found")
        
        return {
            "status": "success",
            "detection_report": report
        }
        
    except HTTPException:
        raise
    except Exception as e:
        console.print(f"[bold red]Error retrieving detection:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/session/permissions")
async def grant_permissions(request: PermissionRequest):
    """
    Grant permissions for a session to perform actions.
    User must explicitly approve commands before they can be executed.
    """
    if not permission_manager:
        raise HTTPException(status_code=503, detail="Permission manager not available")
    
    try:
        permission = permission_manager.grant_permission(
            session_id=request.session_id,
            actions=request.actions,
            commands=request.commands,
            duration=request.duration
        )
        
        # Audit log
        audit_logger.log_event(
            event_type=AuditEventType.COMMAND_APPROVED,
            details={
                "session_id": request.session_id,
                "actions": request.actions,
                "commands": request.commands,
                "duration": request.duration
            },
            user=request.session_id,
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


@app.post("/api/app/preview")
async def preview_app(request: PreviewRequest):
    """
    Prepare and return a secure preview URL with session token and expiry.
    This is a lightweight endpoint that creates a session without launching a container.
    """
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not available")
    
    try:
        app_path = Path(request.app_path).resolve()
        
        if not app_path.exists():
            raise HTTPException(status_code=404, detail=f"Application path not found: {request.app_path}")
        
        # For preview, we assume the app is already running or will be launched separately
        # Generate a preview URL placeholder
        preview_url = f"http://localhost:{request.port}"
        
        # Create session
        session = session_manager.create_session(
            instance_id=f"preview-{app_path.name}",
            preview_url=preview_url,
            duration=request.session_duration,
            metadata={"app_path": str(app_path)}
        )
        
        return {
            "status": "success",
            "preview_url": session["preview_url"],
            "session_token": session["session_token"],
            "expires_at": session["expires_at"],
            "message": "Preview session created. Launch instance to start the application."
        }
        
    except Exception as e:
        console.print(f"[bold red]Preview error:[/bold red] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/app/launch")
async def launch_app(request: LaunchRequest):
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
        session_id = f"session-{app_path.name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Check permission
        if not permission_manager.has_permission(session_id, "allow_run"):
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
        
        # Launch instance
        instance = await sandbox_orchestrator.launch_instance(
            app_path=str(app_path),
            port=request.port,
            cpu_limit=request.cpu_limit,
            memory_limit=request.memory_limit,
            timeout=request.timeout,
            environment=request.environment,
        )
        
        # Create secure session
        session = session_manager.create_session(
            instance_id=instance["instance_id"],
            preview_url=instance["preview_url"],
            duration=request.timeout,
            metadata={"app_path": str(app_path)}
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
        
        return {
            "status": "success",
            "instance_id": instance["instance_id"],
            "preview_url": instance["preview_url"],
            "secure_preview_url": session["preview_url"],
            "session_token": session["session_token"],
            "expires_at": instance["expires_at"],
            "logs_url": instance["logs_url"],
            "port": instance["port"],
            "message": "Sandbox instance launched successfully"
        }
        
    except Exception as e:
        console.print(f"[bold red]Launch error:[/bold red] {str(e)}")
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
        raise HTTPException(status_code=404, detail=str(e))
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
        raise HTTPException(status_code=404, detail=str(e))
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
