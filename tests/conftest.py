"""
Pytest configuration and shared fixtures
"""
import os
import sys
import pytest
from pathlib import Path

# Set environment variables before importing any modules
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("USE_FAKE_WORKFLOW", "1")

# Ensure coordinator dir is on sys.path
COORDINATOR_DIR = Path(__file__).resolve().parents[1] / "coordinator"
if str(COORDINATOR_DIR) not in sys.path:
    sys.path.insert(0, str(COORDINATOR_DIR))


@pytest.fixture
def client():
    """Shared test client fixture"""
    from fastapi.testclient import TestClient
    import main as appmod
    
    # Return test client
    return TestClient(appmod.app)
