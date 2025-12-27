"""
Sandbox orchestration service - manages isolated container execution
"""
import asyncio
import secrets
import shutil
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List
import docker
from docker.errors import DockerException, NotFound, APIError
import logging
import json
import shlex

logger = logging.getLogger(__name__)


class SandboxOrchestrator:
    """Manages sandboxed application instances with resource limits and security"""
    
    def __init__(
        self,
        docker_client: Optional[docker.DockerClient] = None,
        network_name: str = "appbuilder-sandbox",
        max_containers: int = 10,
        default_cpu_limit: float = 1.0,  # CPU cores
        default_memory_limit: str = "512m",
        default_timeout: int = 3600,  # 1 hour
        idle_timeout: int = 300,  # 5 minutes
    ):
        self.docker_client = docker_client or docker.from_env()
        self.network_name = network_name
        self.max_containers = max_containers
        self.default_cpu_limit = default_cpu_limit
        self.default_memory_limit = default_memory_limit
        self.default_timeout = default_timeout
        self.idle_timeout = idle_timeout
        
        # Active instances
        self.instances: Dict[str, Dict] = {}
        
        # Ensure sandbox network exists
        self._ensure_network()
    
    def _ensure_network(self):
        """Ensure Docker network exists with restricted configuration"""
        try:
            networks = self.docker_client.networks.list(names=[self.network_name])
            if not networks:
                logger.info(f"Creating sandbox network: {self.network_name}")
                self.docker_client.networks.create(
                    self.network_name,
                    driver="bridge",
                    internal=False,  # Allow external access for preview
                    options={
                        "com.docker.network.bridge.enable_icc": "true",
                        "com.docker.network.bridge.enable_ip_masquerade": "true",
                    }
                )
        except DockerException as e:
            logger.error(f"Failed to create network: {e}")
    
    async def launch_instance(
        self,
        app_path: str,
        instance_name: Optional[str] = None,
        port: int = 3000,
        cpu_limit: Optional[float] = None,
        memory_limit: Optional[str] = None,
        timeout: Optional[int] = None,
        environment: Optional[Dict[str, str]] = None,
        build_command: Optional[str] = None,
        run_command: Optional[str] = None,
        approved_commands: Optional[List[str]] = None,
        session_id: Optional[str] = None,
    ) -> Dict:
        """
        Launch a sandboxed application instance with command validation
        
        Args:
            app_path: Path to the application directory
            instance_name: Optional custom instance name
            port: Port to expose (default 3000)
            cpu_limit: CPU limit in cores (default from config)
            memory_limit: Memory limit (e.g., "512m", "1g")
            timeout: Max run time in seconds
            environment: Environment variables
            build_command: Optional build command (must be in approved_commands)
            run_command: Optional run command (must be in approved_commands)
            approved_commands: List of user-approved commands
            session_id: Session ID for tracking
        
        Returns:
            Instance details including preview URL, instance ID, expiry
        """
        # Check container limit
        if len(self.instances) >= self.max_containers:
            raise RuntimeError(f"Maximum containers ({self.max_containers}) reached. Stop an instance first.")
        
        # Generate instance ID
        instance_id = instance_name or f"sandbox-{secrets.token_hex(8)}"
        
        # Validate app path
        app_path_obj = Path(app_path).resolve()
        if not app_path_obj.exists():
            raise FileNotFoundError(f"Application path not found: {app_path}")
        
        # Security: Mask secrets in environment
        safe_env = self._mask_secrets(environment or {})
        
        # Resource limits
        cpu_limit = cpu_limit or self.default_cpu_limit
        memory_limit = memory_limit or self.default_memory_limit
        timeout = timeout or self.default_timeout
        
        # Calculate expiry
        expires_at = datetime.utcnow() + timedelta(seconds=timeout)
        
        try:
            # Build Docker image for the app
            image_name = f"{instance_id}:latest"
            logger.info(f"Building image for {instance_id}...")
            
            # Determine build context (monorepo-aware)
            context_dir = app_path_obj
            if not (app_path_obj / "package.json").exists() and (app_path_obj / "frontend" / "package.json").exists():
                context_dir = app_path_obj / "frontend"
            elif not (app_path_obj / "requirements.txt").exists() and (app_path_obj / "backend" / "requirements.txt").exists():
                context_dir = app_path_obj / "backend"

            # Detect Dockerfile or use default in the context directory
            dockerfile_path = context_dir / "Dockerfile"
            if not dockerfile_path.exists():
                # Create a default Dockerfile
                dockerfile_path = self._generate_dockerfile(context_dir, run_command)
            dockerfile_name = dockerfile_path.name

            # Detect intended container port by project type for correct mapping
            if (context_dir / "package.json").exists():
                container_port = 3000
            elif (context_dir / "requirements.txt").exists():
                container_port = 8000
            else:
                container_port = 3000
            
            # Build image
            build_log_lines = []
            try:
                image, build_logs = self.docker_client.images.build(
                    path=str(context_dir),
                    tag=image_name,
                    rm=True,
                    forcerm=True,
                    dockerfile=dockerfile_name,
                )
                
                # Capture build logs
                for log in build_logs:
                    if "stream" in log:
                        log_line = log["stream"].strip()
                        build_log_lines.append(log_line)
                        logger.debug(f"Build: {log_line}")
                    elif "error" in log:
                        error_line = log["error"].strip()
                        build_log_lines.append(f"ERROR: {error_line}")
                        logger.error(f"Build error: {error_line}")
                
                logger.info(f"Image built: {image_name}")
                
            except DockerException as build_error:
                # Capture error details
                error_msg = str(build_error)
                logger.error(f"Docker build failed: {error_msg}")

                # Attempt fallback for Node projects: dev server without build
                node_project = (context_dir / "package.json").exists()
                if node_project:
                    try:
                        logger.info("Falling back to dev-server Dockerfile (no build)...")
                        dev_dockerfile = context_dir / "Dockerfile.dev.generated"
                        dev_dockerfile.write_text(
                            """
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci || npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--port", "3000", "--host", "0.0.0.0"]
""".strip()
                        )
                        image, build_logs = self.docker_client.images.build(
                            path=str(context_dir),
                            tag=image_name,
                            rm=True,
                            forcerm=True,
                            dockerfile=dev_dockerfile.name,
                        )
                        build_log_lines.append("[fallback] built dev-server image")
                        container_port = 3000  # Ensure port aligns with dev server
                    except DockerException as dev_error:
                        # Log both errors and raise
                        err2 = str(dev_error)
                        logger.error(f"Fallback Docker build (dev server) failed: {err2}")
                        if build_log_lines:
                            logger.error("Last build logs:")
                            for line in build_log_lines[-20:]:
                                logger.error(f"  {line}")
                        detailed_error = (
                            f"Docker build failed: {error_msg}\nFallback (dev) failed: {err2}"
                        )
                        raise RuntimeError(detailed_error)
                else:
                    # Log the last 20 lines of build output for debugging
                    if build_log_lines:
                        logger.error("Last build logs:")
                        for line in build_log_lines[-20:]:
                            logger.error(f"  {line}")
                    # Create detailed error message
                    detailed_error = f"Docker build failed: {error_msg}"
                    if build_log_lines:
                        detailed_error += f"\n\nLast build output:\n" + "\n".join(build_log_lines[-10:])
                    raise RuntimeError(detailed_error)
            
            # Start container
            container = self.docker_client.containers.run(
                image_name,
                name=instance_id,
                detach=True,
                ports={f"{container_port}/tcp": None},  # Random host port for detected container port
                environment=safe_env,
                network=self.network_name,
                cpu_quota=int(cpu_limit * 100000),  # CPU limit
                mem_limit=memory_limit,
                restart_policy={"Name": "no"},
                labels={
                    "appbuilder.managed": "true",
                    "appbuilder.expires": expires_at.isoformat(),
                },
                # Security options
                security_opt=["no-new-privileges:true"],
                cap_drop=["ALL"],
                cap_add=["NET_BIND_SERVICE"],
            )
            
            logger.info(f"Container started: {instance_id}")
            
            # Get assigned port
            container.reload()
            port_bindings = container.attrs["NetworkSettings"]["Ports"]
            host_port = None
            if f"{container_port}/tcp" in port_bindings and port_bindings[f"{container_port}/tcp"]:
                host_port = port_bindings[f"{container_port}/tcp"][0]["HostPort"]
            
            # Generate preview URL
            preview_url = f"http://localhost:{host_port}" if host_port else None
            
            # Store instance info with command tracking
            self.instances[instance_id] = {
                "instance_id": instance_id,
                "container": container,
                "image": image_name,
                "app_path": str(app_path_obj),
                "port": port,
                "host_port": host_port,
                "preview_url": preview_url,
                "status": "running",
                "started_at": datetime.utcnow().isoformat() + "Z",
                "expires_at": expires_at.isoformat() + "Z",
                "cpu_limit": cpu_limit,
                "memory_limit": memory_limit,
                "build_logs": build_log_lines[:50],  # Keep last 50 lines
                "build_command": build_command,
                "run_command": run_command,
                "approved_commands": approved_commands or [],
                "session_id": session_id,
            }
            
            # Schedule cleanup
            asyncio.create_task(self._schedule_cleanup(instance_id, timeout))
            
            logger.info(f"Instance {instance_id} launched with commands: build={build_command}, run={run_command}")
            
            return {
                "instance_id": instance_id,
                "preview_url": preview_url,
                "status": "running",
                "started_at": self.instances[instance_id]["started_at"],
                "expires_at": self.instances[instance_id]["expires_at"],
                "logs_url": f"/api/sandbox/{instance_id}/logs",
                "port": host_port,
                "build_command": build_command,
                "run_command": run_command,
            }
            
        except RuntimeError as e:
            # Already formatted error from build failure
            logger.error(f"Failed to launch instance: {e}")
            await self._cleanup_instance(instance_id)
            raise
        except DockerException as e:
            logger.error(f"Failed to launch instance: {e}")
            # Cleanup on failure
            await self._cleanup_instance(instance_id)
            raise RuntimeError(f"Failed to launch sandbox: {str(e)}")
    
    async def stop_instance(self, instance_id: str, force: bool = False) -> Dict:
        """Stop a running instance"""
        if instance_id not in self.instances:
            raise ValueError(f"Instance not found: {instance_id}")
        
        instance = self.instances[instance_id]
        
        try:
            container = instance["container"]

            try:
                container.reload()
                container_status = container.status
            except DockerException:
                container_status = None

            already_stopped = container_status in {"exited", "dead", "created", "removing"}

            if not already_stopped:
                try:
                    if force:
                        container.kill()
                        logger.info(f"Forcefully killed container: {instance_id}")
                    else:
                        container.stop(timeout=10)
                        logger.info(f"Stopped container: {instance_id}")
                except APIError as e:
                    if e.status_code == 409 and "is not running" in str(e).lower():
                        already_stopped = True
                        logger.info(f"Container already stopped: {instance_id}")
                    else:
                        raise

            instance["status"] = "stopped"
            instance["stopped_at"] = datetime.utcnow().isoformat() + "Z"

            # Cleanup
            await self._cleanup_instance(instance_id)

            return {
                "success": True,
                "instance_id": instance_id,
                "status": "stopped",
                "message": "Instance already stopped" if already_stopped else "Instance stopped successfully"
            }

        except DockerException as e:
            logger.error(f"Failed to stop instance: {e}")
            return {
                "success": False,
                "instance_id": instance_id,
                "error": str(e)
            }
    
    async def get_instance_status(self, instance_id: str) -> Dict:
        """Get instance status and health"""
        if instance_id not in self.instances:
            raise ValueError(f"Instance not found: {instance_id}")
        
        instance = self.instances[instance_id]
        container = instance["container"]
        
        try:
            container.reload()
            status = container.status
            
            # Get resource usage stats
            stats = container.stats(stream=False)
            
            cpu_usage = self._calculate_cpu_percent(stats)
            memory_usage = stats["memory_stats"].get("usage", 0)
            memory_limit = stats["memory_stats"].get("limit", 0)
            memory_percent = (memory_usage / memory_limit * 100) if memory_limit > 0 else 0
            
            return {
                "instance_id": instance_id,
                "status": status,
                "health": "healthy" if status == "running" else "unhealthy",
                "preview_url": instance["preview_url"],
                "started_at": instance["started_at"],
                "expires_at": instance["expires_at"],
                "resources": {
                    "cpu_percent": round(cpu_usage, 2),
                    "memory_usage": f"{memory_usage / 1024 / 1024:.2f} MB",
                    "memory_percent": round(memory_percent, 2),
                },
            }
            
        except DockerException as e:
            logger.error(f"Failed to get instance status: {e}")
            return {
                "instance_id": instance_id,
                "status": "error",
                "health": "unhealthy",
                "error": str(e)
            }
    
    async def get_instance_logs(
        self,
        instance_id: str,
        tail: int = 100,
        follow: bool = False
    ) -> str:
        """Get instance logs"""
        if instance_id not in self.instances:
            raise ValueError(f"Instance not found: {instance_id}")
        
        instance = self.instances[instance_id]
        container = instance["container"]
        
        try:
            logs = container.logs(
                stdout=True,
                stderr=True,
                tail=tail,
                follow=follow,
                timestamps=True
            )
            
            if isinstance(logs, bytes):
                return logs.decode("utf-8")
            else:
                # Generator for streaming
                return "\n".join(line.decode("utf-8") for line in logs)
                
        except DockerException as e:
            logger.error(f"Failed to get logs: {e}")
            return f"Error retrieving logs: {str(e)}"
    
    def list_instances(self) -> List[Dict]:
        """List all active instances"""
        return [
            {
                "instance_id": inst_id,
                "status": inst["status"],
                "preview_url": inst["preview_url"],
                "started_at": inst["started_at"],
                "expires_at": inst["expires_at"],
            }
            for inst_id, inst in self.instances.items()
        ]
    
    async def cleanup_expired(self):
        """Clean up expired instances"""
        now = datetime.utcnow()
        expired = []
        
        for instance_id, instance in self.instances.items():
            expires_at = datetime.fromisoformat(instance["expires_at"].replace("Z", ""))
            if now > expires_at:
                expired.append(instance_id)
        
        for instance_id in expired:
            logger.info(f"Cleaning up expired instance: {instance_id}")
            await self.stop_instance(instance_id, force=True)
    
    async def _schedule_cleanup(self, instance_id: str, timeout: int):
        """Schedule automatic cleanup after timeout"""
        await asyncio.sleep(timeout)
        
        if instance_id in self.instances:
            logger.info(f"Timeout reached for instance: {instance_id}")
            await self.stop_instance(instance_id, force=True)
    
    async def _cleanup_instance(self, instance_id: str):
        """Clean up container and image"""
        if instance_id not in self.instances:
            return
        
        instance = self.instances[instance_id]
        
        try:
            # Remove container
            container = instance["container"]
            try:
                container.remove(force=True)
                logger.info(f"Removed container: {instance_id}")
            except NotFound:
                pass
            
            # Remove image
            image_name = instance["image"]
            try:
                self.docker_client.images.remove(image_name, force=True)
                logger.info(f"Removed image: {image_name}")
            except NotFound:
                pass
                
        except DockerException as e:
            logger.error(f"Cleanup error: {e}")
        finally:
            # Remove from instances
            del self.instances[instance_id]
    
    def _generate_dockerfile(self, app_path: Path, run_command: Optional[str] = None) -> Path:
        """Generate a basic Dockerfile if none exists"""
        # Detect project type
        if (app_path / "package.json").exists():
            # Node.js (Vite/React) project: build and serve with vite preview
            dockerfile_content = """
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci || npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview", "--", "--port", "3000", "--host", "0.0.0.0"]
"""
        elif (app_path / "requirements.txt").exists():
            # Python project
            cmd = run_command or "python main.py"
            cmd_args = shlex.split(cmd)
            dockerfile_content = f"""
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD {json.dumps(cmd_args)}
"""
        else:
            # Generic: serve current directory via a simple HTTP server so the preview shows something
            dockerfile_content = """
FROM python:3.11-slim
WORKDIR /app
COPY . .
EXPOSE 3000
CMD ["python", "-m", "http.server", "3000"]
"""
        
        dockerfile_path = app_path / "Dockerfile.generated"
        dockerfile_path.write_text(dockerfile_content.strip())
        return dockerfile_path
    
    def _mask_secrets(self, env: Dict[str, str]) -> Dict[str, str]:
        """Mask sensitive environment variables in logs"""
        sensitive_keys = ["API_KEY", "SECRET", "PASSWORD", "TOKEN", "PRIVATE"]
        masked = {}
        
        for key, value in env.items():
            if any(sk in key.upper() for sk in sensitive_keys):
                masked[key] = "***MASKED***"
            else:
                masked[key] = value
        
        return masked
    
    def _calculate_cpu_percent(self, stats: Dict) -> float:
        """Calculate CPU usage percentage"""
        try:
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                        stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                          stats["precpu_stats"]["system_cpu_usage"]
            
            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * len(stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [1])) * 100.0
                return cpu_percent
        except (KeyError, ZeroDivisionError):
            pass
        
        return 0.0
    
    async def health_check(self) -> Dict:
        """Health check for orchestrator"""
        try:
            # Check Docker daemon
            self.docker_client.ping()
            
            # Check network
            networks = self.docker_client.networks.list(names=[self.network_name])
            network_ok = len(networks) > 0
            
            return {
                "status": "healthy",
                "docker": "connected",
                "network": "ok" if network_ok else "missing",
                "active_instances": len(self.instances),
                "max_instances": self.max_containers,
            }
        except DockerException as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def shutdown(self):
        """Graceful shutdown - stop all instances"""
        logger.info("Shutting down sandbox orchestrator...")
        
        instance_ids = list(self.instances.keys())
        for instance_id in instance_ids:
            await self.stop_instance(instance_id, force=True)
        
        logger.info("All instances stopped")
