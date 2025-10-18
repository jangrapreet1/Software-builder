"""
Run-specific audit logging for tracking complete workflows (detect, build, run, fix, PR)
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class RunAuditLogger:
    """Tracks complete run workflows with structured artifacts"""
    
    def __init__(self, artifacts_dir: str = ".sb_artifacts"):
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.current_run_id: Optional[str] = None
        self.current_run_log: List[Dict] = []
    
    def start_run(self, run_type: str, description: str) -> str:
        """Start a new run and return run_id"""
        self.current_run_id = f"run_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
        self.current_run_log = [{
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "runId": self.current_run_id,
            "step": "start",
            "runType": run_type,
            "description": description,
            "humanSummary": f"Started {run_type}: {description}"
        }]
        return self.current_run_id
    
    def log_step(
        self,
        step: str,
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        stdout_snippet: Optional[str] = None,
        stderr_snippet: Optional[str] = None,
        container_id: Optional[str] = None,
        human_summary: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Log a step in the current run"""
        if not self.current_run_id:
            raise ValueError("No active run. Call start_run() first.")
        
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "runId": self.current_run_id,
            "step": step,
        }
        
        if command:
            entry["command"] = command
        if exit_code is not None:
            entry["exitCode"] = exit_code
        if stdout_snippet:
            entry["stdoutSnippet"] = stdout_snippet[:500]
        if stderr_snippet:
            entry["stderrSnippet"] = stderr_snippet[:500]
        if container_id:
            entry["containerId"] = container_id
        if human_summary:
            entry["humanSummary"] = human_summary
        if metadata:
            entry["metadata"] = metadata
        
        self.current_run_log.append(entry)
    
    def finish_run(self, success: bool = True, summary: Optional[str] = None) -> Path:
        """Finish the current run and persist audit log"""
        if not self.current_run_id:
            raise ValueError("No active run to finish.")
        
        self.log_step(
            step="finish",
            human_summary=summary or ("Run completed successfully" if success else "Run failed"),
            metadata={"success": success}
        )
        
        # Write audit log
        audit_path = self.artifacts_dir / f"audit_{self.current_run_id}.json"
        with open(audit_path, 'w', encoding='utf-8') as f:
            json.dump(self.current_run_log, f, indent=2)
        
        # Reset state
        run_id = self.current_run_id
        self.current_run_id = None
        self.current_run_log = []
        
        return audit_path
    
    def get_run_log(self, run_id: str) -> Optional[List[Dict]]:
        """Retrieve audit log for a specific run"""
        audit_path = self.artifacts_dir / f"audit_{run_id}.json"
        if not audit_path.exists():
            return None
        
        try:
            with open(audit_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def list_runs(self, limit: int = 50) -> List[Dict]:
        """List recent runs with summary info"""
        runs = []
        audit_files = sorted(self.artifacts_dir.glob("audit_run_*.json"), reverse=True)
        
        for audit_file in audit_files[:limit]:
            try:
                with open(audit_file, 'r', encoding='utf-8') as f:
                    log = json.load(f)
                    if log:
                        first_entry = log[0]
                        last_entry = log[-1]
                        runs.append({
                            "runId": first_entry.get("runId"),
                            "runType": first_entry.get("runType"),
                            "description": first_entry.get("description"),
                            "startTime": first_entry.get("timestamp"),
                            "endTime": last_entry.get("timestamp"),
                            "success": last_entry.get("metadata", {}).get("success", True),
                            "steps": len(log),
                            "auditPath": str(audit_file)
                        })
            except Exception:
                continue
        
        return runs
