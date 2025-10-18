"""
Permission management for sandbox operations
"""
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import secrets
import hashlib
import json


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
        Grant permissions for a session with command hash validation
        
        Args:
            session_id: Session identifier
            actions: List of actions (e.g., 'allow_build', 'allow_run')
            commands: List of commands user approved
            duration: Permission duration in seconds
        
        Returns:
            Permission record with command hashes
        """
        duration = duration or self.default_expiry
        expires_at = datetime.utcnow() + timedelta(seconds=duration)
        
        # Generate hashes for approved commands
        command_hashes = [self._hash_command(cmd) for cmd in commands]
        
        permission = {
            "session_id": session_id,
            "actions": {action: True for action in actions},
            "approved_commands": commands,
            "command_hashes": command_hashes,
            "granted_at": datetime.utcnow().isoformat() + "Z",
            "expires_at": expires_at.isoformat() + "Z",
            "active": True,
            "execution_count": 0,  # Track how many times commands were executed
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
    
    def validate_command(self, session_id: str, command: str) -> bool:
        """
        Validate that a command matches an approved command hash
        
        Args:
            session_id: Session identifier
            command: Command to validate
        
        Returns:
            True if command is approved, False otherwise
        """
        if not self.has_permission(session_id, "allow_run"):
            return False
        
        perm = self.permissions.get(session_id)
        if not perm:
            return False
        
        command_hash = self._hash_command(command)
        is_valid = command_hash in perm.get("command_hashes", [])
        
        if is_valid:
            perm["execution_count"] += 1
        
        return is_valid
    
    def get_approved_commands(self, session_id: str) -> List[str]:
        """Get list of approved commands for a session"""
        perm = self.permissions.get(session_id)
        if not perm:
            return []
        return perm.get("approved_commands", [])
    
    def _hash_command(self, command: str) -> str:
        """Generate SHA-256 hash of a command"""
        # Normalize command (strip whitespace, lowercase)
        normalized = command.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()
    
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
    
    def get_stats(self) -> Dict:
        """Get permission statistics"""
        total_permissions = len(self.permissions)
        active_permissions = sum(1 for p in self.permissions.values() if p["active"])
        total_executions = sum(p.get("execution_count", 0) for p in self.permissions.values())
        
        return {
            "total_permissions": total_permissions,
            "active_permissions": active_permissions,
            "total_executions": total_executions,
        }
