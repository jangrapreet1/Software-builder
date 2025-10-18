# Phase 1: Live Preview Implementation Guide

## Overview
This guide explains how to use the Phase 1 live preview sandbox orchestration system with permission-first workflow, detection report persistence, and audit logging.

## Architecture

### Components
1. **Repository Detector** - Auto-detects languages, frameworks, build/run commands
2. **Permission Manager** - Enforces explicit user approval before executing commands
3. **Sandbox Orchestrator** - Manages isolated Docker containers with resource limits
4. **Session Manager** - Handles secure preview URLs with expiring tokens
5. **Audit Logger** - Tracks all operations with structured JSON logs
6. **Build Registry** - Persists build metadata across restarts

## Permission-First Workflow

### How It Works
1. **Detection Phase**
   - Call `POST /api/repo/detect` with `{ "repo_path": "./generated/my-app" }`
   - System analyzes the repository and persists detection report to `.sb_artifacts/detection_report_<timestamp>.json`
   - Returns detected build/run commands

2. **Permission Grant Phase**
   - UI displays exact commands in a modal
   - User explicitly approves by clicking "Approve & Launch"
   - Frontend calls `POST /api/session/permissions` with:
     ```json
     {
       "session_id": "session-xyz",
       "actions": ["allow_build", "allow_run"],
       "commands": ["npm install", "npm run dev"],
       "duration": 3600
     }
     ```
   - Permission is recorded and valid for specified duration

3. **Launch Phase**
   - Call `POST /api/app/launch` with app path and resource limits
   - Backend checks for recorded permission
   - If permission missing, returns HTTP 403 with required commands
   - If permission granted, launches sandbox container
   - Returns `{ previewUrl, instanceId, expiresAt, logsUrl, sessionToken }`

### API Endpoints

#### Detection
```bash
# Detect repository configuration
POST /api/repo/detect
{
  "repo_path": "./generated/my-app"
}

# Response includes artifactPath
{
  "status": "success",
  "detection_report": { ... },
  "artifactPath": ".sb_artifacts/detection_report_20250114T120000Z.json"
}

# Get latest detection report
GET /api/repo/detect/latest?repo_path=./generated/my-app
```

#### Permissions
```bash
# Grant permission for session
POST /api/session/permissions
{
  "session_id": "session-123",
  "actions": ["allow_build", "allow_run"],
  "commands": ["npm install", "npm start"],
  "duration": 3600
}
```

#### Sandbox Operations
```bash
# Launch instance (requires permission)
POST /api/app/launch
{
  "app_path": "./generated/my-app",
  "port": 3000,
  "cpu_limit": 1.0,
  "memory_limit": "512m",
  "timeout": 3600
}

# Response
{
  "status": "success",
  "instance_id": "inst_abc123",
  "preview_url": "http://localhost:3000",
  "session_token": "tok_xyz...",
  "expires_at": "2025-01-14T13:00:00Z",
  "logs_url": "/api/sandbox/inst_abc123/logs"
}

# Stop instance
POST /api/app/stop
{
  "instance_id": "inst_abc123",
  "force": false
}

# Download source code (respects .gitignore)
GET /api/app/download?app_path=./generated/my-app
```

#### Audit & Monitoring
```bash
# Get run audit log
GET /api/audit/{run_id}

# List recent runs
GET /api/audit/runs/list?limit=50

# Get recent audit events
GET /api/audit/recent?limit=100

# Query specific events
GET /api/audit/query?event_type=instance_launched&limit=50
```

## Artifacts & Persistence

### Detection Reports
- Location: `.sb_artifacts/detection_report_<timestamp>.json`
- Contains: languages, frameworks, build/run commands, environment variables
- Persisted on every detection run
- Retrieved via `/api/repo/detect/latest`

### Audit Logs
- Location: `.sb_artifacts/audit_run_<runId>.json`
- Format: Array of structured log entries
- Each entry includes:
  ```json
  {
    "timestamp": "2025-01-14T12:00:00Z",
    "runId": "run_20250114T120000Z_abc123",
    "step": "detect|build|run|validate",
    "command": "npm install",
    "exitCode": 0,
    "stdoutSnippet": "...",
    "stderrSnippet": "...",
    "containerId": "container_xyz",
    "humanSummary": "Installed dependencies successfully"
  }
  ```

### Build Metadata
- Location: `.sb_artifacts/builds/<build_id>.json`
- Persists across backend restarts
- Includes: project_name, status, progress, source_path, timestamps
- Auto-bootstrapped from `generated/` directory on startup

## Security Features

### Sandboxing
- All commands run in isolated Docker containers
- CPU and memory limits enforced
- Network access restricted
- Automatic cleanup after timeout or stop

### Secret Management
- Secrets automatically masked in logs
- Environment variables filtered
- Session tokens expire after duration
- No secrets stored in detection reports

### Permission Model
- Explicit user approval required
- Commands shown before execution
- Time-limited permissions
- Audit trail for all operations

## Frontend Integration

### React Components
- `LivePreview.tsx` - Embedded iframe for preview
- `ControlsPanel.tsx` - Launch/stop/download controls with permission modal
- `StatusIndicator.tsx` - Instance status and progress
- `LogsPanel.tsx` - Real-time container logs

### Permission Modal Flow
1. User clicks "Launch App"
2. If no permission, modal shows exact commands
3. User reviews security notice and commands
4. User clicks "Approve & Launch"
5. Frontend calls `/api/session/permissions`
6. Frontend calls `/api/app/launch`
7. Preview URL displayed in iframe

## Running Locally

### Prerequisites
- Docker Desktop running
- Python 3.11+
- Node.js 18+

### Backend
```bash
cd "c:\Users\Lenovo\Code\Software builder"
python coordinator\main.py
```

### Frontend
```bash
cd coordinator\ui
npm install
npm run dev
```

### Access
- Backend API: http://localhost:5000
- Frontend UI: http://localhost:5173
- API Docs: http://localhost:5000/docs

## Validation Workflow

### Manual Validation
```bash
# 1. Detect repository
curl -X POST http://localhost:5000/api/repo/detect \
  -H "Content-Type: application/json" \
  -d '{"repo_path": "./generated/to-do"}'

# 2. Grant permission
curl -X POST http://localhost:5000/api/session/permissions \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "actions": ["allow_run"],
    "commands": ["npm install", "npm run dev"],
    "duration": 3600
  }'

# 3. Launch instance
curl -X POST http://localhost:5000/api/app/launch \
  -H "Content-Type: application/json" \
  -d '{
    "app_path": "./generated/to-do",
    "port": 3000,
    "cpu_limit": 1.0,
    "memory_limit": "512m",
    "timeout": 3600
  }'

# 4. Check audit logs
curl http://localhost:5000/api/audit/runs/list
```

## Troubleshooting

### Docker Not Available
- **Symptom**: "Sandbox orchestrator unavailable" warning
- **Solution**: Start Docker Desktop and restart coordinator

### Permission Denied (403)
- **Symptom**: Launch returns "permission_required" error
- **Solution**: Call `/api/session/permissions` first with required commands

### Build Not Persisting
- **Symptom**: Builds disappear after restart
- **Solution**: Check `.sb_artifacts/builds/` directory exists and is writable

### Detection Report Not Found
- **Symptom**: Latest detection returns 404
- **Solution**: Run `/api/repo/detect` first to generate report

## Default Commands

### Python (FastAPI/Flask)
- Build: `pip install -r requirements.txt`
- Run: `uvicorn main:app --reload` or `python main.py`

### Node.js (React/Vite)
- Build: `npm install`, `npm run build`
- Run: `npm run dev` or `npm start`

### Docker
- Build: `docker build -t app .`
- Run: `docker-compose up`

## Resource Limits

### Default Limits
- CPU: 1.0 cores
- Memory: 512MB
- Timeout: 3600 seconds (1 hour)
- Idle timeout: 300 seconds (5 minutes)

### Customization
Pass custom limits in launch request:
```json
{
  "cpu_limit": 2.0,
  "memory_limit": "1g",
  "timeout": 7200
}
```

## Next Steps

### Phase 2 (Planned)
- Automated testing integration
- PR creation workflow
- Multi-container orchestration
- Real-time collaboration
- Advanced debugging tools

## Support

For issues or questions:
1. Check audit logs: `/api/audit/recent`
2. Review detection report: `.sb_artifacts/detection_report_*.json`
3. Inspect container logs: `/api/sandbox/{instance_id}/logs`
4. Verify permissions: Ensure `/api/session/permissions` was called

## Summary

Phase 1 delivers a secure, permission-first live preview system with:
- ✅ Auto-detection of build/run commands
- ✅ Explicit user approval workflow
- ✅ Sandboxed execution with resource limits
- ✅ Persistent detection reports and audit logs
- ✅ Build metadata persistence across restarts
- ✅ Complete REST API with structured responses
- ✅ React UI with permission modal
