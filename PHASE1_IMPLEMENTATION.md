# Phase 1 Implementation Guide

## Overview

Phase 1 implements live preview, sandbox orchestration, and permission-first workflow for the Autonomous App Builder platform.

**Status:** ✅ COMPLETE  
**Date:** 2025-10-14  
**Branch:** `feature/live-preview`

---

## Permission-First Flow

### How to Grant Permission

Before any build or run command executes, the system requires explicit user approval.

#### 1. Detect Repository

Call the detection endpoint to analyze your repository:

```bash
curl -X POST http://localhost:5000/api/repo/detect \
  -H "Content-Type: application/json" \
  -d '{"repo_path": "./generated/my-app"}'
```

This returns a detection report including:
- Detected languages and frameworks
- Suggested build commands
- Suggested run commands  
- **artifactPath** - saved to `.sb_artifacts/detection_report_<timestamp>.json`

#### 2. Review Commands

The UI will display the exact commands that will be executed:
- Build commands (e.g., `npm install`, `pip install -r requirements.txt`)
- Run commands (e.g., `npm start`, `python main.py`)

#### 3. Grant Permission

When you click "Launch App", a modal appears showing all commands. Click "Approve & Launch" to grant permission:

```json
POST /api/session/permissions
{
  "session_id": "session-my-app-20251014120000",
  "actions": ["allow_build", "allow_run"],
  "commands": [
    "npm install",
    "npm start"
  ],
  "duration": 3600
}
```

#### 4. Launch Sandbox

After permission is granted, the launch proceeds:

```bash
curl -X POST http://localhost:5000/api/app/launch \
  -H "Content-Type: application/json" \
  -d '{
    "app_path": "./generated/my-app",
    "port": 3000,
    "cpu_limit": 1.0,
    "memory_limit": "512m",
    "timeout": 3600
  }'
```

**Without permission:**  
Returns HTTP 403 with required commands listed

**With permission:**  
Returns preview URL, instance ID, session token, logs URL

---

## Default Commands

The system auto-detects build/run commands based on project type:

### Node.js Projects
- **Build:** `npm ci` or `npm install`  
- **Run:** `npm start` or `npm run dev`

### Python Projects  
- **Build:** `pip install -r requirements.txt`  
- **Run:** `python main.py` or `uvicorn main:app --reload`

### Docker Projects
- **Build:** `docker-compose build`  
- **Run:** `docker-compose up`

---

## Running Sandbox Locally

### Prerequisites
- Docker installed and running
- Python 3.11+
- Port 5000 available

### Start Coordinator

```bash
# Set environment variables
export GOOGLE_API_KEY=your-api-key

# Start coordinator
python coordinator/main.py
```

### Access UI

Navigate to:  
`http://localhost:5000/ui` (Vue.js UI)  
or build the React UI:

```bash
cd coordinator/ui
npm install
npm run dev
```

### Artifacts Location

All artifacts are stored in:
- Detection reports: `<repo>/.sb_artifacts/detection_report_*.json`
- Audit logs: `coordinator/logs/audit/audit-*.jsonl`

---

## API Endpoints

### Detection
- `POST /api/repo/detect` - Auto-detect repository
- `GET /api/repo/detect/latest?repo_path=X` - Get latest detection report

### Permissions
- `POST /api/session/permissions` - Grant permission for session

### Sandbox
- `POST /api/app/preview` - Create preview session (no container)
- `POST /api/app/launch` - Launch sandbox instance (requires permission)
- `POST /api/app/stop` - Stop instance
- `GET /api/app/download?app_path=X` - Download source code

### Monitoring
- `GET /api/sandbox/instances` - List active instances
- `GET /api/sandbox/{id}/status` - Instance status & health
- `GET /api/sandbox/{id}/logs?tail=100` - Container logs

### Audit
- `GET /api/audit/recent?limit=50` - Recent audit events
- `GET /api/audit/stats` - Audit statistics

---

## Frontend Components

### LivePreview
Displays application in iframe (for localhost) or link to new tab.  
**Props:** `previewUrl`, `sessionToken`, `instanceId`

### ControlsPanel  
Buttons for Launch, Stop, Download with permission modal.  
**Props:** `instanceId`, `sessionId`, `detectedCommands`, callbacks

### StatusIndicator
Shows current status with progress bar.  
**States:** detected, building, running, error, stopped, idle

### LogsPanel
Streaming console logs with download option.  
**Props:** `instanceId`, `logsUrl`, `tail`

---

## Security Features

✅ **Permission-first:** No auto-execution without approval  
✅ **Sandbox isolation:** Docker containers with restricted network  
✅ **Resource limits:** CPU/memory/time enforced  
✅ **Secret masking:** API keys hidden in logs  
✅ **Session tokens:** Cryptographic URL-safe tokens  
✅ **Auto-cleanup:** Expired instances removed every 5 min  

---

## Example Workflow

```bash
# 1. Detect repository
curl -X POST http://localhost:5000/api/repo/detect \
  -H "Content-Type: application/json" \
  -d '{"repo_path": "./generated/my-app"}'

# Returns: detection report + artifactPath

# 2. Grant permission (via UI or API)
curl -X POST http://localhost:5000/api/session/permissions \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-session",
    "actions": ["allow_build", "allow_run"],
    "commands": ["npm install", "npm start"],
    "duration": 3600
  }'

# 3. Launch sandbox
curl -X POST http://localhost:5000/api/app/launch \
  -H "Content-Type": "application/json" \
  -d '{
    "app_path": "./generated/my-app",
    "port": 3000
  }'

# Returns: { previewUrl, instanceId, sessionToken, expiresAt, logsUrl }

# 4. Monitor instance
curl http://localhost:5000/api/sandbox/{instanceId}/status

# 5. Stop when done
curl -X POST http://localhost:5000/api/app/stop \
  -H "Content-Type": "application/json" \
  -d '{"instance_id": "{instanceId}", "force": true}'
```

---

## Troubleshooting

**403 Permission Required:**  
Grant permission via `/api/session/permissions` before launching

**Docker not available:**  
Install Docker Desktop and ensure daemon is running

**Port conflicts:**  
Change port in launch request or stop conflicting service

---

**For more details, see:**
- `PHASE1_SUMMARY.md` - Complete implementation summary
- `PHASE1_DELIVERABLE.md` - Acceptance criteria checklist
- `docs/phase1_sandbox_orchestration.md` - Full API reference
