import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure required env exists before importing the app module
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("USE_FAKE_WORKFLOW", "1")

# Ensure 'coordinator' dir is on sys.path so 'workflows' and 'config' imports inside main.py resolve
COORDINATOR_DIR = Path(__file__).resolve().parents[2] / "coordinator"
sys.path.insert(0, str(COORDINATOR_DIR))

from fastapi.testclient import TestClient  # noqa: E402
import main as appmod  # type: ignore  # noqa: E402


class FakeWorkflow:
    def __init__(self):
        self._builds: Dict[str, Dict[str, Any]] = {}

    async def build_from_brief(self, description: str, name: Optional[str] = None, requirements: Optional[List[str]] = None) -> dict:
        if not description or not description.strip():
            # Simulate validation error similar to real workflow
            raise ValueError("Project description cannot be empty")
        build_id = str(uuid.uuid4())
        project_name = name or "test-app"
        self._builds[build_id] = {
            "build_id": build_id,
            "project_name": project_name,
            "build_status": "success",
            "progress": 100,
            "current_step": "Complete",
            "logs": [{"level": "success", "message": "Completed", "timestamp": "2025-01-01T00:00:00"}],
            "app_url": f"http://localhost:3000/{project_name}",
            "source_path": f"./generated/{project_name}",
        }
        return {
            "status": "success",
            "build_id": build_id,
            "message": "Application built successfully",
            "app_url": self._builds[build_id]["app_url"],
            "source_path": self._builds[build_id]["source_path"],
            "logs": self._builds[build_id]["logs"],
        }

    async def get_build_status(self, build_id: str) -> Optional[dict]:
        b = self._builds.get(build_id)
        if not b:
            return None
        return {
            "build_id": build_id,
            "status": b["build_status"],
            "progress": b["progress"],
            "current_step": b["current_step"],
            "logs": b["logs"],
        }

    async def list_builds(self) -> List[dict]:
        return [
            {
                "build_id": b_id,
                "project_name": b["project_name"],
                "status": b["build_status"],
                "progress": b["progress"],
            }
            for b_id, b in self._builds.items()
        ]

    async def delete_build(self, build_id: str) -> dict:
        if build_id in self._builds:
            del self._builds[build_id]
            return {"success": True, "message": "Build deleted"}
        return {"success": False, "message": "Build not found"}


# Patch the real workflow with a fake one to avoid external calls
appmod.workflow = FakeWorkflow()
client = TestClient(appmod.app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json().get("status") == "healthy"


def test_root():
    res = client.get("/")
    assert res.status_code == 200
    assert "service" in res.json()


def test_build_success():
    payload = {"description": "Build a simple notes app", "name": "unit-notes"}
    res = client.post("/api/build", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "build_id" in data
    assert data.get("app_url")
    assert data.get("source_path")


def test_build_invalid_request():
    payload = {"description": ""}
    res = client.post("/api/build", json=payload)
    # Depending on exception mapping, the app may return 400/422/500.
    assert res.status_code in (400, 422, 500)


def test_get_build_status_and_list():
    # Create a build first
    res = client.post("/api/build", json={"description": "Create a blog app"})
    assert res.status_code == 200
    build_id = res.json()["build_id"]

    # Status should reflect success
    st = client.get(f"/api/build/{build_id}/status")
    assert st.status_code == 200
    sdata = st.json()
    assert sdata["build_id"] == build_id
    assert sdata["status"] in ("success", "building", "failed")

    # List builds should include the created build
    lst = client.get("/api/builds")
    assert lst.status_code == 200
    builds = lst.json().get("builds", [])
    assert any(b.get("build_id") == build_id for b in builds)


def test_status_non_existent_build():
    res = client.get("/api/build/does-not-exist/status")
    assert res.status_code == 404


def test_delete_build():
    # Create a build
    res = client.post("/api/build", json={"description": "Create a todo app"})
    assert res.status_code == 200
    build_id = res.json()["build_id"]

    # Delete it
    d = client.delete(f"/api/build/{build_id}")
    assert d.status_code == 200
    assert d.json().get("success") is True

    # Deleting again should report not found but still 200 with success False
    d2 = client.delete(f"/api/build/{build_id}")
    assert d2.status_code == 200
    assert d2.json().get("success") is False
