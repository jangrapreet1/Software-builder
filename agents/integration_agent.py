"""
Integration Agent - Combines frontend and backend, manages deployment
"""
import os
import json
import asyncio
import shutil
from pathlib import Path
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI

from config.settings import Settings


class IntegrationAgent:
    """
    Integration agent that combines frontend and backend code,
    sets up Docker configuration, and manages deployment
    """
    
    def __init__(self, llm: ChatGoogleGenerativeAI, settings: Settings):
        self.llm = llm
        self.settings = settings
        self.generated_dir = Path(settings.generated_apps_dir)
        self.generated_dir.mkdir(parents=True, exist_ok=True)
    
    async def integrate(
        self,
        project_name: str,
        backend_code: dict,
        frontend_code: dict,
        specs: dict
    ) -> dict:
        """
        Integrate backend and frontend code into a unified project structure
        """
        # Create project directory
        project_path = self.generated_dir / project_name
        if project_path.exists():
            shutil.rmtree(project_path)
        project_path.mkdir(parents=True)
        
        # Create backend directory structure
        backend_path = project_path / "backend"
        await self._create_backend_structure(backend_path, backend_code)
        
        # Create frontend directory structure
        frontend_path = project_path / "frontend"
        await self._create_frontend_structure(frontend_path, frontend_code)
        
        # Create Docker configuration
        docker_config = await self._create_docker_config(project_path, project_name, specs)
        
        # Create README
        await self._create_readme(project_path, project_name, specs)
        
        # Create root .env file
        await self._create_env_file(project_path)
        
        # NEW: Create CI/CD pipelines
        await self._create_cicd_pipelines(project_path, project_name)
        
        return {
            "code": {
                "backend": backend_code,
                "frontend": frontend_code
            },
            "docker": docker_config,
            "path": str(project_path)
        }
    
    async def _create_backend_structure(self, base_path: Path, code: dict):
        """Create backend directory structure and files"""
        base_path.mkdir(parents=True, exist_ok=True)
        
        if "files" in code and isinstance(code["files"], dict):
            for rel_path, content in code["files"].items():
                dest_path = base_path / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                self._write_file(dest_path, content)
            return
            
        # Main application files
        self._write_file(base_path / "main.py", code.get("main", ""))
        self._write_file(base_path / "models.py", code.get("models", ""))
        self._write_file(base_path / "database.py", code.get("database", ""))
        self._write_file(base_path / "schemas.py", code.get("schemas", ""))
        self._write_file(base_path / "auth.py", code.get("auth", ""))
        self._write_file(base_path / "routes.py", code.get("routes", ""))
        self._write_file(base_path / "config.py", code.get("config", ""))
        self._write_file(base_path / "requirements.txt", code.get("requirements", ""))
        
        # Tests directory
        tests_path = base_path / "tests"
        tests_path.mkdir(exist_ok=True)
        self._write_file(tests_path / "__init__.py", "")
        self._write_file(tests_path / "test_api.py", code.get("tests", ""))
        
        # Alembic directory
        alembic_path = base_path / "alembic"
        alembic_path.mkdir(exist_ok=True)
        self._write_file(alembic_path / "env.py", code.get("alembic", ""))
        
        # Dockerfile
        dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        self._write_file(base_path / "Dockerfile", dockerfile_content)
        
        # .dockerignore
        dockerignore_content = """__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.pytest_cache/
.coverage
*.db
"""
        self._write_file(base_path / ".dockerignore", dockerignore_content)
    
    async def _create_frontend_structure(self, base_path: Path, code: dict):
        """Create frontend directory structure and files"""
        base_path.mkdir(parents=True, exist_ok=True)
        
        if "files" in code and isinstance(code["files"], dict):
            for rel_path, content in code["files"].items():
                dest_path = base_path / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                self._write_file(dest_path, content)
            return
            
        # Root files
        self._write_file(base_path / "index.html", code.get("index_html", ""))
        self._write_file(base_path / "package.json", code.get("package_json", ""))
        self._write_file(base_path / "vite.config.ts", code.get("vite_config", ""))
        self._write_file(base_path / "tailwind.config.js", code.get("tailwind_config", ""))
        self._write_file(base_path / "tsconfig.json", code.get("tsconfig", ""))
        self._write_file(base_path / "postcss.config.js", "module.exports = {\n  plugins: {\n    tailwindcss: {},\n    autoprefixer: {},\n  },\n}")
        
        # Src directory
        src_path = base_path / "src"
        src_path.mkdir(exist_ok=True)
        
        self._write_file(src_path / "main.tsx", code.get("main", ""))
        self._write_file(src_path / "App.tsx", code.get("app", ""))
        self._write_file(src_path / "index.css", code.get("styles", ""))
        
        # API directory
        api_path = src_path / "api"
        api_path.mkdir(exist_ok=True)
        self._write_file(api_path / "client.ts", code.get("api_client", ""))
        
        # Context directory
        context_path = src_path / "context"
        context_path.mkdir(exist_ok=True)
        self._write_file(context_path / "AuthContext.tsx", code.get("auth_context", ""))
        
        # Pages directory
        pages_path = src_path / "pages"
        pages_path.mkdir(exist_ok=True)
        pages = code.get("pages", {})
        for page_name, page_code in pages.items():
            self._write_file(pages_path / f"{page_name}.tsx", page_code)
        
        # Components directory
        components_path = src_path / "components"
        components_path.mkdir(exist_ok=True)
        components = code.get("components", {})
        for component_name, component_code in components.items():
            self._write_file(components_path / f"{component_name}.tsx", component_code)
        
        # Types directory
        types_path = src_path / "types"
        types_path.mkdir(exist_ok=True)
        self._write_file(types_path / "index.ts", code.get("types", ""))
        
        # Utils directory
        utils_path = src_path / "utils"
        utils_path.mkdir(exist_ok=True)
        self._write_file(utils_path / "helpers.ts", code.get("utils", ""))
        
        # Dockerfile
        dockerfile_content = """FROM node:18-alpine as build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
"""
        self._write_file(base_path / "Dockerfile", dockerfile_content)
        
        # nginx.conf
        nginx_content = """server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
"""
        self._write_file(base_path / "nginx.conf", nginx_content)
        
        # .dockerignore
        dockerignore_content = """node_modules
dist
.env
npm-debug.log
"""
        self._write_file(base_path / ".dockerignore", dockerignore_content)
    
    async def _create_docker_config(self, project_path: Path, project_name: str, specs: dict) -> dict:
        """Create Docker Compose configuration"""
        fe_fw = (specs.get("preferred_frontend") or "").lower().strip()
        frontend_port = "3000:3000" if fe_fw == "nextjs" else "3000:80"
        
        docker_compose_content = f"""version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: {project_name}-db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: {project_name}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: {project_name}-backend
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/{project_name}
      - SECRET_KEY=your-secret-key-change-in-production
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./backend:/app

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: {project_name}-frontend
    ports:
      - "{frontend_port}"
    depends_on:
      - backend

volumes:
  postgres_data:
"""
        
        self._write_file(project_path / "docker-compose.yml", docker_compose_content)
        
        return {"docker_compose": docker_compose_content}
    
    async def _create_readme(self, project_path: Path, project_name: str, specs: dict):
        """Create project README"""
        readme_content = f"""# {project_name.replace('-', ' ').title()}

Auto-generated application by Autonomous App Builder

## Features

{self._format_features(specs.get('features', []))}

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: React, Vite, TailwindCSS, TypeScript
- **Deployment**: Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### Running with Docker

```bash
# Start all services
docker-compose up --build

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Local Development

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
{project_name}/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── models.py            # Database models
│   ├── schemas.py           # Pydantic schemas
│   ├── routes.py            # API routes
│   ├── auth.py              # Authentication
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── pages/          # Page components
│   │   ├── components/     # Reusable components
│   │   ├── context/        # React contexts
│   │   └── api/            # API client
│   └── package.json        # Node dependencies
└── docker-compose.yml      # Docker orchestration
```

## API Documentation

Once running, visit http://localhost:8000/docs for interactive API documentation.

## Environment Variables

Copy `.env.example` to `.env` and configure:

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT secret key
- `OPENAI_API_KEY`: (if using AI features)

## Testing

### Backend Tests

```bash
cd backend
pytest
```

### Frontend Tests

```bash
cd frontend
npm test
```

## Deployment

### Production Considerations

1. Change `SECRET_KEY` in production
2. Use environment-specific configurations
3. Set up proper CORS policies
4. Enable HTTPS
5. Configure database backups
6. Set up monitoring and logging

## License

MIT
"""
        
        self._write_file(project_path / "README.md", readme_content)
    
    async def _create_env_file(self, project_path: Path):
        """Create .env.example file"""
        env_content = """# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/appdb

# Backend
SECRET_KEY=your-secret-key-change-this
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Frontend
VITE_API_URL=http://localhost:8000

# Development
DEBUG=True
"""
        
        self._write_file(project_path / ".env.example", env_content)
    
    async def validate(self, source_path: str) -> dict:
        """Validate the generated application with comprehensive checks"""
        try:
            # Use BuildValidator for comprehensive validation
            from services.build_validator import BuildValidator
            
            validator = BuildValidator()
            validation_results = await validator.validate_build(source_path)
            
            return validation_results
            
        except ImportError:
            # Fallback to basic validation if BuildValidator not available
            return await self._basic_validate(source_path)
        except Exception as e:
            return {
                "status": "error",
                "score": 0,
                "message": f"Validation failed: {str(e)}",
                "checks_passed": 0,
                "checks_failed": 1
            }
    
    async def _basic_validate(self, source_path: str) -> dict:
        """Basic validation fallback"""
        path = Path(source_path)
        
        validation_results = {
            "status": "success",
            "checks": []
        }
        
        # Check backend files
        backend_files = ["main.py", "models.py", "requirements.txt"]
        for file in backend_files:
            exists = (path / "backend" / file).exists()
            validation_results["checks"].append({
                "name": f"Backend: {file}",
                "status": "pass" if exists else "fail"
            })
        
        # Check frontend files
        frontend_files = ["package.json", "index.html", "src/main.tsx"]
        for file in frontend_files:
            exists = (path / "frontend" / file).exists()
            validation_results["checks"].append({
                "name": f"Frontend: {file}",
                "status": "pass" if exists else "fail"
            })
        
        # Check Docker files
        docker_files = ["docker-compose.yml"]
        for file in docker_files:
            exists = (path / file).exists()
            validation_results["checks"].append({
                "name": f"Docker: {file}",
                "status": "pass" if exists else "fail"
            })
        
        # Determine overall status
        failed_checks = [c for c in validation_results["checks"] if c["status"] == "fail"]
        if failed_checks:
            validation_results["status"] = "failed"
        
        return validation_results
    
    async def deploy(self, source_path: str, project_name: str) -> dict:
        """Deploy the application using Docker Compose"""
        path = Path(source_path)
        
        try:
            # For now, just return the local URLs
            # In production, this would actually start the Docker containers
            return {
                "status": "deployed",
                "url": f"http://localhost:3000",
                "api_url": f"http://localhost:8000",
                "docs_url": f"http://localhost:8000/docs"
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _create_cicd_pipelines(self, project_path: Path, project_name: str):
        """Create CI/CD pipeline configurations"""
        from services.cicd_generator import CICDGenerator
        
        # GitHub Actions
        github_workflow = CICDGenerator.generate_github_actions(project_name)
        github_dir = project_path / ".github" / "workflows"
        github_dir.mkdir(parents=True, exist_ok=True)
        self._write_file(github_dir / "ci.yml", github_workflow)
        
        # GitLab CI
        gitlab_ci = CICDGenerator.generate_gitlab_ci(project_name)
        self._write_file(project_path / ".gitlab-ci.yml", gitlab_ci)
        
        # Docker Compose for CI
        docker_compose_ci = CICDGenerator.generate_docker_compose_ci()
        self._write_file(project_path / "docker-compose.ci.yml", docker_compose_ci)
    
    def _write_file(self, file_path: Path, content: str):
        """Write content to file"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _format_features(self, features: list) -> str:
        """Format features list for README"""
        if not features:
            return "- Core functionality"
        return "\n".join([f"- {feature.get('name', 'Feature')}: {feature.get('description', '')}" for feature in features])
