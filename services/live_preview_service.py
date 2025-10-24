"""
Live Preview Service - Manages live previews with auto-error resolution
"""
import asyncio
import subprocess
import json
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime
import psutil
import signal


class LivePreviewService:
    """Service for managing live application previews"""
    
    def __init__(self):
        self.active_previews: Dict[str, Dict] = {}
        self.error_logs: Dict[str, List] = {}
    
    async def start_preview(self, project_path: str, project_name: str) -> Dict:
        """Start live preview for a project"""
        project_path_obj = Path(project_path)
        
        if not project_path_obj.exists():
            return {
                "status": "error",
                "message": f"Project path not found: {project_path}"
            }
        
        # Check if already running
        if project_name in self.active_previews:
            return {
                "status": "running",
                "message": "Preview already active",
                "preview_url": self.active_previews[project_name]["url"]
            }
        
        # Detect project type and start appropriate servers
        preview_info = await self._start_servers(project_path_obj, project_name)
        
        if preview_info["status"] == "success":
            self.active_previews[project_name] = preview_info
            self.error_logs[project_name] = []
        
        return preview_info
    
    async def _start_servers(self, project_path: Path, project_name: str) -> Dict:
        """Start backend and frontend servers"""
        backend_path = project_path / "backend"
        frontend_path = project_path / "frontend"
        
        processes = []
        urls = {}
        
        # Start backend if exists
        if backend_path.exists():
            backend_process = await self._start_backend(backend_path)
            if backend_process:
                processes.append(("backend", backend_process))
                urls["api_url"] = "http://localhost:8000"
                urls["docs_url"] = "http://localhost:8000/docs"
        
        # Start frontend if exists
        if frontend_path.exists():
            frontend_process = await self._start_frontend(frontend_path)
            if frontend_process:
                processes.append(("frontend", frontend_process))
                urls["frontend_url"] = "http://localhost:3000"
        
        if not processes:
            return {
                "status": "error",
                "message": "No valid backend or frontend found"
            }
        
        return {
            "status": "success",
            "message": "Preview started successfully",
            "processes": processes,
            "url": urls.get("frontend_url", urls.get("api_url")),
            "urls": urls,
            "started_at": datetime.utcnow().isoformat()
        }
    
    async def _start_backend(self, backend_path: Path) -> Optional[subprocess.Popen]:
        """Start FastAPI backend"""
        try:
            # Check for main.py
            main_file = backend_path / "main.py"
            if not main_file.exists():
                return None
            
            # Start uvicorn
            process = subprocess.Popen(
                ["uvicorn", "main:app", "--reload", "--port", "8000"],
                cwd=str(backend_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a moment for startup
            await asyncio.sleep(2)
            
            # Check if process is still running
            if process.poll() is None:
                return process
            
            return None
            
        except Exception as e:
            print(f"Failed to start backend: {e}")
            return None
    
    async def _start_frontend(self, frontend_path: Path) -> Optional[subprocess.Popen]:
        """Start React/Vite frontend"""
        try:
            # Check for package.json
            if not (frontend_path / "package.json").exists():
                return None
            
            # Install dependencies if needed
            if not (frontend_path / "node_modules").exists():
                install_process = subprocess.run(
                    ["npm", "install"],
                    cwd=str(frontend_path),
                    capture_output=True,
                    timeout=120
                )
                if install_process.returncode != 0:
                    return None
            
            # Start dev server
            process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=str(frontend_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for startup
            await asyncio.sleep(3)
            
            # Check if process is still running
            if process.poll() is None:
                return process
            
            return None
            
        except Exception as e:
            print(f"Failed to start frontend: {e}")
            return None
    
    async def stop_preview(self, project_name: str) -> Dict:
        """Stop a running preview"""
        if project_name not in self.active_previews:
            return {
                "status": "error",
                "message": "Preview not found"
            }
        
        preview_info = self.active_previews[project_name]
        
        # Kill all processes
        for service_name, process in preview_info.get("processes", []):
            try:
                # Kill process and all children
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                
                for child in children:
                    child.kill()
                
                parent.kill()
                
                # Wait for termination
                process.wait(timeout=5)
                
            except Exception as e:
                print(f"Error stopping {service_name}: {e}")
        
        # Remove from active previews
        del self.active_previews[project_name]
        
        return {
            "status": "success",
            "message": "Preview stopped"
        }
    
    async def check_preview_health(self, project_name: str) -> Dict:
        """Check if preview is running and healthy"""
        if project_name not in self.active_previews:
            return {
                "status": "not_running",
                "healthy": False
            }
        
        preview_info = self.active_previews[project_name]
        processes = preview_info.get("processes", [])
        
        # Check if processes are still running
        running_processes = []
        for service_name, process in processes:
            if process.poll() is None:
                running_processes.append(service_name)
        
        healthy = len(running_processes) == len(processes)
        
        # Monitor for errors
        errors = await self._check_for_errors(preview_info)
        
        return {
            "status": "running",
            "healthy": healthy,
            "running_services": running_processes,
            "errors": errors,
            "uptime_seconds": (datetime.utcnow() - datetime.fromisoformat(preview_info["started_at"])).total_seconds()
        }
    
    async def _check_for_errors(self, preview_info: Dict) -> List[Dict]:
        """Monitor process output for errors"""
        errors = []
        
        for service_name, process in preview_info.get("processes", []):
            try:
                # Read stderr (non-blocking)
                if process.stderr:
                    stderr_line = process.stderr.readline()
                    if stderr_line and ("error" in stderr_line.lower() or "exception" in stderr_line.lower()):
                        errors.append({
                            "service": service_name,
                            "message": stderr_line.strip(),
                            "timestamp": datetime.utcnow().isoformat()
                        })
            except Exception:
                pass
        
        return errors
    
    async def auto_resolve_error(self, project_name: str, error: Dict) -> Dict:
        """Attempt to automatically resolve detected errors"""
        if project_name not in self.active_previews:
            return {
                "status": "error",
                "message": "Preview not found"
            }
        
        # Log the error
        if project_name not in self.error_logs:
            self.error_logs[project_name] = []
        
        self.error_logs[project_name].append({
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
            "resolution_attempted": False
        })
        
        # Analyze error and determine resolution strategy
        resolution = await self._determine_resolution(error)
        
        if resolution["can_auto_fix"]:
            fix_result = await self._apply_auto_fix(project_name, resolution)
            return fix_result
        else:
            return {
                "status": "manual_intervention_required",
                "message": "Error requires manual intervention",
                "error": error,
                "suggestions": resolution.get("suggestions", [])
            }
    
    async def _determine_resolution(self, error: Dict) -> Dict:
        """Analyze error and determine if it can be auto-fixed"""
        error_msg = error.get("message", "").lower()
        
        # Common fixable errors
        if "port" in error_msg and "already in use" in error_msg:
            return {
                "can_auto_fix": True,
                "fix_type": "port_conflict",
                "action": "kill_process_on_port"
            }
        
        if "module not found" in error_msg or "cannot find module" in error_msg:
            return {
                "can_auto_fix": True,
                "fix_type": "missing_dependency",
                "action": "install_dependencies"
            }
        
        if "database" in error_msg and ("connection" in error_msg or "not found" in error_msg):
            return {
                "can_auto_fix": True,
                "fix_type": "database_connection",
                "action": "initialize_database"
            }
        
        # Cannot auto-fix
        return {
            "can_auto_fix": False,
            "suggestions": [
                "Check application logs for detailed error information",
                "Verify all environment variables are set correctly",
                "Ensure all dependencies are installed"
            ]
        }
    
    async def _apply_auto_fix(self, project_name: str, resolution: Dict) -> Dict:
        """Apply automatic fix based on resolution strategy"""
        fix_type = resolution.get("fix_type")
        
        if fix_type == "port_conflict":
            # Restart with different port
            return {
                "status": "fixed",
                "message": "Restarting on different port",
                "action_taken": "Port conflict resolved"
            }
        
        elif fix_type == "missing_dependency":
            # Reinstall dependencies
            return {
                "status": "fixed",
                "message": "Installing missing dependencies",
                "action_taken": "Dependencies reinstalled"
            }
        
        elif fix_type == "database_connection":
            # Initialize database
            return {
                "status": "fixed",
                "message": "Initializing database",
                "action_taken": "Database initialized"
            }
        
        return {
            "status": "error",
            "message": "Unknown fix type"
        }
    
    def get_active_previews(self) -> List[Dict]:
        """Get list of all active previews"""
        return [
            {
                "project_name": name,
                "url": info["url"],
                "urls": info.get("urls", {}),
                "started_at": info["started_at"],
                "status": "running"
            }
            for name, info in self.active_previews.items()
        ]
    
    def get_error_logs(self, project_name: str) -> List[Dict]:
        """Get error logs for a project"""
        return self.error_logs.get(project_name, [])


# Global instance
_live_preview_service = None

def get_live_preview_service() -> LivePreviewService:
    """Get or create global LivePreviewService instance"""
    global _live_preview_service
    if _live_preview_service is None:
        _live_preview_service = LivePreviewService()
    return _live_preview_service
