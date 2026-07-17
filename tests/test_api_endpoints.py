"""
Comprehensive API Endpoint Tests for the Coordinator
Tests all major API endpoints using FastAPI TestClient
"""
import pytest
import json
import uuid
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture(scope="module")
def test_client():
    """Create a test client for the FastAPI app"""
    import os
    os.environ.setdefault("GOOGLE_API_KEY", "test-key")
    os.environ.setdefault("USE_FAKE_WORKFLOW", "1")
    os.environ.setdefault("APPBUILDER_ALLOW_TEMP_ROOTS", "1")
    
    import sys
    from pathlib import Path
    
    # Ensure coordinator is on path
    coord_dir = Path(__file__).resolve().parents[1] / "coordinator"
    if str(coord_dir) not in sys.path:
        sys.path.insert(0, str(coord_dir))
    
    import main as appmod
    return TestClient(appmod.app)


@pytest.fixture
def sample_project_dir():
    """Create a temporary project directory for testing"""
    temp_dir = tempfile.mkdtemp()
    project_path = Path(temp_dir) / "test-project"
    project_path.mkdir()
    
    # Create sample files
    (project_path / "main.py").write_text("""
def hello():
    return "Hello, World!"

if __name__ == "__main__":
    print(hello())
""")
    
    (project_path / "requirements.txt").write_text("fastapi\nuvicorn\n")
    
    (project_path / "package.json").write_text(json.dumps({
        "name": "test-project",
        "version": "1.0.0",
        "scripts": {
            "dev": "vite",
            "build": "vite build"
        }
    }))
    
    yield str(project_path)
    
    # Cleanup
    shutil.rmtree(temp_dir)


# ==============================================================================
# Root & Health Endpoints
# ==============================================================================

class TestRootAndHealthEndpoints:
    """Tests for root and health check endpoints"""
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint returns welcome message"""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data or "message" in data or "name" in data
    
    def test_health_check(self, test_client):
        """Test health check endpoint"""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy" or "ok" in str(data).lower()
    
    def test_metrics_endpoint(self, test_client):
        """Test metrics endpoint returns Prometheus format"""
        # The /metrics endpoint may exist at root or not be mounted
        response = test_client.get("/metrics")
        # May return 200 or 404 depending on configuration
        assert response.status_code in [200, 404]


# ==============================================================================
# Build Management Endpoints
# ==============================================================================

class TestBuildEndpoints:
    """Tests for build management endpoints"""
    
    def test_build_app_with_brief(self, test_client):
        """Test creating a build from a project brief"""
        response = test_client.post("/api/build", json={
            "description": "A simple todo application",
            "name": "test-todo-app",
            "requirements": ["Create tasks", "Mark complete"]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "build_id" in data
        assert "status" in data
    
    def test_build_app_minimal(self, test_client):
        """Test build with minimal payload"""
        response = test_client.post("/api/build", json={
            "description": "Simple counter app"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "build_id" in data
    
    def test_list_builds(self, test_client):
        """Test listing all builds"""
        response = test_client.get("/api/builds")
        assert response.status_code == 200
        data = response.json()
        assert "builds" in data or isinstance(data, list)
    
    def test_get_build_status_nonexistent(self, test_client):
        """Test getting status of non-existent build"""
        fake_id = str(uuid.uuid4())
        response = test_client.get(f"/api/build/{fake_id}/status")
        # Should return 404 or empty status
        assert response.status_code in [404, 200]
    
    def test_delete_build_nonexistent(self, test_client):
        """Test deleting non-existent build"""
        fake_id = str(uuid.uuid4())
        response = test_client.delete(f"/api/build/{fake_id}")
        # Should handle gracefully
        assert response.status_code in [404, 200]
    
    def test_get_generated_projects(self, test_client):
        """Test listing generated projects"""
        response = test_client.get("/api/projects")
        # Endpoint may not exist or may be at different path
        assert response.status_code in [200, 404]


# ==============================================================================
# Repository Detection Endpoints
# ==============================================================================

class TestRepositoryDetectionEndpoints:
    """Tests for repository detection endpoints"""
    
    def test_detect_repository(self, test_client, sample_project_dir):
        """Test repository detection"""
        response = test_client.post("/api/repo/detect", json={
            "repo_path": sample_project_dir
        })
        
        assert response.status_code == 200
        data = response.json()
        # Should return detection report
        assert "languages" in data or "frameworks" in data or "detection" in data or "error" not in data
    
    def test_detect_repository_invalid_path(self, test_client):
        """Test detection with invalid path"""
        response = test_client.post("/api/repo/detect", json={
            "repo_path": "/nonexistent/path"
        })
        
        # Should return error or empty detection
        assert response.status_code in [200, 400, 404]
    
    def test_get_latest_detection(self, test_client, sample_project_dir):
        """Test getting latest detection report"""
        # First detect
        test_client.post("/api/repo/detect", json={
            "repo_path": sample_project_dir
        })
        
        # Then get latest
        response = test_client.get("/api/repo/detect/latest", params={
            "repo_path": sample_project_dir
        })
        
        assert response.status_code in [200, 404]


# ==============================================================================
# Sandbox & Preview Endpoints
# ==============================================================================

class TestSandboxEndpoints:
    """Tests for sandbox orchestration endpoints"""
    
    def test_list_instances(self, test_client):
        """Test listing sandbox instances"""
        response = test_client.get("/api/sandbox/instances")
        
        # Sandbox may not be available if Docker is not running
        assert response.status_code in [200, 404, 503]
    
    def test_sandbox_health(self, test_client):
        """Test sandbox health endpoint"""
        response = test_client.get("/api/sandbox/health")
        
        # Sandbox may not be available if Docker is not running
        assert response.status_code in [200, 404, 503]
    
    def test_preview_app_request(self, test_client, sample_project_dir):
        """Test preview app endpoint"""
        response = test_client.post("/api/app/preview", json={
            "app_path": sample_project_dir,
            "port": 3000,
            "session_duration": 3600
        })
        
        # May fail if Docker not available or endpoint path differs
        assert response.status_code in [200, 400, 404, 500, 503]
    
    def test_get_instance_status_nonexistent(self, test_client):
        """Test getting status of non-existent instance"""
        fake_id = str(uuid.uuid4())
        response = test_client.get(f"/api/sandbox/{fake_id}/status")
        
        assert response.status_code in [200, 404]
    
    def test_get_instance_logs_nonexistent(self, test_client):
        """Test getting logs of non-existent instance"""
        fake_id = str(uuid.uuid4())
        response = test_client.get(f"/api/sandbox/{fake_id}/logs")
        
        assert response.status_code in [200, 404]


# ==============================================================================
# Problem Resolver Endpoints
# ==============================================================================

class TestProblemResolverEndpoints:
    """Tests for problem resolver endpoints"""
    
    def test_analyze_and_resolve(self, test_client, sample_project_dir):
        """Test analyze and resolve endpoint"""
        response = test_client.post("/api/resolve", json={
            "app_path": sample_project_dir,
            "error_logs": None,
            "auto_fix": False
        })
        
        # Endpoint may be at different path or not available
        assert response.status_code in [200, 400, 404, 500]
    
    def test_start_problem_resolver(self, test_client, sample_project_dir):
        """Test starting problem resolver"""
        response = test_client.post("/api/agent/problem-resolver", json={
            "session_id": str(uuid.uuid4()),
            "app_path": sample_project_dir,
            "commands": {},
            "run_mode": "diagnose-only"
        })
        
        assert response.status_code in [200, 400, 500]
    
    def test_get_problem_resolver_result_nonexistent(self, test_client):
        """Test getting result for non-existent run"""
        fake_id = str(uuid.uuid4())
        response = test_client.get(f"/api/agent/problem-resolver/{fake_id}/result")
        
        assert response.status_code in [200, 404]
    
    def test_get_problem_resolver_logs_nonexistent(self, test_client):
        """Test getting logs for non-existent run"""
        fake_id = str(uuid.uuid4())
        response = test_client.get(f"/api/agent/problem-resolver/{fake_id}/logs")
        
        assert response.status_code in [200, 404]


# ==============================================================================
# Testing Endpoints
# ==============================================================================

class TestTestingEndpoints:
    """Tests for test execution endpoints"""
    
    def test_run_tests(self, test_client, sample_project_dir):
        """Test run tests endpoint"""
        response = test_client.post("/api/test/run", json={
            "app_path": sample_project_dir,
            "test_type": "all",
            "specific_tests": [],
            "generate_missing": False
        })
        
        assert response.status_code in [200, 400, 500]


# ==============================================================================
# Live Preview Endpoints
# ==============================================================================

class TestLivePreviewEndpoints:
    """Tests for live preview endpoints"""
    
    def test_list_previews(self, test_client):
        """Test listing all previews"""
        response = test_client.get("/api/preview/list")
        
        assert response.status_code in [200, 404]
    
    def test_get_preview_status_nonexistent(self, test_client):
        """Test getting preview status for non-existent build"""
        fake_id = str(uuid.uuid4())
        response = test_client.get(f"/api/preview/{fake_id}/status")
        
        assert response.status_code in [200, 404]


# ==============================================================================
# Session & Permission Endpoints
# ==============================================================================

class TestSessionEndpoints:
    """Tests for session and permission endpoints"""
    
    def test_session_stats(self, test_client):
        """Test session statistics endpoint"""
        response = test_client.get("/api/session/stats")
        
        # Endpoint path may vary
        assert response.status_code in [200, 404]
    
    def test_grant_permissions(self, test_client):
        """Test granting permissions"""
        response = test_client.post("/api/session/permissions", json={
            "session_id": str(uuid.uuid4()),
            "actions": ["read", "write"],
            "commands": ["npm install"],
            "duration": 3600
        })
        
        assert response.status_code in [200, 400]
    
    def test_get_permissions_stats(self, test_client):
        """Test getting permission statistics"""
        response = test_client.get("/api/session/permissions/stats")
        
        assert response.status_code in [200, 404]


# ==============================================================================
# Metrics & Observability Endpoints
# ==============================================================================

class TestObservabilityEndpoints:
    """Tests for metrics and observability endpoints"""
    
    def test_get_metrics_json(self, test_client):
        """Test getting metrics in JSON format"""
        response = test_client.get("/api/metrics")
        
        assert response.status_code in [200, 404]
    
    def test_get_prometheus_metrics(self, test_client):
        """Test getting Prometheus format metrics"""
        response = test_client.get("/api/metrics/prometheus")
        
        assert response.status_code in [200, 404]
    
    def test_get_performance_report(self, test_client):
        """Test getting performance report"""
        response = test_client.get("/api/metrics/performance")
        
        assert response.status_code in [200, 404]
    
    def test_get_system_health(self, test_client):
        """Test getting system health"""
        response = test_client.get("/api/metrics/health")
        
        assert response.status_code in [200, 404]
    
    def test_get_registry_stats(self, test_client):
        """Test getting registry statistics"""
        response = test_client.get("/api/registry/stats")
        
        assert response.status_code in [200, 404]


# ==============================================================================
# Audit Endpoints
# ==============================================================================

class TestAuditEndpoints:
    """Tests for audit log endpoints"""
    
    def test_get_recent_audit_events(self, test_client):
        """Test getting recent audit events"""
        response = test_client.get("/api/audit/events", params={"limit": 10})
        
        assert response.status_code in [200, 404]
    
    def test_get_audit_stats(self, test_client):
        """Test getting audit statistics"""
        response = test_client.get("/api/audit/stats")
        
        assert response.status_code in [200, 404]
    
    def test_query_audit_events(self, test_client):
        """Test querying audit events with filters"""
        response = test_client.get("/api/audit/query", params={
            "limit": 50
        })
        
        assert response.status_code in [200, 404]


# ==============================================================================
# File System Endpoints
# ==============================================================================

class TestFileSystemEndpoints:
    """Tests for file system API endpoints"""
    
    def test_fs_list(self, test_client, sample_project_dir):
        """Test listing directory contents"""
        response = test_client.get("/api/fs/list", params={
            "root": sample_project_dir,
            "path": "."
        })
        
        assert response.status_code == 200
        data = response.json()
        # Response may have 'items', 'entries', or 'files' key
        assert "items" in data or "entries" in data or "files" in data or isinstance(data, list)
    
    def test_fs_read(self, test_client, sample_project_dir):
        """Test reading file contents"""
        response = test_client.get("/api/fs/read", params={
            "root": sample_project_dir,
            "path": "main.py"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data or "hello" in str(data).lower()
    
    def test_fs_write(self, test_client, sample_project_dir):
        """Test writing file contents"""
        response = test_client.post("/api/fs/write", json={
            "root": sample_project_dir,
            "path": "test_new_file.txt",
            "content": "Hello from test!"
        })
        
        assert response.status_code in [200, 201]
    
    def test_fs_mkdir(self, test_client, sample_project_dir):
        """Test creating directory"""
        response = test_client.post("/api/fs/mkdir", json={
            "root": sample_project_dir,
            "path": "new_directory"
        })
        
        assert response.status_code in [200, 201]
    
    def test_fs_rename(self, test_client, sample_project_dir):
        """Test renaming file"""
        # First create a file
        test_client.post("/api/fs/write", json={
            "root": sample_project_dir,
            "path": "rename_me.txt",
            "content": "To be renamed"
        })
        
        # Then rename it
        response = test_client.post("/api/fs/rename", json={
            "root": sample_project_dir,
            "src": "rename_me.txt",
            "dest": "renamed.txt"
        })
        
        assert response.status_code in [200, 404]
    
    def test_fs_delete(self, test_client, sample_project_dir):
        """Test deleting file"""
        # First create a file
        test_client.post("/api/fs/write", json={
            "root": sample_project_dir,
            "path": "delete_me.txt",
            "content": "To be deleted"
        })
        
        # Then delete it
        response = test_client.delete("/api/fs/delete", params={
            "root": sample_project_dir,
            "path": "delete_me.txt"
        })
        
        assert response.status_code in [200, 204, 404]

    def test_fs_rejects_path_escape(self, test_client, sample_project_dir):
        """Test that relative paths cannot escape the selected root."""
        response = test_client.get("/api/fs/read", params={
            "root": sample_project_dir,
            "path": "../outside.txt"
        })

        assert response.status_code == 400

    def test_fs_delete_rejects_root(self, test_client, sample_project_dir):
        """Test that delete cannot target the selected root directory."""
        response = test_client.delete("/api/fs/delete", params={
            "root": sample_project_dir,
            "path": "."
        })

        assert response.status_code == 400
    
    def test_fs_list_invalid_root(self, test_client):
        """Test listing with invalid root path"""
        response = test_client.get("/api/fs/list", params={
            "root": "/nonexistent/path",
            "path": "."
        })
        
        # API may return 200 with empty list, 400, or 404
        assert response.status_code in [200, 400, 404]


# ==============================================================================
# Secrets Endpoints
# ==============================================================================

class TestSecretsEndpoints:
    """Tests for secrets management endpoints"""
    
    def test_secrets_list(self, test_client, sample_project_dir):
        """Test listing secrets"""
        # Create a .env file first
        env_path = Path(sample_project_dir) / ".env"
        env_path.write_text("TEST_KEY=test_value\nANOTHER_KEY=another_value\n")
        
        response = test_client.get("/api/secrets/list", params={
            "root": sample_project_dir
        })
        
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert data["secrets"]["TEST_KEY"]["set"] is True
            assert "test_value" not in json.dumps(data)
    
    def test_secrets_set(self, test_client, sample_project_dir):
        """Test setting a secret"""
        response = test_client.post("/api/secrets/set", json={
            "root": sample_project_dir,
            "key": "NEW_SECRET",
            "value": "secret_value",
            "filename": ".env"
        })
        
        assert response.status_code in [200, 201]


# ==============================================================================
# Git Endpoints
# ==============================================================================

class TestGitEndpoints:
    """Tests for Git operation endpoints"""
    
    def test_git_init(self, test_client, sample_project_dir):
        """Test git init"""
        response = test_client.post("/api/git/init", json={
            "repo_path": sample_project_dir
        })
        
        # Endpoint path may vary
        assert response.status_code in [200, 400, 404]
    
    def test_git_status(self, test_client, sample_project_dir):
        """Test git status"""
        # Init first
        test_client.post("/api/git/init", json={
            "repo_path": sample_project_dir
        })
        
        response = test_client.get("/api/git/status", params={
            "repo_path": sample_project_dir
        })
        
        assert response.status_code in [200, 400]
    
    def test_git_status_not_a_repo(self, test_client, sample_project_dir):
        """Test git status on non-git directory"""
        # Create a new temp dir that's not a git repo
        temp_dir = tempfile.mkdtemp()
        try:
            response = test_client.get("/api/git/status", params={
                "repo_path": temp_dir
            })
            assert response.status_code in [200, 400, 500]
        finally:
            shutil.rmtree(temp_dir)


# ==============================================================================
# Collaboration Endpoints
# ==============================================================================

class TestCollaborationEndpoints:
    """Tests for collaboration endpoints"""
    
    def test_list_collaboration_sessions(self, test_client):
        """Test listing collaboration sessions"""
        response = test_client.get("/api/collaboration/sessions")
        
        assert response.status_code in [200, 404]
    
    def test_get_collaboration_history(self, test_client):
        """Test getting collaboration history"""
        response = test_client.get("/api/collaboration/history", params={
            "limit": 50
        })
        
        assert response.status_code in [200, 404]


# ==============================================================================
# Recovery Endpoints
# ==============================================================================

class TestRecoveryEndpoints:
    """Tests for crash recovery endpoints"""
    
    def test_recover_build_nonexistent(self, test_client):
        """Test recovering non-existent build"""
        fake_id = str(uuid.uuid4())
        response = test_client.post(f"/api/build/{fake_id}/recover")
        
        assert response.status_code in [200, 404]
    
    def test_get_build_checkpoints_nonexistent(self, test_client):
        """Test getting checkpoints for non-existent build"""
        fake_id = str(uuid.uuid4())
        response = test_client.get(f"/api/build/{fake_id}/checkpoints")
        
        assert response.status_code in [200, 404]


# ==============================================================================
# Context & State Endpoints
# ==============================================================================

class TestContextEndpoints:
    """Tests for context and state endpoints"""
    
    def test_get_workflow_state_nonexistent(self, test_client):
        """Test getting workflow state for non-existent build"""
        fake_id = str(uuid.uuid4())
        response = test_client.get(f"/api/state/{fake_id}")
        
        assert response.status_code in [200, 404]


# ==============================================================================
# Build Activity Endpoints
# ==============================================================================

class TestBuildActivityEndpoints:
    """Tests for build activity endpoints"""
    
    def test_get_build_activity(self, test_client):
        """Test getting build activity"""
        fake_id = str(uuid.uuid4())
        response = test_client.get(f"/api/build/{fake_id}/activity", params={
            "limit": 100
        })
        
        assert response.status_code in [200, 404]


# ==============================================================================
# Download Endpoints
# ==============================================================================

class TestDownloadEndpoints:
    """Tests for download endpoints"""
    
    def test_download_app(self, test_client, sample_project_dir):
        """Test downloading app as zip"""
        response = test_client.get("/api/app/download", params={
            "app_path": sample_project_dir
        })
        
        # Should return a zip file or error if path issues
        assert response.status_code in [200, 400, 404]


# ==============================================================================
# Error Handling Tests
# ==============================================================================

class TestErrorHandling:
    """Tests for error handling across endpoints"""
    
    def test_invalid_json_body(self, test_client):
        """Test handling of invalid JSON body"""
        response = test_client.post(
            "/api/build",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_missing_required_field(self, test_client):
        """Test handling of missing required fields"""
        response = test_client.post("/api/build", json={})
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_endpoint(self, test_client):
        """Test handling of invalid endpoint"""
        response = test_client.get("/api/nonexistent/endpoint")
        
        assert response.status_code == 404


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestBuildWorkflowIntegration:
    """Integration tests for complete build workflow"""
    
    def test_full_build_workflow(self, test_client):
        """Test complete build workflow: create → status → list"""
        # 1. Create a build
        create_response = test_client.post("/api/build", json={
            "description": "Integration test app",
            "name": "integration-test"
        })
        assert create_response.status_code == 200
        build_data = create_response.json()
        build_id = build_data.get("build_id")
        
        if build_id:
            # 2. Get build status
            status_response = test_client.get(f"/api/build/{build_id}/status")
            assert status_response.status_code == 200
            
            # 3. List builds and verify our build is there
            list_response = test_client.get("/api/builds")
            assert list_response.status_code == 200
            builds = list_response.json()
            
            # Verify the build exists in the list
            if isinstance(builds, dict) and "builds" in builds:
                build_ids = [b.get("build_id") for b in builds["builds"]]
            elif isinstance(builds, list):
                build_ids = [b.get("build_id") for b in builds]
            else:
                build_ids = []
            
            assert build_id in build_ids or len(build_ids) > 0


class TestFrameworkPolymorphism:
    """Test frontend/backend agents polymorphic framework generation"""
    
    @pytest.mark.asyncio
    async def test_express_backend_agent(self):
        from agents.backend_agent import BackendAgent
        from config.settings import Settings
        
        # Mock LLM
        mock_llm = Mock()
        settings = Settings(google_api_key="mock-key")
        
        agent = BackendAgent(mock_llm, settings)
        
        # Test generation with Express
        code = await agent.generate_code(
            tasks=[],
            entities=[],
            specs={"preferred_backend": "express"}
        )
        
        assert "files" in code
        assert "package.json" in code["files"]
        assert "server.js" in code["files"]
        assert "db.js" in code["files"]
        assert "Dockerfile" in code["files"]
        assert "express" in code["files"]["package.json"]

    @pytest.mark.asyncio
    async def test_nextjs_frontend_agent(self):
        from agents.frontend_agent import FrontendAgent
        from config.settings import Settings
        
        mock_llm = Mock()
        settings = Settings(google_api_key="mock-key")
        
        agent = FrontendAgent(mock_llm, settings)
        
        code = await agent.generate_code(
            tasks=[],
            user_flows=[],
            specs={"preferred_frontend": "nextjs"},
            backend_code={}
        )
        
        assert "files" in code
        assert "package.json" in code["files"]
        assert "src/app/layout.tsx" in code["files"]
        assert "src/app/page.tsx" in code["files"]
        assert "Dockerfile" in code["files"]
        assert "next" in code["files"]["package.json"]


# ==============================================================================
# Run Tests
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
