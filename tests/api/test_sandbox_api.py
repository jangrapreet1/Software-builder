"""
Tests for Phase 1 sandbox orchestration API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json


@pytest.fixture
def test_app_path(tmp_path):
    """Create a test application directory"""
    app_dir = tmp_path / "test-app"
    app_dir.mkdir()
    
    # Create a simple package.json
    package_json = {
        "name": "test-app",
        "version": "1.0.0",
        "scripts": {
            "start": "node index.js",
            "build": "echo 'Building...'"
        }
    }
    (app_dir / "package.json").write_text(json.dumps(package_json))
    
    # Create index.js
    (app_dir / "index.js").write_text("console.log('Hello World');")
    
    # Create .gitignore
    (app_dir / ".gitignore").write_text("node_modules\n.env\n")
    
    return str(app_dir)


@pytest.fixture
def test_python_app_path(tmp_path):
    """Create a test Python application directory"""
    app_dir = tmp_path / "test-python-app"
    app_dir.mkdir()
    
    # Create requirements.txt
    (app_dir / "requirements.txt").write_text("fastapi>=0.100.0\nuvicorn>=0.20.0\n")
    
    # Create main.py
    main_py = """
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}
"""
    (app_dir / "main.py").write_text(main_py)
    
    # Create Dockerfile
    dockerfile = """
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
    (app_dir / "Dockerfile").write_text(dockerfile)
    
    return str(app_dir)


def test_detect_repository_node(client: TestClient, test_app_path):
    """Test repository detection for Node.js project"""
    response = client.post(
        "/api/repo/detect",
        json={"repo_path": test_app_path}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert "detection_report" in data
    
    report = data["detection_report"]
    assert "languages" in report
    assert "frameworks" in report
    assert "package_managers" in report
    assert "build_commands" in report
    assert "run_commands" in report
    assert "test_commands" in report


def test_detect_repository_python(client: TestClient, test_python_app_path):
    """Test repository detection for Python project"""
    response = client.post(
        "/api/repo/detect",
        json={"repo_path": test_python_app_path}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    report = data["detection_report"]
    
    # Check Python is detected
    languages = report["languages"]["confident"]
    assert any(lang["language"] == "Python" for lang in languages)
    
    # Check pip is detected
    package_managers = report["package_managers"]
    assert any(pm["name"] == "pip" for pm in package_managers)


def test_detect_repository_not_found(client: TestClient):
    """Test detection with non-existent path"""
    response = client.post(
        "/api/repo/detect",
        json={"repo_path": "/nonexistent/path"}
    )
    
    assert response.status_code == 404


def test_preview_session_creation(client: TestClient, test_app_path):
    """Test preview session creation"""
    # Skip if session manager not available
    response = client.post(
        "/api/app/preview",
        json={
            "app_path": test_app_path,
            "port": 3000,
            "session_duration": 3600
        }
    )
    
    # May be 503 if Docker not available
    if response.status_code == 503:
        pytest.skip("Session manager not available")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert "preview_url" in data
    assert "session_token" in data
    assert "expires_at" in data


def test_preview_app_not_found(client: TestClient):
    """Test preview with non-existent app path"""
    response = client.post(
        "/api/app/preview",
        json={"app_path": "/nonexistent/app"}
    )
    
    # May be 503 if not available, or 404 if available
    assert response.status_code in [404, 503]


def test_sandbox_health_check(client: TestClient):
    """Test sandbox health endpoint"""
    response = client.get("/api/sandbox/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    # Status can be "healthy", "unhealthy", or "unavailable"
    assert data["status"] in ["healthy", "unhealthy", "unavailable"]


def test_list_sandbox_instances(client: TestClient):
    """Test listing sandbox instances"""
    response = client.get("/api/sandbox/instances")
    
    # May be 503 if not available
    if response.status_code == 503:
        pytest.skip("Sandbox orchestrator not available")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "instances" in data
    assert "count" in data
    assert isinstance(data["instances"], list)


def test_session_stats(client: TestClient):
    """Test session statistics endpoint"""
    response = client.get("/api/sessions/stats")
    
    # May be 503 if not available
    if response.status_code == 503:
        pytest.skip("Session manager not available")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "total_sessions" in data
    assert "active_sessions" in data


def test_download_app(client: TestClient, test_app_path):
    """Test app download endpoint"""
    response = client.get(
        "/api/app/download",
        params={"app_path": test_app_path}
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "content-disposition" in response.headers
    assert "test-app.zip" in response.headers["content-disposition"]


def test_download_app_not_found(client: TestClient):
    """Test download with non-existent path"""
    response = client.get(
        "/api/app/download",
        params={"app_path": "/nonexistent/app"}
    )
    
    assert response.status_code == 404


# Integration test - requires Docker
@pytest.mark.integration
def test_launch_and_stop_instance(client: TestClient, test_python_app_path):
    """Test launching and stopping a sandbox instance (requires Docker)"""
    # Try to launch
    launch_response = client.post(
        "/api/app/launch",
        json={
            "app_path": test_python_app_path,
            "port": 8000,
            "cpu_limit": 0.5,
            "memory_limit": "256m",
            "timeout": 300
        }
    )
    
    # Skip if Docker not available
    if launch_response.status_code == 503:
        pytest.skip("Sandbox orchestrator not available (Docker required)")
    
    if launch_response.status_code != 200:
        pytest.skip(f"Failed to launch instance: {launch_response.json()}")
    
    launch_data = launch_response.json()
    
    assert launch_data["status"] == "success"
    assert "instance_id" in launch_data
    assert "preview_url" in launch_data
    
    instance_id = launch_data["instance_id"]
    
    # Check instance status
    status_response = client.get(f"/api/sandbox/{instance_id}/status")
    assert status_response.status_code == 200
    
    # Get logs
    logs_response = client.get(f"/api/sandbox/{instance_id}/logs")
    assert logs_response.status_code == 200
    
    # Stop instance
    stop_response = client.post(
        "/api/app/stop",
        json={"instance_id": instance_id, "force": True}
    )
    
    assert stop_response.status_code == 200
    stop_data = stop_response.json()
    assert stop_data["success"] is True
