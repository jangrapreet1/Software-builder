"""
Agent Collaboration Manager - Orchestrates multiple agents for Phase 2
Manages Problem Resolver, Tester, and Builder agents
"""
import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import logging

from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)


class AgentRole:
    """Agent roles in the collaboration framework"""
    COORDINATOR = "coordinator"
    BUILDER = "builder"
    RESOLVER = "resolver"
    TESTER = "tester"
    FRONTEND = "frontend"
    BACKEND = "backend"
    INTEGRATION = "integration"


class CollaborationManager:
    """
    Manages collaboration between multiple agents
    Provides orchestration, state management, and communication
    """
    
    def __init__(self, settings):
        self.settings = settings
        self.active_sessions: Dict[str, Dict] = {}
        self.collaboration_history: List[Dict] = []
        
        # Create shared state directory
        self.shared_state_dir = Path(settings.generated_apps_dir).parent / ".sb_artifacts" / "shared_state"
        self.shared_state_dir.mkdir(parents=True, exist_ok=True)
        
        # Agent state subscriptions
        self.agent_subscriptions: Dict[str, List[str]] = {}  # agent_name -> list of state keys
        
    async def orchestrate_build_with_resolution(
        self,
        build_id: str,
        app_path: str,
        agents: Dict[str, any]
    ) -> Dict:
        """
        Orchestrate a complete build cycle with automatic problem resolution
        
        Args:
            build_id: Unique build identifier
            app_path: Path to application
            agents: Dictionary of agent instances (resolver, tester, builder, etc.)
        
        Returns:
            Complete orchestration result with all agent outputs
        """
        session = {
            "build_id": build_id,
            "app_path": app_path,
            "start_time": datetime.utcnow().isoformat() + "Z",
            "status": "in_progress",
            "agents_involved": list(agents.keys()),
            "steps": []
        }
        
        self.active_sessions[build_id] = session
        
        try:
            # Step 1: Initial build/generation (if builder agents provided)
            if "backend" in agents and "frontend" in agents:
                build_result = await self._orchestrate_build(build_id, agents)
                session["steps"].append({
                    "name": "initial_build",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "result": build_result
                })
            
            # Step 2: Problem detection and resolution
            if "resolver" in agents:
                resolution_result = await self._orchestrate_resolution(
                    app_path,
                    agents["resolver"],
                    session
                )
                session["steps"].append({
                    "name": "problem_resolution",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "result": resolution_result
                })
            
            # Step 3: Validation and testing (if requested)
            if "tester" in agents and session.get("run_tests", False):
                test_result = await self._orchestrate_testing(
                    app_path,
                    agents["tester"]
                )
                session["steps"].append({
                    "name": "testing",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "result": test_result
                })
            
            # Step 4: Final validation
            final_status = self._determine_final_status(session)
            session["status"] = final_status
            session["end_time"] = datetime.utcnow().isoformat() + "Z"
            
            return {
                "success": final_status == "success",
                "build_id": build_id,
                "session": session,
                "summary": self._create_session_summary(session)
            }
            
        except Exception as e:
            session["status"] = "failed"
            session["error"] = str(e)
            session["end_time"] = datetime.utcnow().isoformat() + "Z"
            
            return {
                "success": False,
                "build_id": build_id,
                "session": session,
                "error": str(e)
            }
    
    async def _orchestrate_build(self, build_id: str, agents: Dict) -> Dict:
        """Orchestrate parallel build by backend and frontend agents"""
        results = {}
        
        # Run backend and frontend generation in parallel
        tasks = []
        if "backend" in agents:
            tasks.append(self._run_agent_task("backend", agents["backend"], build_id))
        if "frontend" in agents:
            tasks.append(self._run_agent_task("frontend", agents["frontend"], build_id))
        
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, task_result in enumerate(completed_tasks):
            if isinstance(task_result, Exception):
                results[f"task_{i}"] = {"error": str(task_result)}
            else:
                results.update(task_result)
        
        return results
    
    async def _orchestrate_resolution(
        self,
        app_path: str,
        resolver_agent,
        session: Dict
    ) -> Dict:
        """Orchestrate problem resolution with iterative fixes"""
        max_iterations = 3
        all_resolutions = []
        
        for iteration in range(max_iterations):
            # Get error logs from previous step if available
            error_logs = self._extract_error_logs(session)
            
            # Run resolver
            resolution = await resolver_agent.analyze_and_resolve(
                app_path=app_path,
                error_logs=error_logs,
                context={"iteration": iteration}
            )
            
            all_resolutions.append(resolution)
            
            # If all issues resolved, stop
            if resolution.get("issues_resolved", 0) == resolution.get("issues_found", 0):
                break
            
            # If no progress made, stop
            if iteration > 0 and resolution.get("issues_resolved", 0) == 0:
                break
        
        return {
            "iterations": len(all_resolutions),
            "resolutions": all_resolutions,
            "final_status": all_resolutions[-1] if all_resolutions else {}
        }
    
    async def _orchestrate_testing(self, app_path: str, tester_agent) -> Dict:
        """Orchestrate test execution"""
        return await tester_agent.run_tests(
            app_path=app_path,
            test_type="all",
            generate_missing=True
        )
    
    async def _run_agent_task(self, agent_name: str, agent, *args, **kwargs) -> Dict:
        """Run a single agent task with formal execution contract and shared state"""
        try:
            # Load shared state for subscribed keys
            shared_state = await self._load_shared_state_for_agent(agent_name)
            
            # Check if agent uses new BaseAgent interface
            if hasattr(agent, 'execute_safe'):
                from agents.base_agent import ExecutionContext
                
                # Create execution context with shared state
                context = ExecutionContext(
                    build_id=kwargs.get('build_id', 'unknown'),
                    request_data=kwargs.get('request_data', {}),
                    shared_state=shared_state,
                    metadata={'agent_name': agent_name}
                )
                
                # Execute with safety wrapper
                result = await agent.execute_safe(context)
                result_dict = result.to_dict()
                
                # Publish agent output to shared state
                await self.publish_state(agent_name, result_dict)
                
                return {agent_name: result_dict}
            
            # Fallback to old interface
            elif hasattr(agent, 'execute'):
                result = await agent.execute(*args, **kwargs)
                
                # Publish agent output to shared state
                await self.publish_state(agent_name, result)
                
                return {agent_name: result}
            else:
                # Legacy agents without execute method
                return {agent_name: {"status": "skipped", "message": "Agent has no execute method"}}
                
        except Exception as e:
            logger.error(f"Agent {agent_name} task failed: {e}")
            return {agent_name: {"error": str(e), "status": "failed"}}
    
    def _extract_error_logs(self, session: Dict) -> Optional[str]:
        """Extract error logs from session steps"""
        error_logs = []
        
        for step in session.get("steps", []):
            result = step.get("result", {})
            if "error" in result:
                error_logs.append(result["error"])
        
        return "\n".join(error_logs) if error_logs else None
    
    def _determine_final_status(self, session: Dict) -> str:
        """Determine final status based on all steps"""
        steps = session.get("steps", [])
        
        if not steps:
            return "failed"
        
        # Check if resolver fixed all issues
        for step in steps:
            if step["name"] == "problem_resolution":
                result = step["result"]
                if result.get("final_status", {}).get("status") == "success":
                    return "success"
        
        # Check if tests passed
        for step in steps:
            if step["name"] == "testing":
                result = step["result"]
                if result.get("status") == "passed":
                    return "success"
        
        return "partial"
    
    def _create_session_summary(self, session: Dict) -> Dict:
        """Create a human-readable summary of the session"""
        summary = {
            "build_id": session["build_id"],
            "status": session["status"],
            "duration": self._calculate_duration(session),
            "steps_completed": len(session.get("steps", [])),
            "agents_used": session.get("agents_involved", [])
        }
        
        # Add resolution summary
        for step in session.get("steps", []):
            if step["name"] == "problem_resolution":
                result = step["result"]
                final = result.get("final_status", {})
                summary["issues_found"] = final.get("issues_found", 0)
                summary["issues_resolved"] = final.get("issues_resolved", 0)
        
        # Add test summary
        for step in session.get("steps", []):
            if step["name"] == "testing":
                result = step["result"]
                summary["test_status"] = result.get("status")
                summary["tests_passed"] = result.get("summary", {}).get("passed", 0)
                summary["tests_failed"] = result.get("summary", {}).get("failed", 0)
        
        return summary
    
    def _calculate_duration(self, session: Dict) -> float:
        """Calculate session duration in seconds"""
        start = session.get("start_time")
        end = session.get("end_time")
        
        if not start or not end:
            return 0.0
        
        try:
            from datetime import datetime
            start_dt = datetime.fromisoformat(start.replace("Z", ""))
            end_dt = datetime.fromisoformat(end.replace("Z", ""))
            return (end_dt - start_dt).total_seconds()
        except Exception:
            return 0.0
    
    async def request_agent_action(
        self,
        requesting_agent: str,
        target_agent: str,
        action: str,
        parameters: Dict
    ) -> Dict:
        """
        Request an action from another agent
        Enables inter-agent communication
        """
        request = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "requesting_agent": requesting_agent,
            "target_agent": target_agent,
            "action": action,
            "parameters": parameters
        }
        
        self.collaboration_history.append(request)
        
        # This would route to the appropriate agent
        # Placeholder for now
        return {
            "status": "pending",
            "request_id": f"{requesting_agent}_{target_agent}_{action}_{datetime.utcnow().timestamp()}"
        }
    
    def get_session_status(self, build_id: str) -> Optional[Dict]:
        """Get current status of a build session"""
        return self.active_sessions.get(build_id)
    
    def get_all_active_sessions(self) -> Dict[str, Dict]:
        """Get all active collaboration sessions"""
        return self.active_sessions
    
    def get_collaboration_history(self, limit: int = 50) -> List[Dict]:
        """Get collaboration history"""
        return self.collaboration_history[-limit:]
    
    async def publish_state(self, agent_name: str, state_data: Dict, state_key: Optional[str] = None) -> str:
        """Publish agent state to shared storage for other agents to consume"""
        try:
            key = state_key or f"{agent_name}_{datetime.utcnow().timestamp()}"
            state_file = self.shared_state_dir / f"{key}.json"
            
            state_document = {
                "agent": agent_name,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "key": key,
                "data": state_data
            }
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_document, f, indent=2)
            
            logger.info(f"Published state {key} from agent {agent_name}")
            return key
            
        except Exception as e:
            logger.error(f"Failed to publish state: {e}")
            return ""
    
    async def subscribe_agent(self, agent_name: str, state_keys: List[str]):
        """Subscribe an agent to specific state keys"""
        self.agent_subscriptions[agent_name] = state_keys
        logger.info(f"Agent {agent_name} subscribed to {len(state_keys)} state keys")
    
    async def _load_shared_state_for_agent(self, agent_name: str) -> Dict:
        """Load all subscribed state for an agent"""
        shared_state = {}
        
        if agent_name not in self.agent_subscriptions:
            return shared_state
        
        for key in self.agent_subscriptions[agent_name]:
            state_file = self.shared_state_dir / f"{key}.json"
            
            if state_file.exists():
                try:
                    with open(state_file, 'r', encoding='utf-8') as f:
                        state_doc = json.load(f)
                        shared_state[key] = state_doc.get("data", {})
                except Exception as e:
                    logger.error(f"Failed to load state {key}: {e}")
        
        return shared_state
    
    async def get_state(self, state_key: str) -> Optional[Dict]:
        """Get a specific state document by key"""
        try:
            state_file = self.shared_state_dir / f"{state_key}.json"
            
            if not state_file.exists():
                return None
            
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to get state {state_key}: {e}")
            return None
    
    async def cleanup_old_state(self, max_age_hours: int = 24):
        """Clean up old state documents"""
        try:
            cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
            removed_count = 0
            
            for state_file in self.shared_state_dir.glob("*.json"):
                try:
                    with open(state_file, 'r', encoding='utf-8') as f:
                        state_doc = json.load(f)
                    
                    timestamp_str = state_doc.get("timestamp", "")
                    if timestamp_str:
                        state_time = datetime.fromisoformat(timestamp_str.replace("Z", "")).timestamp()
                        
                        if state_time < cutoff_time:
                            state_file.unlink()
                            removed_count += 1
                            
                except Exception as e:
                    logger.error(f"Error processing {state_file}: {e}")
            
            logger.info(f"Cleaned up {removed_count} old state documents")
            return removed_count
            
        except Exception as e:
            logger.error(f"State cleanup failed: {e}")
            return 0


class LivePreviewBridge:
    """
    Bridge between build system and live preview
    Manages temporary deployments and preview URLs
    """
    
    def __init__(self, sandbox_orchestrator, settings):
        self.sandbox = sandbox_orchestrator
        self.settings = settings
        self.active_previews: Dict[str, Dict] = {}
    
    async def create_live_preview(
        self,
        build_id: str,
        app_path: str,
        port: int = 3000,
        auto_start: bool = True
    ) -> Dict:
        """
        Create a live preview for a build
        
        Returns:
            {
                "previewUrl": str,
                "instanceId": str,
                "expiresAt": str,
                "logsUrl": str,
                "status": str
            }
        """
        try:
            if auto_start:
                # Launch in sandbox
                instance = await self.sandbox.launch_instance(
                    app_path=app_path,
                    port=port,
                    cpu_limit=1.0,
                    memory_limit="512m",
                    timeout=3600
                )
                
                preview_info = {
                    "build_id": build_id,
                    "previewUrl": instance["preview_url"],
                    "instanceId": instance["instance_id"],
                    "expiresAt": instance["expires_at"],
                    "logsUrl": f"/api/sandbox/{instance['instance_id']}/logs",
                    "status": "running",
                    "port": instance["port"],
                    "created_at": datetime.utcnow().isoformat() + "Z"
                }
                
                self.active_previews[build_id] = preview_info
                return preview_info
            else:
                # Create preview session without launching
                preview_info = {
                    "build_id": build_id,
                    "previewUrl": f"http://localhost:{port}",
                    "instanceId": None,
                    "expiresAt": None,
                    "logsUrl": None,
                    "status": "created",
                    "port": port,
                    "created_at": datetime.utcnow().isoformat() + "Z"
                }
                
                self.active_previews[build_id] = preview_info
                return preview_info
                
        except Exception as e:
            return {
                "build_id": build_id,
                "previewUrl": None,
                "instanceId": None,
                "expiresAt": None,
                "logsUrl": None,
                "status": "error",
                "error": str(e)
            }
    
    async def update_preview(self, build_id: str, app_path: str) -> Dict:
        """Update an existing preview with new code"""
        preview = self.active_previews.get(build_id)
        
        if not preview:
            return {"error": "Preview not found"}
        
        # Stop existing instance
        if preview.get("instanceId"):
            try:
                await self.sandbox.stop_instance(preview["instanceId"])
            except Exception:
                pass
        
        # Create new preview
        return await self.create_live_preview(build_id, app_path, preview["port"])
    
    async def stop_preview(self, build_id: str) -> Dict:
        """Stop a live preview"""
        preview = self.active_previews.get(build_id)
        
        if not preview:
            return {"error": "Preview not found"}
        
        if preview.get("instanceId"):
            try:
                result = await self.sandbox.stop_instance(preview["instanceId"])
                preview["status"] = "stopped"
                return result
            except Exception as e:
                return {"error": str(e)}
        
        preview["status"] = "stopped"
        return {"success": True}
    
    def get_preview_status(self, build_id: str) -> Optional[Dict]:
        """Get status of a live preview"""
        return self.active_previews.get(build_id)
    
    def get_all_previews(self) -> Dict[str, Dict]:
        """Get all active previews"""
        return self.active_previews
