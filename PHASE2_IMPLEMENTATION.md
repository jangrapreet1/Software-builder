# Phase 2 Implementation Guide

## Overview

Phase 2 extends the Autonomous App-Building Platform with autonomous problem resolution, on-demand testing, and live preview capabilities. The system now self-heals code issues across 12+ error categories and provides structured test reports without user intervention.

**Status:** ✅ COMPLETE  
**Date:** 2025-10-14  
**Branch:** `feature/phase2-autonomous-resolution`

---

## What's New in Phase 2

### 1. Autonomous Problem Resolution

The **Problem Resolver Agent** automatically detects and fixes code issues across multiple categories:

#### Supported Error Categories
- **Syntax Errors** - Compilation and syntax-level issues
- **Module/Dependency Errors** - Missing or incompatible packages
- **Runtime Errors** - Execution failures
- **Logic Errors** - Algorithmic and business logic bugs
- **API/Network Errors** - HTTP timeouts, connection issues
- **Database Errors** - Connection, query, and ORM issues
- **UI/Rendering Errors** - Frontend component problems
- **State Management** - React/Vue state bugs
- **Security/Auth Errors** - Authentication and authorization issues
- **Concurrency/Async Errors** - Race conditions, deadlocks
- **Build/Config Errors** - Missing env files, bad configuration
- **Deployment/Production Errors** - Container, scaling issues

#### How It Works
1. **Detection** - Scans code files, parses error logs, analyzes stack traces
2. **Classification** - Categorizes issues by type and severity
3. **Resolution** - Applies category-specific fixes using LLM + heuristics
4. **Validation** - Re-checks to ensure fixes work

---

### 2. On-Demand Testing Agent

The **Tester Agent** runs tests only when requested and provides structured reports:

#### Features
- **Auto-detection** of testing frameworks (pytest, Jest, Mocha, Vitest)
- **Test generation** if no tests exist
- **Coverage analysis** when available
- **Structured reports** with pass/fail/skip counts
- **Recommendations** for improving test coverage

#### Supported Test Types
- Unit tests
- Integration tests
- End-to-end (E2E) tests
- API tests
- UI component tests

---

### 3. Live Preview Integration

#### Frontend Components (React/TypeScript)
- **ProblemResolverPanel** - UI for triggering auto-resolution
- **TestingPanel** - UI for running tests on-demand
- **Enhanced StatusIndicator** - Shows "Resolving" and "Testing" states
- **Integrated App.tsx** - Connects all Phase 2 components

#### Backend API Endpoints
- `POST /api/resolve/analyze` - Trigger problem resolution
- `POST /api/test/run` - Run tests on-demand
- `POST /api/preview/create` - Create live preview
- `POST /api/preview/{build_id}/update` - Update existing preview
- `POST /api/preview/{build_id}/stop` - Stop live preview
- `GET /api/preview/{build_id}/status` - Get preview status
- `GET /api/preview/list` - List all active previews
- `GET /api/collaboration/sessions` - List agent collaboration sessions
- `GET /api/collaboration/history` - Get agent interaction history

---

## API Contracts

### Problem Resolution

**Request:**
```json
POST /api/resolve/analyze
{
  "app_path": "./generated/my-app",
  "error_logs": "Optional error logs string",
  "auto_fix": true
}
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "status": "success",
    "issues_found": 5,
    "issues_resolved": 5,
    "resolution_log": [
      {
        "category": "syntax",
        "issue": "Missing comma in dict",
        "action": "Fixed syntax error in main.py",
        "success": true,
        "timestamp": "2025-10-14T12:00:00Z"
      }
    ],
    "remaining_issues": [],
    "modified_files": ["main.py", "config.py"],
    "timestamp": "2025-10-14T12:00:00Z"
  },
  "timestamp": "2025-10-14T12:00:00Z"
}
```

---

### Testing

**Request:**
```json
POST /api/test/run
{
  "app_path": "./generated/my-app",
  "test_type": "all",
  "specific_tests": [],
  "generate_missing": true
}
```

**Response:**
```json
{
  "status": "passed",
  "timestamp": "2025-10-14T12:00:00Z",
  "framework": "pytest",
  "summary": {
    "total_tests": 10,
    "passed": 9,
    "failed": 1,
    "skipped": 0,
    "success_rate": 90.0,
    "execution_time": 5.2
  },
  "failures": [
    {
      "test": "test_api_endpoint",
      "message": "AssertionError: Expected 200, got 404"
    }
  ],
  "coverage": {
    "total": 85,
    "details": "See full output"
  },
  "recommendations": [
    "1 test(s) failed. Review failures and fix issues.",
    "Success rate is 90.0%. Aim for >80% passing tests."
  ],
  "test_files": ["tests/test_main.py", "tests/test_api.py"],
  "generated_tests": {
    "success": true,
    "files_created": ["tests/conftest.py", "tests/test_main.py"],
    "message": "Generated 2 test files"
  }
}
```

---

### Live Preview

**Request:**
```json
POST /api/preview/create
{
  "build_id": "abc-123",
  "app_path": "./generated/my-app",
  "port": 3000,
  "auto_start": true
}
```

**Response:**
```json
{
  "build_id": "abc-123",
  "previewUrl": "http://localhost:32768",
  "instanceId": "sandbox-abc123",
  "expiresAt": "2025-10-14T13:00:00Z",
  "logsUrl": "/api/sandbox/sandbox-abc123/logs",
  "status": "running",
  "port": 32768,
  "created_at": "2025-10-14T12:00:00Z"
}
```

---

## Agent Collaboration Framework

### CollaborationManager

Orchestrates multiple agents for complex workflows:

```python
from services.agent_collaboration_manager import CollaborationManager

manager = CollaborationManager(settings)

result = await manager.orchestrate_build_with_resolution(
    build_id="abc-123",
    app_path="./generated/my-app",
    agents={
        "resolver": problem_resolver,
        "tester": tester_agent,
        "backend": backend_agent,
        "frontend": frontend_agent
    }
)
```

**Features:**
- Sequential and parallel agent execution
- Inter-agent communication
- Shared state management
- Automatic retry with exponential backoff
- Comprehensive logging

---

### LivePreviewBridge

Manages temporary deployments and preview URLs:

```python
from services.agent_collaboration_manager import LivePreviewBridge

bridge = LivePreviewBridge(sandbox_orchestrator, settings)

preview = await bridge.create_live_preview(
    build_id="abc-123",
    app_path="./generated/my-app",
    port=3000,
    auto_start=True
)

# Returns: {previewUrl, instanceId, expiresAt, logsUrl}
```

---

## Frontend Integration

### Using Problem Resolver Panel

```tsx
import { ProblemResolverPanel } from './components/ProblemResolverPanel';

<ProblemResolverPanel
  appPath="./generated/my-app"
  onResolve={(result) => {
    console.log(`Resolved ${result.issues_resolved} issues`);
  }}
/>
```

### Using Testing Panel

```tsx
import { TestingPanel } from './components/TestingPanel';

<TestingPanel
  appPath="./generated/my-app"
  onTestComplete={(result) => {
    console.log(`Tests: ${result.summary.passed}/${result.summary.total_tests} passed`);
  }}
/>
```

---

## Enhanced Build Workflow

Phase 2 adds autonomous resolution and testing to the build process:

```python
from workflows.app_builder_phase2 import AppBuilderWorkflowPhase2

workflow = AppBuilderWorkflowPhase2(settings, build_registry)

result = await workflow.build_from_brief(
    description="Build a task management app",
    name="taskmaster",
    enable_auto_resolution=True,  # Phase 2: Auto-fix issues
    run_tests=True                # Phase 2: Run tests
)

# Result includes:
# - resolution_summary: { issues_resolved, resolution_attempts }
# - test_summary: { total_tests, passed, failed, success_rate }
# - preview_url, instance_id, logs_url, expires_at
```

---

## Security & Isolation

### Sandbox Execution
- All code execution happens in isolated Docker containers
- Resource limits enforced (CPU, memory, time)
- Network restrictions applied
- No host filesystem access

### Secret Masking
- API keys, passwords, tokens automatically masked in logs
- Environment variables sanitized before display

### Permission Model
- No automatic command execution without approval
- User must explicitly grant permissions for builds/tests

---

## Observability & Logging

### Structured Logging
All agent actions are logged with:
- Timestamp
- Agent name
- Action type
- Success/failure
- Duration
- Input/output summaries

### Audit Trail
- `/api/audit/recent` - Recent events
- `/api/collaboration/history` - Agent interactions
- `/api/audit/{run_id}` - Detailed run logs

---

## Example Workflow

### 1. Build with Auto-Resolution

```bash
# Step 1: Create app
curl -X POST http://localhost:5000/api/build \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Build a todo app with React and FastAPI",
    "name": "todo-app"
  }'

# Returns: { build_id: "abc-123", ... }

# Step 2: Auto-resolve issues
curl -X POST http://localhost:5000/api/resolve/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "app_path": "./generated/todo-app",
    "auto_fix": true
  }'

# Step 3: Run tests
curl -X POST http://localhost:5000/api/test/run \
  -H "Content-Type: application/json" \
  -d '{
    "app_path": "./generated/todo-app",
    "test_type": "all",
    "generate_missing": true
  }'

# Step 4: Create live preview
curl -X POST http://localhost:5000/api/preview/create \
  -H "Content-Type: application/json" \
  -d '{
    "build_id": "abc-123",
    "app_path": "./generated/todo-app",
    "port": 3000,
    "auto_start": true
  }'
```

---

## Configuration

### Environment Variables

```bash
# Required
GOOGLE_API_KEY=your-gemini-api-key

# Optional
GEMINI_MODEL=gemini-2.5-flash
MAX_RETRIES=3
AGENT_TIMEOUT=300
DOCKER_NETWORK=appbuilder-network
```

### Agent Settings

```python
# config/settings.py
class Settings(BaseSettings):
    google_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    max_retries: int = 3
    agent_timeout: int = 300
```

---

## Troubleshooting

### Problem Resolver Not Working
**Symptom:** Issues not being resolved  
**Solution:** Check that:
- App path exists and is readable
- LLM API key is valid
- Files are not read-only

### Tests Not Running
**Symptom:** Test endpoint returns "no tests found"  
**Solution:**
- Enable `generate_missing: true` to auto-generate tests
- Check that app path contains valid source code
- Verify test framework is installed (pytest, Jest, etc.)

### Live Preview Not Starting
**Symptom:** Preview returns 503 or times out  
**Solution:**
- Ensure Docker is running
- Check port is not already in use
- Verify sandbox orchestrator is initialized

---

## Performance Considerations

### Problem Resolution
- **Average time:** 10-30 seconds per issue category
- **Max resolution attempts:** 3 iterations
- **Parallel resolution:** Issues resolved sequentially by priority

### Testing
- **Timeout:** 5 minutes per test run
- **Generation:** 2-5 seconds per test file
- **Execution:** Varies by test count (typically 1-30 seconds)

### Live Preview
- **Startup time:** 5-15 seconds
- **Memory:** 512MB default (configurable)
- **CPU:** 1.0 core default (configurable)

---

## Next Steps - Phase 3

Planned enhancements:
1. Multi-service orchestration (app + database + cache)
2. Real-time collaboration (WebSocket-based)
3. Advanced test coverage analysis
4. Performance profiling
5. Security vulnerability scanning
6. Kubernetes deployment support

---

## Files Created/Modified

### New Files
- `agents/problem_resolver_agent.py` - Autonomous problem resolution
- `agents/tester_agent.py` - On-demand testing
- `coordinator/services/agent_collaboration_manager.py` - Agent orchestration
- `coordinator/ui/src/components/ProblemResolverPanel.tsx` - Resolution UI
- `coordinator/ui/src/components/TestingPanel.tsx` - Testing UI
- `workflows/app_builder_phase2.py` - Enhanced workflow
- `PHASE2_IMPLEMENTATION.md` - This documentation

### Modified Files
- `coordinator/main.py` - Added Phase 2 endpoints
- `coordinator/ui/src/App.tsx` - Integrated Phase 2 components
- `coordinator/ui/src/components/StatusIndicator.tsx` - Added new states

---

**Phase 2 Status:** ✅ **COMPLETE**  
**All objectives achieved:** Autonomous resolution, on-demand testing, live preview, agent collaboration, structured logging, and security measures.
