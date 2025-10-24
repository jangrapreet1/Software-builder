"""
Metrics Collector - Comprehensive observability for agent workflows
Tracks performance, success rates, and system health
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
import json
import statistics
import threading


class MetricType:
    """Metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class Metric:
    """Single metric value"""
    
    def __init__(self, name: str, value: float, labels: Optional[Dict] = None):
        self.name = name
        self.value = value
        self.labels = labels or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp.isoformat() + "Z"
        }


class MetricsCollector:
    """
    Collects and aggregates metrics from all system components
    Provides real-time insights and historical analytics
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path(".sb_artifacts/metrics")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Metrics storage
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._timers: Dict[str, List[float]] = defaultdict(list)
        
        # Thread-safe access
        self._lock = threading.RLock()
        
        # Metric history
        self._metric_history: List[Metric] = []
        self._max_history = 10000
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict] = None):
        """Increment a counter metric"""
        with self._lock:
            key = self._make_key(name, labels)
            self._counters[key] += value
            self._record_metric(Metric(name, self._counters[key], labels))
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict] = None):
        """Set a gauge metric"""
        with self._lock:
            key = self._make_key(name, labels)
            self._gauges[key] = value
            self._record_metric(Metric(name, value, labels))
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict] = None):
        """Add observation to histogram"""
        with self._lock:
            key = self._make_key(name, labels)
            self._histograms[key].append(value)
            # Keep only recent values
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]
            self._record_metric(Metric(name, value, labels))
    
    def record_duration(self, name: str, duration: float, labels: Optional[Dict] = None):
        """Record a duration/timer metric"""
        with self._lock:
            key = self._make_key(name, labels)
            self._timers[key].append(duration)
            # Keep only recent values
            if len(self._timers[key]) > 1000:
                self._timers[key] = self._timers[key][-1000:]
            self._record_metric(Metric(name, duration, labels))
    
    def get_counter(self, name: str, labels: Optional[Dict] = None) -> float:
        """Get counter value"""
        with self._lock:
            key = self._make_key(name, labels)
            return self._counters.get(key, 0.0)
    
    def get_gauge(self, name: str, labels: Optional[Dict] = None) -> Optional[float]:
        """Get gauge value"""
        with self._lock:
            key = self._make_key(name, labels)
            return self._gauges.get(key)
    
    def get_histogram_stats(self, name: str, labels: Optional[Dict] = None) -> Optional[Dict]:
        """Get histogram statistics"""
        with self._lock:
            key = self._make_key(name, labels)
            values = self._histograms.get(key, [])
            
            if not values:
                return None
            
            sorted_values = sorted(values)
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "p50": self._percentile(sorted_values, 50),
                "p90": self._percentile(sorted_values, 90),
                "p95": self._percentile(sorted_values, 95),
                "p99": self._percentile(sorted_values, 99)
            }
    
    def get_timer_stats(self, name: str, labels: Optional[Dict] = None) -> Optional[Dict]:
        """Get timer statistics (count, min, max, mean, median, p50, p90, p95, p99)."""
        with self._lock:
            key = self._make_key(name, labels)
            values = self._timers.get(key, [])
            if not values:
                return None
            sorted_values = sorted(values)
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "p50": self._percentile(sorted_values, 50),
                "p90": self._percentile(sorted_values, 90),
                "p95": self._percentile(sorted_values, 95),
                "p99": self._percentile(sorted_values, 99),
            }
    
    def get_all_metrics(self) -> Dict:
        """Get all current metrics"""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    k: self.get_histogram_stats(k.split(":")[0], self._parse_labels(k))
                    for k in self._histograms.keys()
                },
                "timers": {
                    k: self.get_timer_stats(k.split(":")[0], self._parse_labels(k))
                    for k in self._timers.keys()
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
    
    def get_agent_metrics(self, agent_name: str) -> Dict:
        """Get metrics for a specific agent"""
        with self._lock:
            metrics = {
                "agent": agent_name,
                "executions": self.get_counter(f"agent.executions.{agent_name}"),
                "successes": self.get_counter(f"agent.successes.{agent_name}"),
                "failures": self.get_counter(f"agent.failures.{agent_name}"),
                "duration_stats": self.get_timer_stats(f"agent.duration.{agent_name}")
            }
            
            # Calculate success rate
            total = metrics["executions"]
            if total > 0:
                metrics["success_rate"] = (metrics["successes"] / total) * 100
            else:
                metrics["success_rate"] = 0.0
            
            return metrics
    
    def get_build_metrics(self) -> Dict:
        """Get build-related metrics"""
        with self._lock:
            return {
                "total_builds": self.get_counter("builds.total"),
                "successful_builds": self.get_counter("builds.successful"),
                "failed_builds": self.get_counter("builds.failed"),
                "active_builds": self.get_gauge("builds.active"),
                "build_duration_stats": self.get_timer_stats("builds.duration"),
                "success_rate": self._calculate_success_rate(
                    self.get_counter("builds.successful"),
                    self.get_counter("builds.total")
                )
            }
    
    def get_system_health(self) -> Dict:
        """Get overall system health metrics"""
        with self._lock:
            build_metrics = self.get_build_metrics()
            
            # Determine health status
            success_rate = build_metrics.get("success_rate", 0)
            if success_rate >= 90:
                health = "healthy"
            elif success_rate >= 70:
                health = "degraded"
            else:
                health = "unhealthy"
            
            return {
                "status": health,
                "success_rate": success_rate,
                "active_builds": build_metrics.get("active_builds", 0),
                "total_builds": build_metrics.get("total_builds", 0),
                "uptime": self._calculate_uptime(),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
    
    def get_performance_report(self) -> Dict:
        """Generate comprehensive performance report"""
        with self._lock:
            # Agent performance
            agent_names = set()
            for key in self._counters.keys():
                if key.startswith("agent.executions."):
                    agent_name = key.split(".")[-1]
                    agent_names.add(agent_name)
            
            agent_reports = {
                agent: self.get_agent_metrics(agent)
                for agent in agent_names
            }
            
            # Build performance
            build_report = self.get_build_metrics()
            
            # Problem resolution metrics
            resolution_metrics = {
                "total_issues_detected": self.get_counter("resolver.issues.detected"),
                "total_issues_resolved": self.get_counter("resolver.issues.resolved"),
                "resolution_rate": self._calculate_success_rate(
                    self.get_counter("resolver.issues.resolved"),
                    self.get_counter("resolver.issues.detected")
                )
            }
            
            # Test metrics
            test_metrics = {
                "total_test_runs": self.get_counter("tester.runs.total"),
                "tests_passed": self.get_counter("tester.tests.passed"),
                "tests_failed": self.get_counter("tester.tests.failed")
            }
            
            return {
                "agents": agent_reports,
                "builds": build_report,
                "problem_resolution": resolution_metrics,
                "testing": test_metrics,
                "system_health": self.get_system_health(),
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
    
    def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        with self._lock:
            # Export counters
            for key, value in self._counters.items():
                name, labels = self._split_key(key)
                label_str = self._format_prometheus_labels(labels)
                lines.append(f"{name}{label_str} {value}")
            
            # Export gauges
            for key, value in self._gauges.items():
                name, labels = self._split_key(key)
                label_str = self._format_prometheus_labels(labels)
                lines.append(f"{name}{label_str} {value}")
        
        return "\n".join(lines)
    
    def reset_metrics(self):
        """Reset all metrics"""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timers.clear()
            self._metric_history.clear()
    
    def export_to_file(self, filename: Optional[str] = None):
        """Export metrics to JSON file"""
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"metrics_{timestamp}.json"
        
        filepath = self.storage_path / filename
        
        with self._lock:
            metrics_data = self.get_all_metrics()
            metrics_data["performance_report"] = self.get_performance_report()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(metrics_data, f, indent=2)
        
        return str(filepath)
    
    def get_time_series(
        self,
        metric_name: str,
        duration_minutes: int = 60
    ) -> List[Dict]:
        """Get time series data for a metric"""
        cutoff = datetime.utcnow() - timedelta(minutes=duration_minutes)
        
        with self._lock:
            return [
                m.to_dict()
                for m in self._metric_history
                if m.name == metric_name and m.timestamp >= cutoff
            ]
    
    def _record_metric(self, metric: Metric):
        """Record metric in history"""
        self._metric_history.append(metric)
        
        # Trim history if needed
        if len(self._metric_history) > self._max_history:
            self._metric_history = self._metric_history[-self._max_history:]
    
    def _make_key(self, name: str, labels: Optional[Dict]) -> str:
        """Create key from name and labels"""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}:{label_str}"
    
    def _split_key(self, key: str) -> tuple:
        """Split key into name and labels"""
        if ":" not in key:
            return key, {}
        
        name, label_str = key.split(":", 1)
        labels = {}
        for pair in label_str.split(","):
            k, v = pair.split("=", 1)
            labels[k] = v
        
        return name, labels
    
    def _parse_labels(self, key: str) -> Optional[Dict]:
        """Parse labels from key"""
        _, labels = self._split_key(key)
        return labels if labels else None
    
    def _format_prometheus_labels(self, labels: Dict) -> str:
        """Format labels for Prometheus"""
        if not labels:
            return ""
        
        label_pairs = [f'{k}="{v}"' for k, v in labels.items()]
        return "{" + ",".join(label_pairs) + "}"
    
    def _percentile(self, sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile from sorted values"""
        if not sorted_values:
            return 0.0
        
        index = (percentile / 100) * (len(sorted_values) - 1)
        lower = int(index)
        upper = min(lower + 1, len(sorted_values) - 1)
        weight = index - lower
        
        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight
    
    def _calculate_success_rate(self, successes: float, total: float) -> float:
        """Calculate success rate percentage"""
        if total == 0:
            return 0.0
        return (successes / total) * 100
    
    def _calculate_uptime(self) -> str:
        """Calculate system uptime"""
        # This is a placeholder - in production, track actual start time
        return "N/A"


# Global metrics collector instance
_global_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector"""
    global _global_metrics_collector
    if _global_metrics_collector is None:
        _global_metrics_collector = MetricsCollector()
    return _global_metrics_collector
