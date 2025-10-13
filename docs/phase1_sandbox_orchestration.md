# Phase 1: Sandbox Orchestration & Security

## Overview

Phase 1 implements secure sandbox orchestration for generated applications with repository detection, containerized execution, and preview sessions.

## Components

### 1. Repository Detector

Auto-detects repository configuration without executing any commands.

**Features:**
- Language detection (Python, Node.js, Go, Java, Rust)
- Framework identification (FastAPI, React, Django, etc.)
- Package manager detection (pip, npm, yarn, cargo, etc.)
- Build/run/test command inference
- Docker configuration detection
- Environment variable requirements

**Endpoint:** `POST /api/repo/detect`

**Request:**
```json
{
  "repo_path": "/path/to/repository"
}
```

**Response:**
```json
{
  "status": "success",
  "detection_report": {
    "detection_timestamp": "2025-10-11T03:08:59Z",
    "repository_root": "/path/to/repository",
    "languages": {
      "confident": [
        {
          "language": "Python",
          "version": "3.11+",
          "evidence": ["requirements.txt", "*.py"]
        }
      ]
    },
    "frameworks": {
      "confident": ["FastAPI", "Docker"]
    },
    "package_managers": [
      {
        "name": "pip",
        "install_command": "pip install -r requirements.txt"
      }
    ],
    "build_commands": {
      "confident": ["pip install -r requirements.txt"]
    },
    "run_commands": {
      "confident": ["uvicorn main:app --reload"]
    },
    "test_commands": {
      "confident": ["pytest"]
    }
  }
}
```

### 2. Sandbox Orchestrator

Manages containerized application instances with resource limits and security.

**Features:**
- Docker-based isolation
- CPU/memory/time limits (configurable)
- Network isolation (restricted by default)
- Health checks & status monitoring
- Automatic cleanup on timeout/expiry
- Session-to-container mapping
- Build log capture

**Resource Defaults:**
- CPU: 1.0 cores
- Memory: 512MB
- Timeout: 1 hour
- Idle timeout: 5 minutes
- Max containers: 10

### 3. Session Manager

Secure preview sessions with token-based access control.

**Features:**
- Secure token generation (URL-safe)
- Session expiry enforcement
- Per-instance session limits
- Automatic cleanup of expired sessions
- Session revocation support

**Session Duration:** 1 hour (default)

## API Endpoints

### Preview Session

Create a preview session without launching a container.

**Endpoint:** `POST /api/app/preview`

**Request:**
```json
{
  "app_path": "/path/to/app",
  "port": 3000,
  "session_duration": 3600
}
```

**Response:**
```json
{
  "status": "success",
  "preview_url": "http://localhost:3000?session=TOKEN",
  "session_token": "secure-token-here",
  "expires_at": "2025-10-11T04:08:59Z",
  "message": "Preview session created"
}
```

### Launch Sandbox Instance

Launch a containerized application with security and resource limits.

**Endpoint:** `POST /api/app/launch`

**Request:**
```json
{
  "app_path": "/path/to/app",
  "port": 3000,
  "cpu_limit": 1.0,
  "memory_limit": "512m",
  "timeout": 3600,
  "environment": {
    "NODE_ENV": "production"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "instance_id": "sandbox-a1b2c3d4",
  "preview_url": "http://localhost:32768",
  "secure_preview_url": "http://localhost:32768?session=TOKEN",
  "session_token": "secure-token-here",
  "expires_at": "2025-10-11T04:08:59Z",
  "logs_url": "/api/sandbox/sandbox-a1b2c3d4/logs",
  "port": 32768,
  "message": "Sandbox instance launched successfully"
}
```

### Stop Instance

Stop a running sandbox instance and cleanup resources.

**Endpoint:** `POST /api/app/stop`

**Request:**
```json
{
  "instance_id": "sandbox-a1b2c3d4",
  "force": false
}
```

**Response:**
```json
{
  "success": true,
  "instance_id": "sandbox-a1b2c3d4",
  "status": "stopped",
  "revoked_sessions": 2,
  "message": "Instance stopped successfully"
}
```

### Download Application

Download application as a zip archive (respects .gitignore).

**Endpoint:** `GET /api/app/download?app_path=/path/to/app`

**Response:** ZIP file stream

**Headers:**
- `Content-Type: application/zip`
- `Content-Disposition: attachment; filename=app-name.zip`

### List Instances

Get all active sandbox instances.

**Endpoint:** `GET /api/sandbox/instances`

**Response:**
```json
{
  "instances": [
    {
      "instance_id": "sandbox-a1b2c3d4",
      "status": "running",
      "preview_url": "http://localhost:32768",
      "started_at": "2025-10-11T03:08:59Z",
      "expires_at": "2025-10-11T04:08:59Z"
    }
  ],
  "count": 1
}
```

### Instance Status

Get detailed status and health of an instance.

**Endpoint:** `GET /api/sandbox/{instance_id}/status`

**Response:**
```json
{
  "instance_id": "sandbox-a1b2c3d4",
  "status": "running",
  "health": "healthy",
  "preview_url": "http://localhost:32768",
  "started_at": "2025-10-11T03:08:59Z",
  "expires_at": "2025-10-11T04:08:59Z",
  "resources": {
    "cpu_percent": 15.2,
    "memory_usage": "124.56 MB",
    "memory_percent": 24.3
  }
}
```

### Instance Logs

Get logs from a sandbox instance.

**Endpoint:** `GET /api/sandbox/{instance_id}/logs?tail=100`

**Response:**
```json
{
  "instance_id": "sandbox-a1b2c3d4",
  "logs": "2025-10-11T03:09:00Z Container started\n..."
}
```

### Sandbox Health

Check sandbox orchestrator health.

**Endpoint:** `GET /api/sandbox/health`

**Response:**
```json
{
  "status": "healthy",
  "docker": "connected",
  "network": "ok",
  "active_instances": 2,
  "max_instances": 10
}
```

### Session Statistics

Get session manager stats.

**Endpoint:** `GET /api/sessions/stats`

**Response:**
```json
{
  "total_sessions": 15,
  "active_sessions": 8,
  "instances_with_sessions": 3
}
```

## Security Features

### 1. Permission Model

- **NO automatic command execution** - All detected commands require explicit approval
- Commands are presented in detection report for user review
- Execution only proceeds after explicit confirmation

### 2. Secret Masking

Sensitive environment variables are masked in logs:
- API_KEY → `***MASKED***`
- SECRET → `***MASKED***`
- PASSWORD → `***MASKED***`
- TOKEN → `***MASKED***`
- PRIVATE → `***MASKED***`

### 3. Container Security

**Isolation:**
- Separate Docker network (`appbuilder-sandbox`)
- Restricted network access
- No host filesystem access (except mounted app directory)

**Capabilities:**
- Drop all capabilities by default
- Only add `NET_BIND_SERVICE` for port binding
- `no-new-privileges` security option

**Resource Limits:**
- CPU quota enforcement
- Memory limit enforcement
- Time-based cleanup (no runaway containers)

### 4. Session Security

- Cryptographically secure tokens (URL-safe base64)
- Time-based expiry (enforced)
- Session revocation support
- Per-instance session limits

### 5. .gitignore Compliance

Download endpoint respects .gitignore patterns:
- Excludes `.git`, `node_modules`, `__pycache__`
- Excludes `.env`, `*.log`
- Custom patterns from `.gitignore` honored

## Background Tasks

### Automatic Cleanup

Runs every 5 minutes to:
- Stop expired instances
- Remove stopped containers
- Clean up Docker images
- Revoke expired sessions

### Graceful Shutdown

On application shutdown:
- Stop all running instances
- Revoke all active sessions
- Clean up Docker resources

## Error Handling

**404 Not Found:**
- Invalid repository/app path
- Instance not found

**503 Service Unavailable:**
- Docker daemon not available
- Sandbox orchestrator not initialized

**500 Internal Server Error:**
- Docker build/run failures
- Container crashes
- Unexpected errors

## Usage Examples

### 1. Detect Repository

```bash
curl -X POST http://localhost:5000/api/repo/detect \
  -H "Content-Type: application/json" \
  -d '{"repo_path": "./generated/my-app"}'
```

### 2. Launch Sandbox

```bash
curl -X POST http://localhost:5000/api/app/launch \
  -H "Content-Type: application/json" \
  -d '{
    "app_path": "./generated/my-app",
    "port": 3000,
    "cpu_limit": 0.5,
    "memory_limit": "256m",
    "timeout": 1800
  }'
```

### 3. Check Status

```bash
curl http://localhost:5000/api/sandbox/sandbox-a1b2c3d4/status
```

### 4. View Logs

```bash
curl http://localhost:5000/api/sandbox/sandbox-a1b2c3d4/logs?tail=50
```

### 5. Stop Instance

```bash
curl -X POST http://localhost:5000/api/app/stop \
  -H "Content-Type: application/json" \
  -d '{"instance_id": "sandbox-a1b2c3d4", "force": true}'
```

### 6. Download App

```bash
curl http://localhost:5000/api/app/download?app_path=./generated/my-app \
  -o my-app.zip
```

## Testing

### Unit Tests

```bash
pytest tests/api/test_sandbox_api.py -v
```

### Integration Tests (requires Docker)

```bash
pytest tests/api/test_sandbox_api.py -v -m integration
```

## Configuration

Settings in `coordinator/config/settings.py`:

```python
# Docker Configuration
docker_network: str = "appbuilder-network"

# Coordinator ports
coordinator_port: int = 5000
```

Environment variables:
- `GOOGLE_API_KEY` - Required for AI features
- `DOCKER_HOST` - Optional Docker daemon URL

## Acceptance Criteria

✅ **Detection Report:** Repository detection produces structured JSON report
✅ **Permission Required:** No commands executed without approval
✅ **API Endpoints:** All endpoints return documented JSON contracts
✅ **Sandbox Orchestration:** Containers launch with limits and cleanup
✅ **Security:** Secrets masked, containers isolated, sessions secured
✅ **Resource Limits:** CPU/memory/time limits enforced
✅ **Session Management:** Secure tokens with expiry
✅ **Download Support:** ZIP export respects .gitignore

## Audit Log Format

For approved command execution (future phases):

```json
{
  "timestamp": "2025-10-11T03:08:59Z",
  "command": "pip install -r requirements.txt",
  "exit_code": 0,
  "stdout": "Successfully installed...",
  "stderr": "",
  "duration_ms": 2350,
  "approved_by": "user",
  "approval_timestamp": "2025-10-11T03:08:45Z"
}
```

## Future Enhancements

- WebSocket streaming for real-time logs
- Custom Dockerfile generation for unsupported projects
- Multi-container orchestration (database + app)
- Network proxy for restricted external access
- Rate limiting per user/IP
- Persistent volume support
