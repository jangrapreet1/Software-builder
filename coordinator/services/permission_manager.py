"""
Permission management for sandbox operations
"""
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import secrets


class PermissionManager:
    """Manages user permissions for sandbox operations"""
    
    def __init__(self, default_expiry: int = 3600):
        self.default_expiry = default_expiry
        self.permissions: Dict[str, Dict] = {}
    
    def grant_permission(
        self,
        session_id: str,
        actions: List[str],
        commands: List[str],
        duration: Optional[int] = None
    ) -> Dict:
        """
        Grant permissions for a session
        
        Args:
            session_id: Session identifier
            actions: List of actions (e.g., 'allow_build', 'allow_run')
            commands: List of commands user approved
            duration: Permission duration in seconds
        
        Returns:
            Permission record
        """
        duration = duration or self.default_expiry
        expires_at = datetime.utcnow() + timedelta(seconds=duration)
        
        permission = {
            "session_id": session_id,
            "actions": {action: True for action in actions},
            "approved_commands": commands,
            "granted_at": datetime.utcnow().isoformat() + "Z",
            "expires_at": expires_at.isoformat() + "Z",
            "active": True
        }
        
        self.permissions[session_id] = permission
        return permission
    
    def has_permission(self, session_id: str, action: str) -> bool:
        """Check if session has permission for action"""
        if session_id not in self.permissions:
            return False
        
        perm = self.permissions[session_id]
        
        # Check expiry
        expires_at = datetime.fromisoformat(perm["expires_at"].replace("Z", ""))
        if datetime.utcnow() > expires_at:
            perm["active"] = False
            return False
        
        if not perm["active"]:
            return False
        
        return perm["actions"].get(action, False)
    
    def get_permission(self, session_id: str) -> Optional[Dict]:
        """Get permission record for session"""
        return self.permissions.get(session_id)
    
    def revoke_permission(self, session_id: str) -> bool:
        """Revoke permissions for session"""
        if session_id not in self.permissions:
            return False
        
        self.permissions[session_id]["active"] = False
        self.permissions[session_id]["revoked_at"] = datetime.utcnow().isoformat() + "Z"
        return True
    
    def cleanup_expired(self):
        """Clean up expired permissions"""
        now = datetime.utcnow()
        expired = []
        
        for session_id, perm in self.permissions.items():
            expires_at = datetime.fromisoformat(perm["expires_at"].replace("Z", ""))
            if now > expires_at:
                expired.append(session_id)
        
        for session_id in expired:
            del self.permissions[session_id]
        
        return len(expired)
