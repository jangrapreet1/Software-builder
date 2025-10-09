# API Reference

## Base URL

```
http://localhost:5000
```

## Endpoints

### Health Check

**GET** `/health`

Check if the coordinator service is running.

**Response:**
```json
{
  "status": "healthy"
}
```

---

### Build Application

**POST** `/api/build`

Create a new application from a project brief.

**Request Body:**
```json
{
  "description": "Build a task management app with user authentication",
  "name": "my-task-app",
  "requirements": ["user authentication", "task sharing"]
}
```

**Parameters:**
- `description` (required): Project brief describing the application
- `name` (optional): Project name (auto-generated if not provided)
- `requirements` (optional): Array of additional requirements

**Response:**
```json
{
  "status": "success",
  "build_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Application built successfully",
  "app_url": "http://localhost:3000",
  "source_path": "/generated/my-task-app",
  "logs": [
    {
      "level": "info",
      "message": "Brief analysis complete",
      "timestamp": "2024-01-01T12:00:00Z"
    }
  ]
}
```

**Status Codes:**
- `200`: Build started successfully
- `400`: Invalid request
- `500`: Server error

---

### Get Build Status

**GET** `/api/build/{build_id}/status`

Get the current status of a build.

**Parameters:**
- `build_id` (path): Build identifier

**Response:**
```json
{
  "build_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "building",
  "progress": 65,
  "current_step": "Generating frontend code",
  "logs": [
    {
      "level": "info",
      "message": "Backend code generated",
      "timestamp": "2024-01-01T12:05:00Z"
    }
  ]
}
```

**Status Values:**
- `initializing`: Build setup
- `analyzing`: Analyzing project brief
- `building`: Active code generation
- `validating`: Running tests and validation
- `success`: Build completed successfully
- `failed`: Build failed

---

### List Builds

**GET** `/api/builds`

Get a list of all builds.

**Response:**
```json
{
  "builds": [
    {
      "build_id": "550e8400-e29b-41d4-a716-446655440000",
      "project_name": "my-task-app",
      "status": "success",
      "progress": 100
    }
  ]
}
```

---

### Delete Build

**DELETE** `/api/build/{build_id}`

Delete a build and its artifacts.

**Parameters:**
- `build_id` (path): Build identifier

**Response:**
```json
{
  "success": true,
  "message": "Build deleted"
}
```

---

## WebSocket Events (Future)

### Build Progress

**Event:** `build.progress`

Real-time updates on build progress.

**Payload:**
```json
{
  "build_id": "550e8400-e29b-41d4-a716-446655440000",
  "progress": 75,
  "current_step": "Validating build",
  "log": {
    "level": "info",
    "message": "Integration complete"
  }
}
```

### Build Complete

**Event:** `build.complete`

Notification when build finishes.

**Payload:**
```json
{
  "build_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "app_url": "http://localhost:3000"
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common error codes:
- `400`: Bad Request - Invalid input
- `404`: Not Found - Build ID not found
- `500`: Internal Server Error - Server-side error

---

## Rate Limiting

Currently no rate limiting is implemented. In production:
- Max 10 builds per hour per IP
- Max 100 status checks per minute

---

## Examples

### Python

```python
import requests

# Build an app
response = requests.post('http://localhost:5000/api/build', json={
    'description': 'Build a blog with comments',
    'name': 'my-blog'
})

build = response.json()
build_id = build['build_id']

# Check status
status_response = requests.get(f'http://localhost:5000/api/build/{build_id}/status')
status = status_response.json()

print(f"Build progress: {status['progress']}%")
```

### JavaScript

```javascript
// Build an app
const response = await fetch('http://localhost:5000/api/build', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    description: 'Build a blog with comments',
    name: 'my-blog'
  })
});

const build = await response.json();
const buildId = build.build_id;

// Check status
const statusResponse = await fetch(`http://localhost:5000/api/build/${buildId}/status`);
const status = await statusResponse.json();

console.log(`Build progress: ${status.progress}%`);
```

### cURL

```bash
# Build an app
curl -X POST http://localhost:5000/api/build \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Build a blog with comments",
    "name": "my-blog"
  }'

# Check status
curl http://localhost:5000/api/build/{build_id}/status
```

---

## SDK (Future)

```python
from appbuilder import AppBuilder

builder = AppBuilder(api_url='http://localhost:5000')

# Build application
build = builder.create(
    description='Build a blog with comments',
    name='my-blog'
)

# Wait for completion
build.wait()

# Get result
if build.is_successful():
    print(f"App URL: {build.app_url}")
    print(f"Source: {build.source_path}")
```
