# Agent Communication Protocol

## Overview

Agents communicate using structured JSON messages through the AutoGen collaboration layer. This document defines the message formats and protocols.

## Message Structure

### Base Message Format

```json
{
  "sender": "agent_name",
  "recipient": "target_agent_name",
  "message_type": "request|response|clarification|notification",
  "content": {},
  "metadata": {
    "timestamp": "2024-01-01T00:00:00Z",
    "correlation_id": "uuid",
    "priority": "high|medium|low"
  }
}
```

## Message Types

### 1. Task Assignment

**Coordinator → Agent**

```json
{
  "sender": "coordinator",
  "recipient": "backend_agent",
  "message_type": "task_assignment",
  "content": {
    "task_id": "task-123",
    "task_type": "generate_backend",
    "specifications": {
      "entities": [...],
      "features": [...],
      "technical_specs": {...}
    },
    "deadline": "2024-01-01T12:00:00Z"
  }
}
```

### 2. Task Completion

**Agent → Coordinator**

```json
{
  "sender": "backend_agent",
  "recipient": "coordinator",
  "message_type": "task_completion",
  "content": {
    "task_id": "task-123",
    "status": "success|failed",
    "output": {
      "files": {...},
      "metrics": {
        "lines_of_code": 1234,
        "execution_time": "45s"
      }
    },
    "errors": []
  }
}
```

### 3. Clarification Request

**Agent → Coordinator**

```json
{
  "sender": "frontend_agent",
  "recipient": "coordinator",
  "message_type": "clarification_request",
  "content": {
    "question": "Should the login form support OAuth providers?",
    "context": {
      "feature": "authentication",
      "current_implementation": "JWT only"
    },
    "options": [
      "Add OAuth support",
      "Keep JWT only",
      "Add both with fallback"
    ]
  }
}
```

### 4. Clarification Response

**Coordinator → Agent**

```json
{
  "sender": "coordinator",
  "recipient": "frontend_agent",
  "message_type": "clarification_response",
  "content": {
    "original_question_id": "clarification-456",
    "decision": "Keep JWT only",
    "reasoning": "Simplicity for MVP, OAuth can be added later",
    "additional_context": {}
  }
}
```

### 5. Conflict Resolution

**Multiple Agents → Coordinator**

```json
{
  "sender": "multiple",
  "recipient": "coordinator",
  "message_type": "conflict",
  "content": {
    "conflict_type": "implementation_approach",
    "conflict_area": "state_management",
    "proposals": [
      {
        "agent": "frontend_agent",
        "approach": "Redux",
        "rationale": "Better for complex state"
      },
      {
        "agent": "backend_agent",
        "approach": "React Context",
        "rationale": "Simpler, built-in"
      }
    ]
  }
}
```

**Coordinator → Agents**

```json
{
  "sender": "coordinator",
  "recipient": "all",
  "message_type": "conflict_resolution",
  "content": {
    "conflict_id": "conflict-789",
    "decision": "React Context",
    "reasoning": "Aligns with minimalism principle for MVP",
    "affected_agents": ["frontend_agent"],
    "action_required": true
  }
}
```

### 6. Status Update

**Agent → Coordinator**

```json
{
  "sender": "backend_agent",
  "recipient": "coordinator",
  "message_type": "status_update",
  "content": {
    "task_id": "task-123",
    "progress": 65,
    "current_step": "Generating API routes",
    "estimated_completion": "2024-01-01T11:30:00Z",
    "blockers": []
  }
}
```

### 7. Error Report

**Agent → Coordinator**

```json
{
  "sender": "integration_agent",
  "recipient": "coordinator",
  "message_type": "error_report",
  "content": {
    "task_id": "task-123",
    "error_type": "validation_failed",
    "error_message": "Docker build failed",
    "error_details": {
      "step": "docker_build",
      "exit_code": 1,
      "logs": "..."
    },
    "recovery_suggestions": [
      "Check Dockerfile syntax",
      "Verify base image availability"
    ]
  }
}
```

### 8. Collaboration Request

**Agent → Agent (via Coordinator)**

```json
{
  "sender": "frontend_agent",
  "recipient": "backend_agent",
  "message_type": "collaboration_request",
  "content": {
    "topic": "API endpoint structure",
    "question": "Can you provide the exact endpoint URLs and response schemas?",
    "context": {
      "feature": "user_dashboard"
    }
  }
}
```

## Communication Patterns

### 1. Request-Response Pattern

```
Coordinator → Agent: Task Assignment
Agent → Coordinator: Acknowledgment
Agent → Coordinator: Status Updates (periodic)
Agent → Coordinator: Task Completion
```

### 2. Clarification Pattern

```
Agent → Coordinator: Clarification Request
Coordinator → LLM: Analysis
Coordinator → Agent: Clarification Response
Agent → Coordinator: Updated Output
```

### 3. Conflict Resolution Pattern

```
Agent A → Coordinator: Proposal
Agent B → Coordinator: Alternative Proposal
Coordinator → LLM: Evaluate Options
Coordinator → All Agents: Decision
Affected Agents → Coordinator: Acknowledgment
```

### 4. Collaborative Discussion Pattern

```
Coordinator → All Agents: Discussion Topic
Agent A → All: Initial Thoughts
Agent B → All: Response
Agent C → All: Additional Input
Coordinator → All: Synthesis & Decision
```

## Task Specification Format

### Backend Task

```json
{
  "task_type": "generate_backend",
  "priority": "high",
  "dependencies": [],
  "specifications": {
    "entities": [
      {
        "name": "User",
        "fields": [
          {"name": "id", "type": "int", "primary_key": true},
          {"name": "email", "type": "string", "unique": true},
          {"name": "password_hash", "type": "string"}
        ],
        "relationships": [
          {"type": "one_to_many", "target": "Task"}
        ]
      }
    ],
    "endpoints": [
      {
        "method": "POST",
        "path": "/api/auth/register",
        "description": "User registration",
        "auth_required": false
      }
    ],
    "authentication": {
      "type": "JWT",
      "token_expiry": "24h"
    }
  }
}
```

### Frontend Task

```json
{
  "task_type": "generate_frontend",
  "priority": "high",
  "dependencies": ["backend_task_123"],
  "specifications": {
    "pages": [
      {
        "name": "Dashboard",
        "route": "/dashboard",
        "auth_required": true,
        "components": ["TaskList", "CreateTaskForm"]
      }
    ],
    "components": [
      {
        "name": "TaskList",
        "type": "container",
        "props": ["tasks", "onTaskUpdate"],
        "state": ["filter", "sortBy"]
      }
    ],
    "api_endpoints": [
      {
        "name": "getTasks",
        "method": "GET",
        "url": "/api/tasks"
      }
    ]
  }
}
```

## Response Format

### Success Response

```json
{
  "status": "success",
  "task_id": "task-123",
  "output": {
    "files": {
      "main.py": "content...",
      "models.py": "content..."
    },
    "metadata": {
      "lines_of_code": 500,
      "files_created": 8,
      "duration": "45s"
    }
  }
}
```

### Error Response

```json
{
  "status": "error",
  "task_id": "task-123",
  "error": {
    "code": "GENERATION_FAILED",
    "message": "Unable to generate valid SQLAlchemy models",
    "details": {
      "reason": "Invalid field type specified",
      "field": "created_at",
      "suggestion": "Use DateTime instead of Timestamp"
    },
    "recoverable": true
  }
}
```

## State Synchronization

### State Update Message

```json
{
  "sender": "coordinator",
  "recipient": "all",
  "message_type": "state_update",
  "content": {
    "build_id": "build-123",
    "updates": {
      "current_phase": "integration",
      "completed_tasks": ["backend", "frontend"],
      "pending_tasks": ["validation", "deployment"],
      "progress": 75
    }
  }
}
```

## Priority Levels

- **high**: Critical path items, blockers
- **medium**: Normal workflow tasks
- **low**: Optimization, documentation

## Timeout Configuration

| Message Type | Timeout | Retry |
|--------------|---------|-------|
| Task Assignment | 5s | 3 |
| Clarification Request | 30s | 2 |
| Code Generation | 300s | 1 |
| Validation | 60s | 2 |
| Deployment | 120s | 1 |

## Error Codes

| Code | Description |
|------|-------------|
| INVALID_SPEC | Task specification is invalid |
| GENERATION_FAILED | Code generation failed |
| VALIDATION_FAILED | Output validation failed |
| TIMEOUT | Operation timed out |
| DEPENDENCY_MISSING | Required dependency not met |
| CONFLICT_UNRESOLVED | Conflict resolution failed |

## Best Practices

1. **Always include correlation IDs** for request tracking
2. **Use structured error messages** with actionable suggestions
3. **Provide context** in clarification requests
4. **Send periodic status updates** for long-running tasks
5. **Acknowledge all messages** to confirm receipt
6. **Include timestamps** in all messages
7. **Use priority levels** appropriately
8. **Document assumptions** when making decisions
