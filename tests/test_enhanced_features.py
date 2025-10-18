"""
Comprehensive tests for enhanced features
Tests metrics, crash recovery, error handling, and observability
"""
import pytest
import json
import uuid
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# Test BuildRegistry
from services.build_registry import BuildRegistry


class TestBuildRegistry:
    """Test build registry functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.test_dir = Path("./test_artifacts")
        self.test_dir.mkdir(exist_ok=True)
        self.registry = BuildRegistry(self.test_dir)
    
    def teardown_method(self):
        """Cleanup test artifacts"""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_register_build(self):
        """Test build registration"""
        build_id = str(uuid.uuid4())
        metadata = {
            "build_id": build_id,
            "project_name": "test-app",
            "status": "building",
            "progress": 50
        }
        
        result = self.registry.register_build(metadata)
        assert result is True
        
        # Verify retrieval
        retrieved = self.registry.get(build_id)
        assert retrieved is not None
        assert retrieved["build_id"] == build_id
        assert retrieved["project_name"] == "test-app"
        assert "created_at" in retrieved
        assert "updated_at" in retrieved
    
    def test_update_build(self):
        """Test build updates"""
        build_id = str(uuid.uuid4())
        
        # Initial registration
        self.registry.register_build({
            "build_id": build_id,
            "project_name": "test-app",
            "status": "building",
            "progress": 50
        })
        
        # Update
        self.registry.register_build({
            "build_id": build_id,
            "status": "success",
            "progress": 100
        })
        
        # Verify update
        retrieved = self.registry.get(build_id)
        assert retrieved["status"] == "success"
        assert retrieved["progress"] == 100
        assert retrieved["project_name"] == "test-app"  # Original field preserved
    
    def test_remove_build(self):
        """Test build removal"""
        build_id = str(uuid.uuid4())
        
        self.registry.register_build({
            "build_id": build_id,
            "project_name": "test-app"
        })
        
        result = self.registry.remove(build_id)
        assert result is True
        
        retrieved = self.registry.get(build_id)
        assert retrieved is None
    
    def test_search_builds(self):
        """Test build search"""
        # Register multiple builds
        for i in range(5):
            self.registry.register_build({
                "build_id": str(uuid.uuid4()),
                "project_name": f"test-app-{i}",
                "status": "success" if i % 2 == 0 else "failed"
            })
        
        # Search by status
        success_builds = self.registry.search(status="success")
        assert len(success_builds) == 3
        
        # Search by project name
        project_builds = self.registry.search(project_name="test-app-2")
        assert len(project_builds) == 1
        assert project_builds[0]["project_name"] == "test-app-2"
    
    def test_get_stats(self):
        """Test registry statistics"""
        # Register builds with different statuses
        for i in range(3):
            self.registry.register_build({
                "build_id": str(uuid.uuid4()),
                "project_name": f"app-{i}",
                "status": "success"
            })
        
        for i in range(2):
            self.registry.register_build({
                "build_id": str(uuid.uuid4()),
                "project_name": f"app-fail-{i}",
                "status": "failed"
            })
        
        stats = self.registry.get_stats()
        
        assert stats["total_builds"] == 5
        assert stats["by_status"]["success"] == 3
        assert stats["by_status"]["failed"] == 2
        assert len(stats["recent_builds"]) == 5


# Test MetricsCollector
from services.metrics_collector import MetricsCollector


class TestMetricsCollector:
    """Test metrics collection functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.test_dir = Path("./test_metrics")
        self.test_dir.mkdir(exist_ok=True)
        self.collector = MetricsCollector(self.test_dir)
    
    def teardown_method(self):
        """Cleanup test artifacts"""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_counter_increment(self):
        """Test counter increments"""
        self.collector.increment_counter("test.counter", 5.0)
        self.collector.increment_counter("test.counter", 3.0)
        
        value = self.collector.get_counter("test.counter")
        assert value == 8.0
    
    def test_gauge_set(self):
        """Test gauge values"""
        self.collector.set_gauge("test.gauge", 42.0)
        value = self.collector.get_gauge("test.gauge")
        assert value == 42.0
        
        self.collector.set_gauge("test.gauge", 100.0)
        value = self.collector.get_gauge("test.gauge")
        assert value == 100.0
    
    def test_histogram_observations(self):
        """Test histogram observations"""
        values = [10, 20, 30, 40, 50]
        for v in values:
            self.collector.observe_histogram("test.histogram", float(v))
        
        stats = self.collector.get_histogram_stats("test.histogram")
        assert stats["count"] == 5
        assert stats["mean"] == 30.0
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
    
    def test_duration_recording(self):
        """Test duration recording"""
        durations = [1.5, 2.0, 1.8, 2.2, 1.7]
        for d in durations:
            self.collector.record_duration("test.duration", d)
        
        stats = self.collector.get_timer_stats("test.duration")
        assert stats["count"] == 5
        assert abs(stats["mean"] - 1.84) < 0.01
    
    def test_labels(self):
        """Test metrics with labels"""
        self.collector.increment_counter(
            "http.requests",
            labels={"method": "GET", "endpoint": "/api/build"}
        )
        self.collector.increment_counter(
            "http.requests",
            labels={"method": "POST", "endpoint": "/api/build"}
        )
        
        get_count = self.collector.get_counter(
            "http.requests",
            labels={"method": "GET", "endpoint": "/api/build"}
        )
        post_count = self.collector.get_counter(
            "http.requests",
            labels={"method": "POST", "endpoint": "/api/build"}
        )
        
        assert get_count == 1.0
        assert post_count == 1.0
    
    def test_prometheus_export(self):
        """Test Prometheus format export"""
        self.collector.increment_counter("test_counter", 10.0)
        self.collector.set_gauge("test_gauge", 50.0)
        
        prometheus_output = self.collector.export_prometheus_format()
        
        assert "test_counter" in prometheus_output
        assert "test_gauge" in prometheus_output
        assert "10" in prometheus_output or "10.0" in prometheus_output
        assert "50" in prometheus_output or "50.0" in prometheus_output
    
    def test_performance_report(self):
        """Test performance report generation"""
        # Simulate some metrics
        self.collector.increment_counter("builds.total", 10.0)
        self.collector.increment_counter("builds.successful", 8.0)
        self.collector.record_duration("builds.duration", 120.0)
        self.collector.record_duration("builds.duration", 150.0)
        
        report = self.collector.get_performance_report()
        
        assert "builds" in report
        assert "system_health" in report
        assert "generated_at" in report


# Test Error Handler Middleware
from services.error_handler_middleware import ErrorHandlerMiddleware, ErrorCategory
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


class TestErrorHandlerMiddleware:
    """Test error handling middleware"""
    
    def setup_method(self):
        """Setup test FastAPI app"""
        self.app = FastAPI()
        
        @self.app.get("/test/success")
        async def success():
            return {"status": "ok"}
        
        @self.app.get("/test/validation-error")
        async def validation_error():
            raise HTTPException(status_code=400, detail="Invalid input")
        
        @self.app.get("/test/not-found")
        async def not_found():
            raise HTTPException(status_code=404, detail="Resource not found")
        
        @self.app.get("/test/internal-error")
        async def internal_error():
            raise Exception("Internal server error")
        
        # Add middleware
        self.app.add_middleware(
            ErrorHandlerMiddleware,
            debug=True,
            metrics_enabled=False,
            audit_enabled=False
        )
        
        self.client = TestClient(self.app)
    
    def test_successful_request(self):
        """Test successful request passes through"""
        response = self.client.get("/test/success")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    
    def test_validation_error(self):
        """Test validation error handling"""
        response = self.client.get("/test/validation-error")
        assert response.status_code == 400
        
        data = response.json()
        assert "error" in data
        assert "request_id" in data["error"]
        assert "timestamp" in data["error"]
    
    def test_not_found_error(self):
        """Test not found error handling"""
        response = self.client.get("/test/not-found")
        assert response.status_code == 404
        
        data = response.json()
        assert "error" in data
    
    def test_internal_error(self):
        """Test internal error handling"""
        response = self.client.get("/test/internal-error")
        assert response.status_code == 500
        
        data = response.json()
        assert "error" in data
        assert "stack_trace" in data["error"]  # Debug mode


# Integration Test for Enhanced Workflow
@pytest.mark.asyncio
class TestEnhancedWorkflowIntegration:
    """Integration tests for enhanced workflow features"""
    
    @pytest.mark.skipif(
        not Path("services/enhanced_state_manager.py").exists(),
        reason="Enhanced state manager not available"
    )
    async def test_state_persistence(self):
        """Test state persistence across workflow steps"""
        from services.enhanced_state_manager import EnhancedStateManager
        
        test_dir = Path("./test_state")
        test_dir.mkdir(exist_ok=True)
        
        try:
            manager = EnhancedStateManager(test_dir)
            
            build_id = str(uuid.uuid4())
            initial_state = {
                "build_id": build_id,
                "status": "building",
                "progress": 0
            }
            
            # Save initial state
            manager.save_state(build_id, initial_state)
            
            # Retrieve and verify
            retrieved = manager.get_state(build_id)
            assert retrieved is not None
            assert retrieved["build_id"] == build_id
            assert retrieved["status"] == "building"
            
            # Update state
            updated_state = {**retrieved, "progress": 50}
            manager.save_state(build_id, updated_state)
            
            # Verify update
            final_state = manager.get_state(build_id)
            assert final_state["progress"] == 50
            
        finally:
            import shutil
            if test_dir.exists():
                shutil.rmtree(test_dir)
    
    @pytest.mark.skipif(
        not Path("services/error_feedback_system.py").exists(),
        reason="Error feedback system not available"
    )
    async def test_error_feedback_tracking(self):
        """Test error feedback system"""
        from services.error_feedback_system import ErrorFeedbackSystem
        
        test_dir = Path("./test_feedback")
        test_dir.mkdir(exist_ok=True)
        
        try:
            feedback = ErrorFeedbackSystem(test_dir)
            
            # Record some errors
            feedback.record_error(
                build_id="build-1",
                error_category="syntax_error",
                error_message="Missing semicolon",
                context={"file": "app.py", "line": 42},
                resolution_attempted=True,
                resolution_successful=True
            )
            
            feedback.record_error(
                build_id="build-2",
                error_category="syntax_error",
                error_message="Missing semicolon",
                context={"file": "main.py", "line": 10},
                resolution_attempted=True,
                resolution_successful=False
            )
            
            # Get analytics
            analytics = feedback.get_error_analytics()
            
            assert analytics["total_errors"] >= 2
            assert "by_category" in analytics
            assert "syntax_error" in analytics["by_category"]
            
        finally:
            import shutil
            if test_dir.exists():
                shutil.rmtree(test_dir)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
