"""
Audit logging for command execution and security events
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from enum import Enum


class AuditEventType(Enum):
    """Types of audit events"""
    COMMAND_APPROVED = "command_approved"
    COMMAND_EXECUTED = "command_executed"
    COMMAND_FAILED = "command_failed"
    INSTANCE_LAUNCHED = "instance_launched"
    INSTANCE_STOPPED = "instance_stopped"
    SESSION_CREATED = "session_created"
    SESSION_REVOKED = "session_revoked"
    SECURITY_VIOLATION = "security_violation"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"


logger = logging.getLogger(__name__)


class AuditLogger:
    """Audit logger for security and compliance"""
    
    def __init__(self, log_dir: Optional[str] = None):
        self.log_dir = Path(log_dir) if log_dir else Path("logs/audit")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Current log file (rotated daily)
        self.current_log_file = self._get_log_file()
        
        # In-memory buffer for recent events
        self.recent_events: List[Dict] = []
        self.max_recent_events = 100
    
    def _get_log_file(self) -> Path:
        """Get current log file path (daily rotation)"""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        return self.log_dir / f"audit-{date_str}.jsonl"
    
    def log_event(
        self,
        event_type: AuditEventType,
        details: Dict,
        user: Optional[str] = None,
        instance_id: Optional[str] = None,
        success: bool = True,
    ) -> Dict:
        """
        Log an audit event
        
        Args:
            event_type: Type of event
            details: Event-specific details
            user: User identifier (if applicable)
            instance_id: Instance identifier (if applicable)
            success: Whether the event was successful
        
        Returns:
            Logged event data
        """
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type.value,
            "success": success,
            "details": details,
        }
        
        if user:
            event["user"] = user
        if instance_id:
            event["instance_id"] = instance_id
        
        # Write to file
        self._write_event(event)
        
        # Add to recent events buffer
        self.recent_events.append(event)
        if len(self.recent_events) > self.max_recent_events:
            self.recent_events.pop(0)
        
        logger.info(f"Audit event: {event_type.value} - {success}")
        
        return event
    
    def log_command_execution(
        self,
        command: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        duration_ms: int,
        approved_by: Optional[str] = None,
        approval_timestamp: Optional[str] = None,
        instance_id: Optional[str] = None,
    ) -> Dict:
        """Log command execution with full audit trail"""
        details = {
            "command": command,
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "stdout_lines": len(stdout.split("\n")) if stdout else 0,
            "stderr_lines": len(stderr.split("\n")) if stderr else 0,
            "stdout_preview": stdout[:500] if stdout else "",
            "stderr_preview": stderr[:500] if stderr else "",
        }
        
        if approved_by:
            details["approved_by"] = approved_by
        if approval_timestamp:
            details["approval_timestamp"] = approval_timestamp
        
        event_type = AuditEventType.COMMAND_EXECUTED if exit_code == 0 else AuditEventType.COMMAND_FAILED
        
        return self.log_event(
            event_type=event_type,
            details=details,
            instance_id=instance_id,
            success=(exit_code == 0),
        )
    
    def log_instance_launch(
        self,
        instance_id: str,
        app_path: str,
        cpu_limit: float,
        memory_limit: str,
        timeout: int,
        user: Optional[str] = None,
    ) -> Dict:
        """Log instance launch event"""
        details = {
            "app_path": app_path,
            "cpu_limit": cpu_limit,
            "memory_limit": memory_limit,
            "timeout": timeout,
        }
        
        return self.log_event(
            event_type=AuditEventType.INSTANCE_LAUNCHED,
            details=details,
            user=user,
            instance_id=instance_id,
        )
    
    def log_instance_stop(
        self,
        instance_id: str,
        forced: bool,
        reason: str,
        user: Optional[str] = None,
    ) -> Dict:
        """Log instance stop event"""
        details = {
            "forced": forced,
            "reason": reason,
        }
        
        return self.log_event(
            event_type=AuditEventType.INSTANCE_STOPPED,
            details=details,
            user=user,
            instance_id=instance_id,
        )
    
    def log_session_created(
        self,
        session_token_prefix: str,
        instance_id: str,
        duration: int,
        user: Optional[str] = None,
    ) -> Dict:
        """Log session creation (token prefix only for security)"""
        details = {
            "session_token_prefix": session_token_prefix[:16] + "...",
            "duration": duration,
        }
        
        return self.log_event(
            event_type=AuditEventType.SESSION_CREATED,
            details=details,
            user=user,
            instance_id=instance_id,
        )
    
    def log_security_violation(
        self,
        violation_type: str,
        description: str,
        instance_id: Optional[str] = None,
        user: Optional[str] = None,
    ) -> Dict:
        """Log security violation"""
        details = {
            "violation_type": violation_type,
            "description": description,
        }
        
        return self.log_event(
            event_type=AuditEventType.SECURITY_VIOLATION,
            details=details,
            user=user,
            instance_id=instance_id,
            success=False,
        )
    
    def log_resource_limit_exceeded(
        self,
        resource_type: str,
        limit: str,
        actual: str,
        instance_id: Optional[str] = None,
    ) -> Dict:
        """Log resource limit exceeded"""
        details = {
            "resource_type": resource_type,
            "limit": limit,
            "actual": actual,
        }
        
        return self.log_event(
            event_type=AuditEventType.RESOURCE_LIMIT_EXCEEDED,
            details=details,
            instance_id=instance_id,
            success=False,
        )
    
    def _write_event(self, event: Dict):
        """Write event to log file"""
        try:
            # Check if we need to rotate
            current_file = self._get_log_file()
            if current_file != self.current_log_file:
                self.current_log_file = current_file
            
            # Append to JSONL file
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event) + "\n")
                
        except Exception as e:
            logger.error(f"Failed to write audit event: {e}")
    
    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Get recent audit events from memory"""
        return self.recent_events[-limit:]
    
    def query_events(
        self,
        event_type: Optional[AuditEventType] = None,
        instance_id: Optional[str] = None,
        user: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Query audit events from log files
        
        Args:
            event_type: Filter by event type
            instance_id: Filter by instance ID
            user: Filter by user
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            limit: Maximum number of events to return
        
        Returns:
            List of matching events
        """
        events = []
        
        # Read from current and recent log files
        log_files = sorted(self.log_dir.glob("audit-*.jsonl"), reverse=True)
        
        for log_file in log_files[:7]:  # Last 7 days
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        
                        event = json.loads(line)
                        
                        # Apply filters
                        if event_type and event.get("event_type") != event_type.value:
                            continue
                        if instance_id and event.get("instance_id") != instance_id:
                            continue
                        if user and event.get("user") != user:
                            continue
                        if start_date and event.get("timestamp", "") < start_date:
                            continue
                        if end_date and event.get("timestamp", "") > end_date:
                            continue
                        
                        events.append(event)
                        
                        if len(events) >= limit:
                            return events
                            
            except Exception as e:
                logger.error(f"Error reading audit log {log_file}: {e}")
        
        return events
    
    def get_stats(self) -> Dict:
        """Get audit log statistics"""
        recent = self.get_recent_events(100)
        
        event_counts = {}
        for event in recent:
            event_type = event.get("event_type", "unknown")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        success_count = sum(1 for e in recent if e.get("success", True))
        failure_count = len(recent) - success_count
        
        return {
            "total_events": len(recent),
            "success_count": success_count,
            "failure_count": failure_count,
            "event_type_counts": event_counts,
            "log_directory": str(self.log_dir),
        }


# Global audit logger instance
audit_logger = AuditLogger()
