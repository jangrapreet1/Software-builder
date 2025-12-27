"""
Session management for secure preview URLs and access control
"""
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages preview sessions with tokens and expiry"""
    
    def __init__(
        self,
        default_session_duration: int = 3600,  # 1 hour
        max_sessions_per_instance: int = 5,
    ):
        self.default_session_duration = default_session_duration
        self.max_sessions_per_instance = max_sessions_per_instance
        
        # Sessions: {session_token: session_data}
        self.sessions: Dict[str, Dict] = {}
        
        # Instance to sessions mapping
        self.instance_sessions: Dict[str, list] = {}
    
    def create_session(
        self,
        instance_id: str,
        preview_url: str,
        duration: Optional[int] = None,
        metadata: Optional[Dict] = None,
        build_id: Optional[str] = None,
        approved_commands: Optional[list] = None,
        detection_data: Optional[Dict] = None,
    ) -> Dict:
        """
        Create a new preview session with secure token and rich metadata
        
        Args:
            instance_id: Instance identifier
            preview_url: Base preview URL
            duration: Session duration in seconds
            metadata: Additional session metadata
            build_id: Build/workflow ID for traceability
            approved_commands: Commands approved by user
            detection_data: Repository detection context
        
        Returns:
            Session details with token and expiry
        """
        # Check session limit per instance
        if instance_id in self.instance_sessions:
            if len(self.instance_sessions[instance_id]) >= self.max_sessions_per_instance:
                # Clean up expired sessions first
                self._cleanup_expired_sessions(instance_id)
                
                # Check again
                if len(self.instance_sessions[instance_id]) >= self.max_sessions_per_instance:
                    raise RuntimeError(f"Maximum sessions ({self.max_sessions_per_instance}) for instance {instance_id}")
        
        # Generate secure token
        session_token = secrets.token_urlsafe(32)
        
        # Calculate expiry
        duration = duration or self.default_session_duration
        expires_at = datetime.utcnow() + timedelta(seconds=duration)
        
        # Create session with enriched metadata
        session = {
            "session_token": session_token,
            "instance_id": instance_id,
            # Store target base URL (raw sandbox preview origin)
            "preview_url": preview_url,
            # Expose a coordinator-relative bridge URL for clients to load inside HTTPS UI
            "secure_preview_url": f"/preview/bridge/?session={session_token}",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "expires_at": expires_at.isoformat() + "Z",
            "duration": duration,
            "active": True,
            "metadata": metadata or {},
            "build_id": build_id,
            "approved_commands": approved_commands or [],
            "detection_data": detection_data or {},
            "agent_outputs": [],  # Track agent interactions
            "workflow_state": None,  # Link to workflow state
        }
        
        # Store session
        self.sessions[session_token] = session
        
        # Track by instance
        if instance_id not in self.instance_sessions:
            self.instance_sessions[instance_id] = []
        self.instance_sessions[instance_id].append(session_token)
        
        logger.info(f"Created session for instance {instance_id}: {session_token[:16]}...")
        
        return {
            "session_token": session_token,
            # Return the bridged (coordinator-relative) URL to prevent mixed-content issues
            "preview_url": session["secure_preview_url"],
            "expires_at": session["expires_at"],
            "duration": duration,
        }
    
    def validate_session(self, session_token: str) -> Dict:
        """
        Validate a session token
        
        Returns:
            Session data if valid, raises ValueError if invalid/expired
        """
        if session_token not in self.sessions:
            raise ValueError("Invalid session token")
        
        session = self.sessions[session_token]
        
        # Check expiry
        expires_at = datetime.fromisoformat(session["expires_at"].replace("Z", ""))
        if datetime.utcnow() > expires_at:
            session["active"] = False
            raise ValueError("Session expired")
        
        if not session["active"]:
            raise ValueError("Session inactive")
        
        return session
    
    def revoke_session(self, session_token: str) -> bool:
        """Revoke a session"""
        if session_token not in self.sessions:
            return False
        
        session = self.sessions[session_token]
        session["active"] = False
        session["revoked_at"] = datetime.utcnow().isoformat() + "Z"
        
        logger.info(f"Revoked session: {session_token[:16]}...")
        return True
    
    def revoke_instance_sessions(self, instance_id: str) -> int:
        """Revoke all sessions for an instance"""
        if instance_id not in self.instance_sessions:
            return 0
        
        count = 0
        for session_token in self.instance_sessions[instance_id]:
            if self.revoke_session(session_token):
                count += 1
        
        logger.info(f"Revoked {count} sessions for instance {instance_id}")
        return count
    
    def get_session(self, session_token: str) -> Optional[Dict]:
        """Get session data"""
        return self.sessions.get(session_token)
    
    def list_instance_sessions(self, instance_id: str) -> list:
        """List all sessions for an instance"""
        if instance_id not in self.instance_sessions:
            return []
        
        sessions = []
        for session_token in self.instance_sessions[instance_id]:
            session = self.sessions.get(session_token)
            if session:
                sessions.append({
                    "session_token": session_token[:16] + "...",  # Truncated for security
                    "active": session["active"],
                    "created_at": session["created_at"],
                    "expires_at": session["expires_at"],
                })
        
        return sessions
    
    def cleanup_expired(self):
        """Clean up all expired sessions"""
        now = datetime.utcnow()
        expired = []
        
        for session_token, session in self.sessions.items():
            expires_at = datetime.fromisoformat(session["expires_at"].replace("Z", ""))
            if now > expires_at:
                expired.append(session_token)
        
        for session_token in expired:
            instance_id = self.sessions[session_token]["instance_id"]
            
            # Remove from sessions
            del self.sessions[session_token]
            
            # Remove from instance mapping
            if instance_id in self.instance_sessions:
                self.instance_sessions[instance_id].remove(session_token)
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
        
        return len(expired)
    
    def _cleanup_expired_sessions(self, instance_id: str):
        """Clean up expired sessions for a specific instance"""
        if instance_id not in self.instance_sessions:
            return
        
        now = datetime.utcnow()
        expired = []
        
        for session_token in self.instance_sessions[instance_id]:
            session = self.sessions.get(session_token)
            if session:
                expires_at = datetime.fromisoformat(session["expires_at"].replace("Z", ""))
                if now > expires_at:
                    expired.append(session_token)
        
        for session_token in expired:
            del self.sessions[session_token]
            self.instance_sessions[instance_id].remove(session_token)
    
    def add_agent_output(self, session_token: str, agent_name: str, output: Dict) -> bool:
        """Add agent output to session for context tracking"""
        if session_token not in self.sessions:
            return False
        
        session = self.sessions[session_token]
        session["agent_outputs"].append({
            "agent": agent_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "output": output
        })
        
        logger.info(f"Added {agent_name} output to session {session_token[:16]}...")
        return True
    
    def link_workflow_state(self, session_token: str, workflow_state_path: str) -> bool:
        """Link session to persisted workflow state"""
        if session_token not in self.sessions:
            return False
        
        self.sessions[session_token]["workflow_state"] = workflow_state_path
        logger.info(f"Linked workflow state to session {session_token[:16]}...")
        return True
    
    def get_session_context(self, session_token: str) -> Optional[Dict]:
        """Get full session context including metadata, commands, and agent outputs"""
        session = self.sessions.get(session_token)
        if not session:
            return None
        
        return {
            "session_token": session_token[:16] + "...",  # Truncated for security
            "instance_id": session["instance_id"],
            "build_id": session.get("build_id"),
            "created_at": session["created_at"],
            "expires_at": session["expires_at"],
            "active": session["active"],
            "approved_commands": session.get("approved_commands", []),
            "detection_data": session.get("detection_data", {}),
            "agent_outputs": session.get("agent_outputs", []),
            "workflow_state": session.get("workflow_state"),
            "metadata": session.get("metadata", {})
        }
    
    def get_stats(self) -> Dict:
        """Get session statistics"""
        total_sessions = len(self.sessions)
        active_sessions = sum(1 for s in self.sessions.values() if s["active"])
        sessions_with_workflows = sum(1 for s in self.sessions.values() if s.get("workflow_state"))
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "instances_with_sessions": len(self.instance_sessions),
            "sessions_with_workflows": sessions_with_workflows,
        }
