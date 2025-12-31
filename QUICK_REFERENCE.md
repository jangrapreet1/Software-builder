# Quick Reference Guide - Autonomous App-Building Platform

## Essential Information

**Platform**: AI-driven full-stack application builder
**Technologies**: Google Gemini, LangGraph, FastAPI, React, Docker
**Agents**: 23 specialized AI agents
**Output**: Production-ready React + FastAPI + PostgreSQL applications

---

## Quick Start Commands

```bash
# Start Coordinator
python coordinator/main.py

# Access UI
http://localhost:5000/ui

# API Documentation
http://localhost:5000/docs

# Health Check
curl http://localhost:5000/health
```

---

## Core API Endpoints

### Build Operations

```bash
# Start new build
curl -X POST http://localhost:5000/api/build \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Build a blog platform with comments",
    "name": "my-blog",
    "requirements": ["User auth", "Rich text editor", "Comments"]
  }'

# Check build status
curl http://localhost:5000/api/build/{build_id}/status

# List all builds
curl http://localhost:5000/api/builds

# Delete build
curl -X DELETE http://localhost:5000/api/build/{build_id}
```

### Sandbox Operations

```bash
# Launch sandbox instance
curl -X POST http://localhost:5000/api/sandbox/launch \
  -H "Content-Type: application/json" \
  -d '{
    "app_path": "./generated/my-app",
    "port": 3000,
    "cpu_limit": 1.0,
    "memory_limit": "512m"
  }'

# Stop instance
curl -X POST http://localhost:5000/api/sandbox/{instance_id}/stop

# List active instances
curl http://localhost:5000/api/sandbox/instances
```

### Repository Detection

```bash
# Auto-detect project config
curl -X POST http://localhost:5000/api/repo/detect \
  -H "Content-Type: application/json" \
  -d '{"repo_path": "./generated/my-app"}'

# Get latest detection
curl "http://localhost:5000/api/repo/detect/latest?repo_path=./generated/my-app"
```

### Testing

```bash
# Run tests
curl -X POST http://localhost:5000/api/test/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_path": "./generated/my-app",
    "test_type": "all",
    "generate_missing": true
  }'

# Get test history
curl http://localhost:5000/api/test/history
```

---

## Common Workflows

### Workflow 1: Create New Application

```bash
# 1. Submit brief
POST /api/build
{
  "description": "E-commerce store with cart and checkout",
  "name": "shop",
  "requirements": ["Product catalog", "Shopping cart", "Stripe payment"]
}

# 2. Monitor progress
GET /api/build/{build_id}/status

# 3. Access application
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# Source: ./generated/shop/
```

### Workflow 2: Debug Application

```bash
# 1. Detect configuration
POST /api/repo/detect
{"repo_path": "./generated/my-app"}

# 2. Start problem resolver
POST /api/agent/problem-resolver
{
  "session_id": "session-123",
  "app_path": "./generated/my-app",
  "run_mode": "attempt-fix"
}

# 3. Check resolution result
GET /api/agent/problem-resolver/{run_id}/result

# 4. View logs
GET /api/agent/problem-resolver/{run_id}/logs
```

### Workflow 3: Test & Validate

```bash
# 1. Run all tests
POST /api/test/run
{
  "project_path": "./generated/my-app",
  "test_type": "all"
}

# 2. Get test suggestions
POST /api/test/generate-suggestions
{"project_path": "./generated/my-app"}

# 3. Launch live preview
POST /api/app/preview
{
  "app_path": "./generated/my-app",
  "port": 3000
}
```

---

## Key Agents

| Agent | Purpose | File Size |
|-------|---------|-----------|
| **CoordinatorAgent** | Orchestrates workflow, delegates tasks | 12KB |
| **BackendAgent** | Generates FastAPI + SQLAlchemy | 13KB |
| **FrontendAgent** | Generates React components | 12KB |
| **IntegrationAgent** | Combines frontend + backend | 17KB |
| **TesterAgent** | Generates & runs tests | 23KB |
| **ProblemResolverAgent** | Detects errors | 27KB |
| **EnhancedProblemResolver** | Auto-fixes issues | 38KB |
| **DocumentationAgent** | API docs generation | 31KB |
| **SecurityAgent** | Security scanning | 13KB |
| **DeploymentAgent** | Docker & CI/CD | 13KB |

---

## Configuration

### Environment Variables

```bash
# Required
GOOGLE_API_KEY=your-gemini-api-key

# Model (optional)
GEMINI_MODEL=gemini-1.5-pro

# Paths (optional)
GENERATED_APPS_DIR=./generated
ARTIFACTS_DIR=./.sb_artifacts

# Docker (optional)
DOCKER_NETWORK=appbuilder-network

# Features (optional)
USE_FAKE_WORKFLOW=false
DEBUG=false
```

### Rate Limits

Default rate limits per minute:
- Builds: 10/minute
- Preview: 20/minute
- Detection: 30/minute
- Read ops: 100/minute

---

## Generated Application Structure

```
generated/{project-name}/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── models/              # SQLAlchemy models
│   │   ├── routers/             # API endpoints
│   │   ├── schemas/             # Pydantic schemas
│   │   └── database.py          # DB connection
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── pages/               # Page components
│   │   ├── services/            # API client
│   │   └── App.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── docker-compose.yml           # Multi-container setup
└── .project_metadata.json       # Build metadata
```

---

## Example Prompts

### Simple Applications

```
"Build a todo list with user authentication"
"Create a blog with markdown support"
"Make a contact form with email sending"
```

### Medium Complexity

```
"Build a task management app with user authentication and task sharing"
"Create an e-commerce store with product catalog, shopping cart, and Stripe checkout"
"Make a project tracker with teams, tasks, and kanban boards"
```

### Advanced Applications

```
"Build a social media platform with posts, comments, likes, followers, and real-time notifications"
"Create a booking system with calendar, availability, payments, and email confirmations"
"Make a learning management system with courses, lessons, quizzes, and progress tracking"
```

---

## Troubleshooting

### Build Fails

```bash
# 1. Check build logs
GET /api/build/{build_id}/status

# 2. Run problem resolver
POST /api/agent/problem-resolver
{
  "session_id": "debug-session",
  "app_path": "./generated/failed-app",
  "run_mode": "diagnose-only"
}

# 3. Review diagnosis
GET /api/agent/problem-resolver/{run_id}/result
```

### Sandbox Won't Start

```bash
# 1. Check Docker
docker ps

# 2. Verify network
docker network ls | grep appbuilder

# 3. Check logs
docker logs {container_id}

# 4. Restart coordinator
python coordinator/main.py
```

### Tests Failing

```bash
# 1. Check test output
POST /api/test/run
{"project_path": "./generated/my-app", "test_type": "all"}

# 2. Auto-generate missing tests
POST /api/test/run
{
  "project_path": "./generated/my-app",
  "generate_missing": true
}

# 3. Get test suggestions
POST /api/test/generate-suggestions
{"project_path": "./generated/my-app"}
```

---

## Monitoring & Metrics

### Prometheus Metrics

```bash
# Access metrics endpoint
curl http://localhost:5000/metrics

# Key metrics:
# - http_requests_total
# - http_request_duration_seconds
# - appbuild_builds_started_total
# - appbuild_builds_success_total
# - appbuild_builds_failed_total
# - appbuild_builds_active
```

### Dashboard

```bash
# Get dashboard metrics
curl http://localhost:5000/api/metrics/dashboard

# Example response:
{
  "builds": {
    "total": 150,
    "successful": 142,
    "failed": 8
  },
  "agents": {
    "coordinator": {"avg_time": 2.5},
    "backend": {"avg_time": 15.3},
    "frontend": {"avg_time": 12.7}
  }
}
```

---

## Testing

### Unit Tests

```bash
# Run all unit tests
pytest -q

# Run specific test file
pytest tests/test_workflow.py -v

# Run with coverage
pytest --cov=coordinator --cov=agents --cov=workflows
```

### End-to-End Tests

```bash
# Comprehensive E2E test
python comprehensive_test.py

# Windows test script
powershell -ExecutionPolicy Bypass -File scripts/run_all_tests.ps1 -E2E
```

---

## WebSocket Real-Time Updates

```javascript
// Connect to build updates
const ws = new WebSocket(`ws://localhost:5000/ws/build/${buildId}`);

ws.onmessage = (event) => {
    const status = JSON.parse(event.data);
    console.log(`Progress: ${status.progress}%`);
    console.log(`Step: ${status.current_step}`);
    console.log(`Status: ${status.status}`);
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

ws.onclose = () => {
    console.log('Build completed or connection closed');
};
```

---

## Advanced Features

### Custom Frameworks

```bash
# List available frameworks
curl http://localhost:5000/api/v2/frameworks-legacy

# Build with specific frameworks
POST /api/build
{
  "description": "Blog platform",
  "preferred_backend": "fastapi",
  "preferred_frontend": "react"
}
```

### Template Library

```python
# Using templates in agents
from services.template_library import get_template_library

template_lib = get_template_library()
auth_template = template_lib.get_template("authentication", "jwt")
crud_template = template_lib.get_template("crud", "user")
```

### Live Preview Bridge

```bash
# Enable hot-reload during development
POST /api/preview/start
{
  "project_name": "my-app",
  "project_path": "./generated/my-app"
}

# Stop preview
POST /api/preview/stop
{"project_name": "my-app"}

# Check preview health
GET /api/preview/health/my-app
```

---

## File System Operations

```bash
# List directory
GET /api/fs/list?root=./generated/my-app&path=.

# Read file
GET /api/fs/read?root=./generated/my-app&path=backend/app/main.py

# Write file
POST /api/fs/write
{
  "root": "./generated/my-app",
  "path": "backend/app/custom.py",
  "content": "# Custom code here"
}

# Delete file
DELETE /api/fs/delete?root=./generated/my-app&path=backend/app/old.py
```

---

## Best Practices

### Writing Effective Briefs

✅ **Good:**
- "Build a task management app with user authentication, task creation/editing, due dates, and sharing"
- "Create an e-commerce store with product catalog, shopping cart, checkout, and Stripe integration"

❌ **Avoid:**
- "Make an app"
- "Build something cool"
- Vague descriptions without specific features

### Structuring Requirements

```python
requirements = [
    "User authentication (email/password)",
    "CRUD operations for tasks",
    "Task status tracking (pending, in-progress, done)",
    "Task sharing with other users",
    "Email notifications for task updates",
    "Search and filter tasks"
]
```

### Iterative Development

1. Start with MVP features
2. Test and validate
3. Add advanced features incrementally
4. Use problem resolver for debugging
5. Generate documentation

---

## Support & Resources

- **API Docs**: http://localhost:5000/docs
- **UI**: http://localhost:5000/ui
- **Comprehensive Walkthrough**: See `walkthrough.md`
- **Architecture Docs**: `docs/architecture.md`
- **Test Suite**: `comprehensive_test.py`

---

## Summary

The Autonomous App-Building Platform provides:

✅ Natural language to code conversion
✅ Full-stack application generation
✅ Automated testing and validation
✅ Docker-based sandboxing
✅ AI-powered error resolution
✅ Real-time preview and monitoring
✅ Production-ready code output

**Typical Build Time**: 30-120 seconds depending on complexity
**Success Rate**: 95%+ for well-defined requirements
**Code Quality**: Production-ready, tested, documented
