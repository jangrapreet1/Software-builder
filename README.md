# Autonomous App-Building Platform

An AI-driven development system that transforms short project briefs into working web applications using coordinated AI agents.

## Overview

This platform uses:
- **LangGraph**: Workflow orchestration and state management
- **AutoGen**: Agent collaboration and dialogue
- **Semantic Kernel**: Tool invocation and skill integration
- **FastAPI**: Backend API generation
- **React + Vite**: Frontend UI generation
- **PostgreSQL**: Data persistence
- **Docker Compose**: Integration and deployment

## System Architecture

### 1. Coordinator Agent
- Accepts project briefs
- Extracts features, entities, and user flows
- Breaks down into technical tasks
- Orchestrates specialized agents
- Validates and integrates outputs

### 2. Frontend Agent
- Generates React components with TailwindCSS
- Creates views, navigation, forms
- Implements API integration

### 3. Backend Agent
- Builds FastAPI REST endpoints
- Implements SQLAlchemy models
- Creates authentication and CRUD logic
- Generates database migrations

### 4. Integration Environment
- Combines frontend and backend
- Sets up Docker Compose
- Provides local web UI for testing

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Add your Google Gemini API key to .env (set GOOGLE_API_KEY)

# Run the platform
docker-compose up

# Access the platform
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# Coordinator UI: http://localhost:5000
```

## Testing

```bash
# Unit/API tests (FastAPI TestClient with a stubbed workflow)
pytest -q

# Full end-to-end suite (requires a valid GOOGLE_API_KEY and running coordinator)
python comprehensive_test.py

# Windows convenience script (lint, tests, optional E2E)
powershell -ExecutionPolicy Bypass -File scripts/run_all_tests.ps1 -E2E
```

## Usage

1. Open the Coordinator UI at http://localhost:5000
2. Enter a project brief (e.g., "Build a task management app with user authentication")
3. Watch as agents plan, generate, and integrate the application
4. View the generated code, logs, and test results
5. Access your running app in the embedded preview

## Project Structure

```
├── coordinator/          # Main orchestration agent
│   ├── agents/          # Agent implementations
│   ├── workflows/       # LangGraph workflows
│   ├── ui/              # Testing UI
│   └── config/          # Configuration
├── agents/              # Specialized agents
│   ├── frontend/        # Frontend generation agent
│   ├── backend/         # Backend generation agent
│   └── shared/          # Shared utilities
├── generated/           # Generated applications
├── docker-compose.yml   # Integration environment
└── docs/               # Documentation
```

## Example

```python
from coordinator import AppBuilder

builder = AppBuilder()
result = builder.build_from_brief(
    "Build a task management app with user authentication and task sharing"
)

print(f"Status: {result.status}")
print(f"App URL: {result.app_url}")
print(f"Source: {result.source_path}")
```

## Features

- **One-Command Deployment**: Generated apps run with `docker-compose up`
- **Structured Communication**: Agents use JSON task specifications
- **State Persistence**: LangGraph maintains recoverable workflow state
- **Validation**: Automated testing, linting, and build verification
- **Iterative Refinement**: AutoGen dialogues for clarification
- **Extensibility**: Semantic Kernel for dynamic tool integration

## Documentation

- [Architecture Guide](docs/architecture.md)
- [Agent Communication Protocol](docs/protocol.md)
- [Workflow Diagrams](docs/workflows.md)
- [API Reference](docs/api.md)

## License

MIT
