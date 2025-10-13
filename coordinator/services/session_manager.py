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
    ) -> Dict:
        """
        Create a new preview session with secure token
        
        Args:
            instance_id: Instance identifier
            preview_url: Base preview URL
            duration: Session duration in seconds
            metadata: Additional session metadata
        
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
        
        # Create session
        session = {
            "session_token": session_token,
            "instance_id": instance_id,
            "preview_url": preview_url,
            "secure_preview_url": f"{preview_url}?session={session_token}",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "expires_at": expires_at.isoformat() + "Z",
            "duration": duration,
            "active": True,
            "metadata": metadata or {},
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
    
    def get_stats(self) -> Dict:
        """Get session statistics"""
        total_sessions = len(self.sessions)
        active_sessions = sum(1 for s in self.sessions.values() if s["active"])
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "instances_with_sessions": len(self.instance_sessions),
        }
