"""
DocumentationAgent - Auto-generate comprehensive documentation
"""
import json
import re
from typing import Any, Dict, List
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

from config.settings import Settings


class DocumentationAgent:
    """
    Specialized agent for generating comprehensive documentation
    """
    
    def __init__(self, llm: ChatGoogleGenerativeAI, settings: Settings):
        self.llm = llm
        self.settings = settings
    
    async def generate_all_docs(
        self,
        project_name: str,
        specs: dict,
        backend_code: dict,
        frontend_code: dict,
        user_flows: List[dict]
    ) -> dict:
        """
        Generate complete documentation suite
        """
        docs = {}
        
        # Generate API documentation
        docs["api_documentation"] = await self.generate_api_docs(backend_code, specs)
        
        # Generate user guide
        docs["user_guide"] = await self.generate_user_guide(specs, user_flows, project_name)
        
        # Generate developer documentation
        dev_docs = await self.generate_developer_docs(specs, project_name)
        docs.update(dev_docs)
        
        # Generate deployment guide
        docs["deployment_guide"] = await self.generate_deployment_guide(project_name, specs)
        
        # Generate architecture documentation
        docs["architecture"] = await self.generate_architecture_docs(specs, backend_code, frontend_code)
        
        # Generate contributing guide
        docs["contributing"] = await self.generate_contributing_guide(project_name)
        
        return docs
    
    async def generate_api_docs(self, backend_code: dict, specs: dict) -> str:
        """Generate comprehensive API documentation"""
        
        # Extract routes from backend code
        routes = self._extract_routes(backend_code.get("routes", ""))
        
        api_doc = f"""# API Documentation

## Overview

This API follows REST principles and uses JSON for request and response payloads.

## Base URL

```
Production: https://api.{specs.get('domain', 'example.com')}
Development: http://localhost:8000
```

## Authentication

All endpoints except `/api/auth/*` require authentication using JWT tokens.

### Getting a Token

```bash
POST /api/auth/login
Content-Type: application/json

{{
  "email": "user@example.com",
  "password": "password"
}}
```

Response:
```json
{{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbG...",
  "token_type": "bearer"
}}
```

### Using the Token

Include the token in the Authorization header:

```
Authorization: Bearer <your_token>
```

## Endpoints

"""
        
        # Document each route
        for route in routes:
            api_doc += f"""
### {route['method']} {route['path']}

**Description**: {route.get('description', 'No description available')}

**Authentication**: {'Required' if route.get('requires_auth', True) else 'Not required'}

"""
            
            if route['method'] in ['POST', 'PUT', 'PATCH']:
                api_doc += """
**Request Body**:
```json
{
  "field1": "value1",
  "field2": "value2"
}
```

"""
            
            api_doc += """
**Response**:
```json
{
  "success": true,
  "data": {}
}
```

**Status Codes**:
- `200 OK`: Success
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Missing or invalid token
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

"""
        
        api_doc += """
## Error Handling

All errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

## Rate Limiting

- **Rate Limit**: 100 requests per minute per IP
- **Headers**:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Time when limit resets (Unix timestamp)

## Pagination

List endpoints support pagination:

```
GET /api/items?page=1&page_size=20
```

Response includes pagination metadata:

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "pages": 5
}
```

## Filtering and Sorting

```
GET /api/items?sort=created_at:desc&filter=status:active
```

## SDKs and Examples

### Python Example

```python
import requests

# Login
response = requests.post('http://localhost:8000/api/auth/login', json={
    'email': 'user@example.com',
    'password': 'password'
})
token = response.json()['access_token']

# Authenticated request
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://localhost:8000/api/items', headers=headers)
items = response.json()
```

### JavaScript Example

```javascript
// Login
const loginRes = await fetch('http://localhost:8000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'user@example.com', password: 'password' })
});
const { access_token } = await loginRes.json();

// Authenticated request
const itemsRes = await fetch('http://localhost:8000/api/items', {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
const items = await itemsRes.json();
```

## WebSocket Support

Real-time updates are available via WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

## API Versioning

The API uses URL versioning:

```
/api/v1/resource
/api/v2/resource
```

Current version: **v1**
"""
        
        return api_doc
    
    async def generate_user_guide(self, specs: dict, user_flows: List[dict], project_name: str) -> str:
        """Generate end-user documentation"""
        
        user_guide = f"""# {project_name.replace('-', ' ').title()} - User Guide

## Introduction

Welcome to {project_name.replace('-', ' ').title()}! This guide will help you get started.

## Getting Started

### Creating an Account

1. Navigate to the application URL
2. Click **Sign Up**
3. Enter your email and password
4. Verify your email (check your inbox)
5. Log in with your credentials

### Logging In

1. Go to the login page
2. Enter your email and password
3. Click **Sign In**

## Features

"""
        
        # Document each feature from specs
        features = specs.get('features', [])
        for feature in features:
            if isinstance(feature, dict):
                user_guide += f"""
### {feature.get('name', 'Feature')}

{feature.get('description', 'No description available')}

**How to use:**

1. Navigate to the relevant section
2. Follow the on-screen instructions
3. Save your changes

"""
        
        # Document user flows
        user_guide += "\n## Common Workflows\n\n"
        
        for flow in user_flows:
            if isinstance(flow, dict):
                user_guide += f"""
### {flow.get('name', 'Workflow')}

**Steps:**

"""
                steps = flow.get('steps', [])
                for i, step in enumerate(steps, 1):
                    user_guide += f"{i}. {step}\n"
                
                user_guide += "\n"
        
        user_guide += """
## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save |
| `Ctrl+N` | New |
| `Ctrl+F` | Search |
| `Esc` | Close modal |

## Troubleshooting

### I forgot my password

1. Click **Forgot Password** on the login page
2. Enter your email
3. Check your inbox for reset link
4. Follow the link to set a new password

### I'm not receiving emails

1. Check your spam folder
2. Verify your email address is correct
3. Contact support if the issue persists

### The page is loading slowly

1. Check your internet connection
2. Try refreshing the page
3. Clear your browser cache
4. Try a different browser

## Support

For additional help:

- **Email**: support@example.com
- **Documentation**: https://docs.example.com
- **Community Forum**: https://community.example.com

## Privacy and Security

- Your data is encrypted
- We never share your information
- You can delete your account anytime

For more information, see our [Privacy Policy](#).
"""
        
        return user_guide
    
    async def generate_developer_docs(self, specs: dict, project_name: str) -> dict:
        """Generate developer documentation"""
        
        docs = {}
        
        # Architecture documentation
        docs["architecture"] = f"""# Architecture Overview

## System Architecture

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Frontend  │─────▶│   Backend   │─────▶│  Database   │
│   (React)   │      │  (FastAPI)  │      │ (PostgreSQL)│
└─────────────┘      └─────────────┘      └─────────────┘
       │                     │                     
       └─────────────────────┴──────────────────────
                           │
                      ┌────────────┐
                      │   Redis    │
                      │  (Cache)   │
                      └────────────┘
```

## Technology Stack

### Backend
- **Framework**: FastAPI 0.104+
- **ORM**: SQLAlchemy 2.0+
- **Database**: PostgreSQL 15+
- **Authentication**: JWT (python-jose)
- **Validation**: Pydantic v2
- **Testing**: pytest

### Frontend
- **Framework**: React 18+
- **Build Tool**: Vite 5+
- **Styling**: TailwindCSS 3+
- **State Management**: React Context + Hooks
- **Routing**: React Router v6
- **HTTP Client**: Axios
- **Testing**: Vitest

### Infrastructure
- **Containerization**: Docker
- **Orchestration**: Docker Compose
- **Reverse Proxy**: Nginx
- **Cache**: Redis 7+

## Project Structure

```
{project_name}/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── routes.py            # API routes
│   ├── auth.py              # Authentication
│   ├── database.py          # Database config
│   ├── config.py            # Settings
│   ├── tests/               # Test suite
│   └── alembic/             # Migrations
├── frontend/
│   ├── src/
│   │   ├── main.tsx         # Entry point
│   │   ├── App.tsx          # Root component
│   │   ├── pages/           # Page components
│   │   ├── components/      # Reusable components
│   │   ├── context/         # React contexts
│   │   ├── api/             # API client
│   │   ├── types/           # TypeScript types
│   │   └── utils/           # Utilities
│   ├── public/              # Static assets
│   └── index.html           # HTML template
├── docker-compose.yml       # Services orchestration
└── README.md                # Project documentation
```

## Design Patterns

### Backend Patterns

1. **Repository Pattern**: Data access abstraction
2. **Dependency Injection**: FastAPI's Depends system
3. **DTO Pattern**: Pydantic schemas for data transfer
4. **Middleware Pattern**: Request/response processing

### Frontend Patterns

1. **Component Composition**: Reusable React components
2. **Container/Presenter**: Separation of logic and UI
3. **Custom Hooks**: Shared stateful logic
4. **Context API**: Global state management

## Security

- **Authentication**: JWT tokens with refresh mechanism
- **Authorization**: Role-based access control (RBAC)
- **Input Validation**: Pydantic models
- **SQL Injection Prevention**: SQLAlchemy ORM
- **XSS Protection**: React's built-in escaping
- **CORS**: Configured for specific origins
- **Rate Limiting**: Per-IP request throttling
- **HTTPS**: Enforced in production

## Performance

- **Caching**: Redis for frequently accessed data
- **Database**: Connection pooling, query optimization
- **Frontend**: Code splitting, lazy loading
- **Compression**: Gzip for responses
- **CDN**: Static asset delivery (production)

## Monitoring

- **Logging**: Structured JSON logs
- **Metrics**: Performance tracking
- **Error Tracking**: Sentry integration (optional)
- **Health Checks**: `/health` endpoint
"""
        
        # Setup guide
        docs["setup"] = f"""# Development Setup

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+ (optional, for caching)
- Docker and Docker Compose (for containerized development)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourorg/{project_name}.git
cd {project_name}
```

### 2. Using Docker (Recommended)

```bash
docker-compose up --build
```

Access:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 3. Local Development

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Set up database
createdb {project_name}

# Run migrations
alembic upgrade head

# Start server
uvicorn main:app --reload
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Environment Variables

Create `.env` files in backend and frontend:

### Backend `.env`

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/{project_name}
SECRET_KEY=your-secret-key-minimum-32-characters-long
REDIS_URL=redis://localhost:6379
CORS_ORIGINS=http://localhost:3000
```

### Frontend `.env`

```
VITE_API_URL=http://localhost:8000
```

## Running Tests

### Backend Tests

```bash
cd backend
pytest
pytest --cov=. --cov-report=html  # With coverage
```

### Frontend Tests

```bash
cd frontend
npm test
npm run test:coverage
```

## Code Quality

### Backend

```bash
# Linting
flake8 .
black --check .

# Type checking
mypy .
```

### Frontend

```bash
# Linting
npm run lint

# Type checking
npm run type-check
```

## Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Debugging

### Backend

Use VSCode launch configuration or:

```bash
python -m debugpy --listen 5678 --wait-for-client -m uvicorn main:app --reload
```

### Frontend

React DevTools browser extension + Vite's HMR

## Common Issues

### Database Connection Error

- Ensure PostgreSQL is running
- Check DATABASE_URL is correct
- Verify database exists

### Port Already in Use

```bash
# Find process
lsof -i :8000  # Backend
lsof -i :3000  # Frontend

# Kill process
kill -9 <PID>
```
"""
        
        return docs
    
    async def generate_deployment_guide(self, project_name: str, specs: dict) -> str:
        """Generate deployment documentation"""
        
        return f"""# Deployment Guide

## Production Deployment

### Prerequisites

- Domain name configured
- SSL certificate (Let's Encrypt recommended)
- Cloud hosting (AWS, GCP, Azure, or DigitalOcean)
- Docker installed on server

### Option 1: Docker Compose Deployment

#### 1. Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose -y
```

#### 2. Clone and Configure

```bash
git clone https://github.com/yourorg/{project_name}.git
cd {project_name}

# Create production .env
cp .env.example .env
nano .env  # Edit with production values
```

#### 3. Deploy

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Option 2: Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {project_name}-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: {project_name}/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

### Option 3: Platform as a Service

#### Heroku

```bash
heroku create {project_name}
heroku addons:create heroku-postgresql:hobby-dev
git push heroku main
```

#### Vercel (Frontend) + Railway (Backend)

Frontend on Vercel:
```bash
vercel --prod
```

Backend on Railway:
```bash
railway up
```

## CI/CD Pipeline

### GitHub Actions

See `.github/workflows/deploy.yml` for automated deployment.

### GitLab CI

See `.gitlab-ci.yml` for automated deployment.

## Monitoring

### Application Monitoring

- **Logs**: CloudWatch, Papertrail, or Loggly
- **Metrics**: Prometheus + Grafana
- **Uptime**: UptimeRobot or Pingdom
- **Errors**: Sentry or Rollbar

### Infrastructure Monitoring

- **Server**: Datadog, New Relic
- **Database**: pgAdmin, CloudWatch RDS
- **Performance**: Lighthouse CI

## Backup Strategy

### Database Backups

```bash
# Automated daily backup
0 2 * * * pg_dump {project_name} > /backups/db_$(date +\%Y\%m\%d).sql
```

### File Backups

Use AWS S3, Google Cloud Storage, or Azure Blob Storage.

## Scaling

### Horizontal Scaling

- Add more application instances behind load balancer
- Use managed database (AWS RDS, Google Cloud SQL)
- Implement Redis cluster for caching

### Vertical Scaling

- Increase server resources (CPU, RAM)
- Optimize database queries
- Enable CDN for static assets

## Security Checklist

- [ ] HTTPS enabled with valid SSL certificate
- [ ] Environment variables secured (no hardcoded secrets)
- [ ] Database backups automated
- [ ] Firewall configured (allow only necessary ports)
- [ ] Security headers enabled (HSTS, CSP, etc.)
- [ ] Rate limiting enabled
- [ ] Regular security updates scheduled
- [ ] Logging and monitoring active

## Rollback Procedure

```bash
# Rollback to previous version
git revert HEAD
docker-compose down
docker-compose up -d --build

# Or use specific version
git checkout <previous-commit>
docker-compose up -d --build
```

## Post-Deployment

1. Verify all services are running
2. Run smoke tests
3. Check logs for errors
4. Test critical user flows
5. Monitor performance metrics
6. Update documentation
"""
    
    async def generate_contributing_guide(self, project_name: str) -> str:
        """Generate contributing guidelines"""
        
        return f"""# Contributing to {project_name.replace('-', ' ').title()}

Thank you for your interest in contributing! This guide will help you get started.

## Code of Conduct

Be respectful, inclusive, and professional in all interactions.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported
2. Create a new issue with:
   - Clear title
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details
   - Screenshots if applicable

### Suggesting Features

1. Check if the feature has been suggested
2. Create a new issue describing:
   - Use case
   - Proposed solution
   - Alternatives considered

### Submitting Code

#### 1. Fork and Clone

```bash
git clone https://github.com/yourorg/{project_name}.git
cd {project_name}
```

#### 2. Create Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming:
- `feature/` for new features
- `fix/` for bug fixes
- `docs/` for documentation
- `refactor/` for code improvements

#### 3. Make Changes

- Follow existing code style
- Write tests for new code
- Update documentation
- Keep commits atomic and descriptive

#### 4. Test

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm test
```

#### 5. Commit

```bash
git add .
git commit -m "feat: add new feature"
```

Commit message format:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation changes
- `style:` formatting changes
- `refactor:` code refactoring
- `test:` adding tests
- `chore:` maintenance tasks

#### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear description of changes
- Link to related issues
- Screenshots for UI changes

## Development Guidelines

### Code Style

#### Python (Backend)
- Follow PEP 8
- Use type hints
- Write docstrings
- Max line length: 100

#### TypeScript (Frontend)
- Follow Airbnb style guide
- Use meaningful variable names
- Write JSDoc comments
- Prefer functional components

### Testing

- Write tests for new features
- Maintain >80% code coverage
- Test edge cases
- Mock external dependencies

### Documentation

- Update README if needed
- Add docstrings/comments
- Update API documentation
- Include examples

## Review Process

1. Automated tests must pass
2. Code review by maintainer
3. Address review feedback
4. Approval and merge

## Getting Help

- Open an issue for questions
- Join our Discord/Slack
- Check existing documentation

Thank you for contributing! 🎉
"""
    
    def _extract_routes(self, routes_code: str) -> List[Dict]:
        """Extract route information from routes code"""
        routes = []
        
        # Simple regex-based extraction (in production, use AST parsing)
        route_pattern = r'@router\.(get|post|put|patch|delete)\(["\']([^"\']+)["\']\)'
        matches = re.finditer(route_pattern, routes_code)
        
        for match in matches:
            method = match.group(1).upper()
            path = match.group(2)
            
            # Try to find description from nearby comments
            line_start = routes_code.rfind('\n', 0, match.start())
            line_content = routes_code[line_start:match.start()]
            
            description = "No description available"
            if '"""' in line_content or "'''" in line_content:
                desc_match = re.search(r'["\']([^"\']+)["\']', line_content)
                if desc_match:
                    description = desc_match.group(1)
            
            routes.append({
                "method": method,
                "path": path,
                "description": description,
                "requires_auth": "Depends" in line_content
            })
        
        return routes
    
    async def generate_architecture_docs(self, specs: dict, backend_code: dict, frontend_code: dict) -> str:
        """Generate detailed architecture documentation"""
        
        return """# Detailed Architecture Documentation

## Component Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                         Client Browser                         │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │   React UI  │◀▶│ State Manager│◀▶│  API Client (Axios) │  │
│  └─────────────┘  └──────────────┘  └─────────────────────┘  │
└───────────────────────────────────────┬───────────────────────┘
                                        │ HTTPS/WebSocket
                                        ▼
┌───────────────────────────────────────────────────────────────┐
│                      API Gateway / Nginx                       │
│                    (Load Balancer, SSL)                        │
└───────────────────────────────────────┬───────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────┐
        │                               │                   │
        ▼                               ▼                   ▼
┌───────────────┐            ┌──────────────────┐  ┌──────────────┐
│  FastAPI App  │            │   Redis Cache    │  │  Job Queue   │
│   Instance 1  │            │  (Session/Data)  │  │   (Celery)   │
└───────┬───────┘            └──────────────────┘  └──────────────┘
        │                               │
        ├───────────────────────────────┤
        ▼                               ▼
┌───────────────────────────────────────────────┐
│           PostgreSQL Database                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Primary │◀▶│ Replica  │◀▶│ Backup   │    │
│  └──────────┘  └──────────┘  └──────────┘    │
└───────────────────────────────────────────────┘
```

## Data Flow

### Read Operation
1. Client sends GET request
2. Nginx routes to available FastAPI instance
3. FastAPI checks Redis cache
4. If cache miss, queries PostgreSQL
5. Result cached in Redis
6. JSON response sent to client

### Write Operation
1. Client sends POST/PUT request
2. FastAPI validates input (Pydantic)
3. Transaction opened on PostgreSQL
4. Data written to database
5. Cache invalidated
6. Success response sent
7. Background job queued if needed

## Security Architecture

```
┌──────────────┐     ┌─────────────────────────┐
│   Client     │────▶│  TLS 1.3 Encryption     │
└──────────────┘     └────────────┬────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │  Rate Limiter           │
                     │  (Per IP/User)          │
                     └────────────┬────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │  JWT Verification       │
                     │  (Auth Middleware)      │
                     └────────────┬────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │  RBAC Check             │
                     │  (Authorization)        │
                     └────────────┬────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │  Input Validation       │
                     │  (Pydantic Schemas)     │
                     └────────────┬────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │  Business Logic         │
                     └─────────────────────────┘
```

## Scalability Strategy

### Application Layer
- Stateless design (scales horizontally)
- Load balancer distributes requests
- Auto-scaling based on CPU/memory

### Caching Layer
- Redis cluster for high availability
- Cache-aside pattern
- TTL-based expiration

### Database Layer
- Read replicas for scaling reads
- Connection pooling
- Query optimization

### File Storage
- CDN for static assets
- Object storage (S3, GCS) for uploads

## Performance Optimizations

1. **Database Level**
   - Indexes on foreign keys
   - Query result caching
   - Connection pooling

2. **Application Level**
   - Redis caching
   - Async I/O operations
   - Background job processing

3. **Frontend Level**
   - Code splitting
   - Lazy loading
   - Service worker caching

## Monitoring Architecture

```
Application Logs ─────┐
                      │
API Metrics ──────────┼────▶ Aggregation ────▶ Visualization
                      │        Service           Dashboard
Database Metrics ─────┘     (Prometheus)        (Grafana)
```

## Disaster Recovery

1. **Regular Backups**
   - Database: Daily snapshots
   - Files: Incremental backups
   - Configurations: Version controlled

2. **Failover Strategy**
   - Database replication
   - Multi-region deployment
   - Health checks and auto-recovery

3. **Recovery Time Objective (RTO)**: < 1 hour
4. **Recovery Point Objective (RPO)**: < 15 minutes
"""
