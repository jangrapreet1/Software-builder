"""
Agent Performance Dashboard - Quick Win #5
Tracks and displays agent performance metrics
"""
import json
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import statistics


class AgentPerformanceTracker:
    """
    Tracks agent performance:
    - Success rates
    - Average execution times
    - Error frequencies by agent
    - Bottleneck identification
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = Path(storage_path) if storage_path else Path(".sb_artifacts/agent_performance")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.executions_file = self.storage_path / "executions.json"
        self.executions: List[Dict] = []
        
        self._load_executions()
    
    def _load_executions(self):
        """Load execution history"""
        if self.executions_file.exists():
            with open(self.executions_file, 'r', encoding='utf-8') as f:
                self.executions = json.load(f)
    
    def _save_executions(self):
        """Save execution history"""
        with open(self.executions_file, 'w', encoding='utf-8') as f:
            json.dump(self.executions[-10000:], f, indent=2)  # Keep last 10k
    
    def record_execution(
        self,
        agent_name: str,
        build_id: str,
        success: bool,
        duration_seconds: float,
        error_type: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Record agent execution"""
        execution = {
            "agent_name": agent_name,
            "build_id": build_id,
            "success": success,
            "duration_seconds": duration_seconds,
            "error_type": error_type,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        self.executions.append(execution)
        self._save_executions()
    
    def get_agent_statistics(self, agent_name: str, days: int = 30) -> Dict:
        """Get statistics for specific agent"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        agent_execs = [
            e for e in self.executions
            if e["agent_name"] == agent_name and 
            datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) > cutoff
        ]
        
        if not agent_execs:
            return {
                "agent_name": agent_name,
                "total_executions": 0,
                "success_rate": 0,
                "average_duration": 0,
                "error_types": {}
            }
        
        total = len(agent_execs)
        successful = sum(1 for e in agent_execs if e["success"])
        durations = [e["duration_seconds"] for e in agent_execs]
        
        # Count error types
        error_types = defaultdict(int)
        for exec in agent_execs:
            if not exec["success"] and exec.get("error_type"):
                error_types[exec["error_type"]] += 1
        
        return {
            "agent_name": agent_name,
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": total - successful,
            "success_rate": round((successful / total * 100), 2),
            "average_duration": round(statistics.mean(durations), 2),
            "median_duration": round(statistics.median(durations), 2),
            "min_duration": round(min(durations), 2),
            "max_duration": round(max(durations), 2),
            "error_types": dict(error_types),
            "period_days": days
        }
    
    def get_all_agents_summary(self, days: int = 30) -> List[Dict]:
        """Get summary for all agents"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        recent_execs = [
            e for e in self.executions
            if datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) > cutoff
        ]
        
        # Group by agent
        by_agent = defaultdict(list)
        for exec in recent_execs:
            by_agent[exec["agent_name"]].append(exec)
        
        summaries = []
        for agent_name, execs in by_agent.items():
            total = len(execs)
            successful = sum(1 for e in execs if e["success"])
            durations = [e["duration_seconds"] for e in execs]
            
            summaries.append({
                "agent_name": agent_name,
                "total_executions": total,
                "success_rate": round((successful / total * 100), 2),
                "average_duration": round(statistics.mean(durations), 2),
                "status": "healthy" if (successful / total) >= 0.8 else "warning"
            })
        
        # Sort by execution count
        summaries.sort(key=lambda x: x["total_executions"], reverse=True)
        return summaries
    
    def identify_bottlenecks(self, days: int = 30) -> List[Dict]:
        """Identify performance bottlenecks"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        recent_execs = [
            e for e in self.executions
            if datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) > cutoff
        ]
        
        # Group by agent
        by_agent = defaultdict(list)
        for exec in recent_execs:
            by_agent[exec["agent_name"]].append(exec["duration_seconds"])
        
        bottlenecks = []
        for agent_name, durations in by_agent.items():
            if len(durations) < 5:  # Need enough data
                continue
            
            avg = statistics.mean(durations)
            median = statistics.median(durations)
            
            # Flag if average is significantly higher than median (long tail)
            if avg > median * 1.5:
                bottlenecks.append({
                    "agent_name": agent_name,
                    "average_duration": round(avg, 2),
                    "median_duration": round(median, 2),
                    "issue": "High variance in execution time",
                    "recommendation": "Investigate slow executions",
                    "severity": "medium" if avg < 60 else "high"
                })
            
            # Flag if consistently slow
            if avg > 30:
                bottlenecks.append({
                    "agent_name": agent_name,
                    "average_duration": round(avg, 2),
                    "issue": "Consistently slow execution",
                    "recommendation": "Optimize agent logic or increase resources",
                    "severity": "high" if avg > 60 else "medium"
                })
        
        return bottlenecks
    
    def get_error_trends(self, days: int = 30) -> Dict:
        """Get error trends over time"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        recent_execs = [
            e for e in self.executions
            if datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) > cutoff and not e["success"]
        ]
        
        # Group by error type
        by_error_type = defaultdict(list)
        for exec in recent_execs:
            error_type = exec.get("error_type", "unknown")
            by_error_type[error_type].append(exec)
        
        trends = []
        for error_type, execs in by_error_type.items():
            # Group by agent
            by_agent = defaultdict(int)
            for exec in execs:
                by_agent[exec["agent_name"]] += 1
            
            trends.append({
                "error_type": error_type,
                "total_occurrences": len(execs),
                "affected_agents": dict(by_agent),
                "first_seen": min(e["timestamp"] for e in execs),
                "last_seen": max(e["timestamp"] for e in execs)
            })
        
        trends.sort(key=lambda x: x["total_occurrences"], reverse=True)
        return {
            "period_days": days,
            "total_errors": len(recent_execs),
            "unique_error_types": len(by_error_type),
            "trends": trends
        }
    
    def get_dashboard_data(self, days: int = 30) -> Dict:
        """Get complete dashboard data"""
        return {
            "summary": self.get_all_agents_summary(days),
            "bottlenecks": self.identify_bottlenecks(days),
            "error_trends": self.get_error_trends(days),
            "period_days": days,
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
    
    def export_report(self, output_path: Optional[Path] = None) -> str:
        """Export performance report"""
        data = self.get_dashboard_data()
        
        if output_path is None:
            output_path = self.storage_path / f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return str(output_path)


# Global instance
_performance_tracker = None

def get_performance_tracker() -> AgentPerformanceTracker:
    """Get global performance tracker"""
    global _performance_tracker
    if _performance_tracker is None:
        _performance_tracker = AgentPerformanceTracker()
    return _performance_tracker
