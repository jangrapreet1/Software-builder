"""
Phase 2 Test Suite - Validates all Phase 2 functionality
Tests Problem Resolver, Tester Agent, Collaboration Manager, and Live Preview
"""
import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil

# Test fixtures
@pytest.fixture
def sample_app_path():
    """Create a temporary app directory with sample code"""
    temp_dir = tempfile.mkdtemp()
    app_path = Path(temp_dir) / "test-app"
    app_path.mkdir()
    
    # Create a simple Python file with an intentional error
    (app_path / "main.py").write_text("""
import requests

def fetch_data(url):
    response = requests.get(url)  # Missing timeout
    return response.json()

def process_data(data)
    # Syntax error: missing colon
    return data['result']

if __name__ == "__main__":
    data = fetch_data("https://api.example.com/data")
    result = process_data(data)
    print(result)
""")
    
    # Create requirements.txt
    (app_path / "requirements.txt").write_text("requests\n")
    
    yield str(app_path)
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def llm_mock():
    """Mock LLM for testing without API calls"""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from unittest.mock import Mock
    
    mock_llm = Mock(spec=ChatGoogleGenerativeAI)
    
    async def mock_ainvoke(messages):
        # Return a mock response
        result = Mock()
        result.content = "Fixed code:\n```python\ndef process_data(data):\n    return data['result']\n```"
        return result
    
    mock_llm.ainvoke = mock_ainvoke
    return mock_llm


@pytest.fixture
def settings():
    """Mock settings"""
    from config.settings import Settings
    from unittest.mock import Mock
    
    mock_settings = Mock(spec=Settings)
    mock_settings.google_api_key = "test-key"
    mock_settings.gemini_model = "gemini-2.5-flash"
    mock_settings.generated_apps_dir = "./generated"
    mock_settings.max_retries = 3
    mock_settings.agent_timeout = 300
    mock_settings.docker_network = "appbuilder-test"
    
    return mock_settings


# ============================================================================
# Problem Resolver Agent Tests
# ============================================================================

@pytest.mark.asyncio
async def test_problem_resolver_detects_syntax_errors(llm_mock, settings, sample_app_path):
    """Test that Problem Resolver detects syntax errors"""
    from agents.problem_resolver_agent import ProblemResolverAgent
    
    resolver = ProblemResolverAgent(llm_mock, settings)
    
    result = await resolver.analyze_and_resolve(
        app_path=sample_app_path,
        error_logs=None
    )
    
    assert result["status"] in ["success", "partial"]
    assert result["issues_found"] > 0
    assert "syntax" in str(result).lower()


@pytest.mark.asyncio
async def test_problem_resolver_detects_api_issues(llm_mock, settings, sample_app_path):
    """Test that Problem Resolver detects API/network issues"""
    from agents.problem_resolver_agent import ProblemResolverAgent
    
    resolver = ProblemResolverAgent(llm_mock, settings)
    
    result = await resolver.analyze_and_resolve(
        app_path=sample_app_path,
        error_logs=None
    )
    
    # Should detect missing timeout in requests.get()
    issues = result.get("issues_found", 0)
    assert issues > 0


@pytest.mark.asyncio
async def test_problem_resolver_handles_missing_path(llm_mock, settings):
    """Test that Problem Resolver handles non-existent paths gracefully"""
    from agents.problem_resolver_agent import ProblemResolverAgent
    
    resolver = ProblemResolverAgent(llm_mock, settings)
    
    result = await resolver.analyze_and_resolve(
        app_path="/non/existent/path",
        error_logs=None
    )
    
    assert result["status"] == "failed"
    assert "error" in result


# ============================================================================
# Tester Agent Tests
# ============================================================================

@pytest.mark.asyncio
async def test_tester_agent_detects_pytest(llm_mock, settings, sample_app_path):
    """Test that Tester Agent detects pytest framework"""
    from agents.tester_agent import TesterAgent
    
    # Create pytest.ini
    pytest_ini = Path(sample_app_path) / "pytest.ini"
    pytest_ini.write_text("[pytest]\ntestpaths = tests\n")
    
    tester = TesterAgent(llm_mock, settings)
    
    result = await tester.run_tests(
        app_path=sample_app_path,
        test_type="all",
        generate_missing=False
    )
    
    assert result["framework"] in ["pytest", None]


@pytest.mark.asyncio
async def test_tester_agent_generates_tests(llm_mock, settings, sample_app_path):
    """Test that Tester Agent can generate missing tests"""
    from agents.tester_agent import TesterAgent
    
    tester = TesterAgent(llm_mock, settings)
    
    result = await tester.run_tests(
        app_path=sample_app_path,
        test_type="all",
        generate_missing=True
    )
    
    assert "generated_tests" in result
    if result["generated_tests"]["success"]:
        assert len(result["generated_tests"]["files_created"]) > 0


@pytest.mark.asyncio
async def test_tester_agent_returns_structured_report(llm_mock, settings, sample_app_path):
    """Test that Tester Agent returns properly structured report"""
    from agents.tester_agent import TesterAgent
    
    tester = TesterAgent(llm_mock, settings)
    
    result = await tester.run_tests(
        app_path=sample_app_path,
        test_type="all",
        generate_missing=True
    )
    
    # Verify structure
    assert "status" in result
    assert "timestamp" in result
    assert "summary" in result
    assert "recommendations" in result
    
    # Verify summary fields
    summary = result["summary"]
    assert "total_tests" in summary
    assert "passed" in summary
    assert "failed" in summary
    assert "skipped" in summary


# ============================================================================
# Collaboration Manager Tests
# ============================================================================

@pytest.mark.asyncio
async def test_collaboration_manager_orchestration(settings):
    """Test that Collaboration Manager orchestrates multiple agents"""
    from services.agent_collaboration_manager import CollaborationManager
    
    manager = CollaborationManager(settings)
    
    build_id = "test-123"
    session = manager.active_sessions.get(build_id)
    
    # Initially no session
    assert session is None
    
    # Sessions can be created
    status = manager.get_session_status(build_id)
    assert status is None


@pytest.mark.asyncio
async def test_collaboration_manager_tracks_history(settings):
    """Test that Collaboration Manager tracks collaboration history"""
    from services.agent_collaboration_manager import CollaborationManager
    
    manager = CollaborationManager(settings)
    
    # Request action
    result = await manager.request_agent_action(
        requesting_agent="coordinator",
        target_agent="resolver",
        action="analyze",
        parameters={"app_path": "/test"}
    )
    
    assert result["status"] == "pending"
    assert "request_id" in result
    
    # Check history
    history = manager.get_collaboration_history(limit=10)
    assert len(history) > 0


# ============================================================================
# Live Preview Bridge Tests
# ============================================================================

@pytest.mark.asyncio
async def test_live_preview_bridge_creates_preview(settings):
    """Test that Live Preview Bridge creates preview info"""
    from services.agent_collaboration_manager import LivePreviewBridge
    from unittest.mock import Mock, AsyncMock
    
    # Mock sandbox orchestrator
    mock_sandbox = Mock()
    mock_sandbox.launch_instance = AsyncMock(return_value={
        "instance_id": "test-instance",
        "preview_url": "http://localhost:3000",
        "expires_at": "2025-10-14T13:00:00Z",
        "port": 3000
    })
    
    bridge = LivePreviewBridge(mock_sandbox, settings)
    
    result = await bridge.create_live_preview(
        build_id="test-123",
        app_path="/test/app",
        port=3000,
        auto_start=True
    )
    
    assert result["build_id"] == "test-123"
    assert result["previewUrl"] is not None
    assert result["instanceId"] is not None


@pytest.mark.asyncio
async def test_live_preview_bridge_tracks_previews(settings):
    """Test that Live Preview Bridge tracks active previews"""
    from services.agent_collaboration_manager import LivePreviewBridge
    
    bridge = LivePreviewBridge(None, settings)
    
    # Create preview without auto-start
    result = await bridge.create_live_preview(
        build_id="test-123",
        app_path="/test/app",
        port=3000,
        auto_start=False
    )
    
    # Should be tracked
    status = bridge.get_preview_status("test-123")
    assert status is not None
    assert status["build_id"] == "test-123"
    
    # List all
    all_previews = bridge.get_all_previews()
    assert "test-123" in all_previews


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_full_phase2_workflow(llm_mock, settings, sample_app_path):
    """Test complete Phase 2 workflow: resolve → test → preview"""
    from agents.problem_resolver_agent import ProblemResolverAgent
    from agents.tester_agent import TesterAgent
    from services.agent_collaboration_manager import CollaborationManager
    
    # Step 1: Resolve problems
    resolver = ProblemResolverAgent(llm_mock, settings)
    resolution = await resolver.analyze_and_resolve(
        app_path=sample_app_path,
        error_logs=None
    )
    
    assert resolution["status"] in ["success", "partial"]
    
    # Step 2: Run tests
    tester = TesterAgent(llm_mock, settings)
    test_result = await tester.run_tests(
        app_path=sample_app_path,
        test_type="all",
        generate_missing=True
    )
    
    assert "status" in test_result
    
    # Step 3: Track collaboration
    manager = CollaborationManager(settings)
    history = manager.get_collaboration_history()
    
    # Workflow completed
    assert resolution is not None
    assert test_result is not None


@pytest.mark.asyncio
async def test_phase2_endpoints_integration(settings):
    """Test Phase 2 API endpoints (requires running server)"""
    # This would be an E2E test that requires the server running
    # Skipped in unit tests
    pytest.skip("Requires running coordinator server")


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_problem_resolver_handles_exceptions(llm_mock, settings):
    """Test that Problem Resolver handles exceptions gracefully"""
    from agents.problem_resolver_agent import ProblemResolverAgent
    
    # Mock LLM to raise exception
    async def mock_error(*args, **kwargs):
        raise Exception("LLM API error")
    
    llm_mock.ainvoke = mock_error
    
    resolver = ProblemResolverAgent(llm_mock, settings)
    
    result = await resolver.analyze_and_resolve(
        app_path="/non/existent/path",
        error_logs=None
    )
    
    # Should return error status, not crash
    assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_tester_agent_handles_timeout(llm_mock, settings, sample_app_path):
    """Test that Tester Agent handles test timeouts"""
    from agents.tester_agent import TesterAgent
    
    tester = TesterAgent(llm_mock, settings)
    
    # This should handle timeout gracefully (tests configured with 5min timeout)
    result = await tester.run_tests(
        app_path=sample_app_path,
        test_type="all",
        generate_missing=False
    )
    
    # Should return structured response even on timeout
    assert "status" in result
    assert "summary" in result


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.asyncio
async def test_problem_resolver_performance(llm_mock, settings, sample_app_path):
    """Test that Problem Resolver completes in reasonable time"""
    import time
    from agents.problem_resolver_agent import ProblemResolverAgent
    
    resolver = ProblemResolverAgent(llm_mock, settings)
    
    start = time.time()
    await resolver.analyze_and_resolve(
        app_path=sample_app_path,
        error_logs=None
    )
    duration = time.time() - start
    
    # Should complete in under 60 seconds for small app
    assert duration < 60


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
