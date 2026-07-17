"""
Backend Agent - Generates FastAPI backend code
"""
import ast
import json
from typing import Any, Dict, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

from config.settings import Settings
from .templates.backend_templates import BackendTemplates
from services.retry_utils import call_llm_with_retry
from services.framework_registry import get_framework_manifest


class BackendAgent:
    """
    Specialized agent for generating FastAPI backend code
    """
    
    def __init__(self, llm: ChatGoogleGenerativeAI, settings: Settings):
        self.llm = llm
        self.settings = settings
        self.templates = BackendTemplates()
    
    async def generate_code(
        self,
        tasks: list[dict],
        entities: list[dict],
        specs: dict
    ) -> dict:
        """
        Generate complete backend code based on tasks and specifications
        """
        if (specs.get("preferred_backend") or "").lower().strip() == "express":
            return await self._generate_express(tasks, entities, specs)

        # Generate code for each component
        code = {
            "main": await self._generate_main_file(specs),
            "models": await self._generate_models(entities),
            "database": self._generate_database_config(),
            "schemas": await self._generate_schemas(entities),
            "auth": await self._generate_auth(specs.get("authentication", {})),
            "routes": await self._generate_routes(tasks, entities),
            "config": self._generate_config(),
            "requirements": self._generate_requirements(),
            "tests": await self._generate_tests(entities),
            "alembic": self._generate_alembic_config()
        }
        
        # Enforce FastAPI requirements manifest
        try:
            manifest = get_framework_manifest("fastapi") or {}
            req_text = code.get("requirements") or ""
            existing = {line.strip().split("[")[0].split("=")[0] for line in req_text.splitlines() if line.strip() and not line.strip().startswith("#")}
            required = manifest.get("required_packages", [])
            missing = [p for p in required if p not in existing]
            if missing:
                additions = "\n".join(missing)
                code["requirements"] = (req_text.rstrip() + "\n" + additions + "\n") if req_text else additions + "\n"
        except Exception:
            pass

        # NEW: Validate generated code quality
        validation = await self._validate_code_quality(code)
        
        if validation["has_critical_issues"]:
            # Auto-fix critical issues
            code = await self._fix_code_issues(code, validation["issues"])
        
        # Generate migrations
        code["migrations"] = await self.generate_migrations(entities)
        
        return code
    
    async def _generate_main_file(self, specs: dict) -> str:
        """Generate main.py FastAPI application"""
        system_prompt = """You are an expert FastAPI developer. Generate a production-ready main.py file.

Include:
- FastAPI app initialization with metadata
- CORS middleware
- Database session management
- Router includes
- Health check endpoint
- Error handlers
- Startup and shutdown events

Use modern FastAPI patterns and best practices."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Specifications:\n{json.dumps(specs, indent=2)}\n\nGenerate main.py")
        ]
        
        response = await call_llm_with_retry(self.llm, messages)
        return self._extract_code(response.content) or self.templates.get_main_template()
    
    async def _generate_models(self, entities: list[dict]) -> str:
        """Generate SQLAlchemy models"""
        system_prompt = """You are an expert in SQLAlchemy. Generate database models.

For each entity, create:
- SQLAlchemy model class
- Proper field types
- Relationships
- Indexes where appropriate
- __repr__ method

Use SQLAlchemy 2.0 style with type annotations."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Entities:\n{json.dumps(entities, indent=2)}\n\nGenerate models.py")
        ]
        
        response = await call_llm_with_retry(self.llm, messages)
        return self._extract_code(response.content) or self.templates.get_models_template(entities)
    
    def _generate_database_config(self) -> str:
        """Generate database configuration"""
        return self.templates.get_database_template()
    
    async def _generate_schemas(self, entities: list[dict]) -> str:
        """Generate Pydantic schemas"""
        system_prompt = """You are an expert in Pydantic. Generate schema classes.

For each entity, create:
- Base schema (shared fields)
- Create schema (for POST requests)
- Update schema (for PUT/PATCH requests)
- Response schema (for GET responses)

Use Pydantic v2 with proper validation."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Entities:\n{json.dumps(entities, indent=2)}\n\nGenerate schemas.py")
        ]
        
        response = await call_llm_with_retry(self.llm, messages)
        return self._extract_code(response.content) or self.templates.get_schemas_template(entities)
    
    async def _generate_auth(self, auth_specs: dict) -> str:
        """Generate authentication module"""
        system_prompt = """You are an expert in FastAPI authentication. Generate auth module.

Include:
- Password hashing (bcrypt)
- JWT token creation and verification
- OAuth2 password bearer
- User authentication functions
- Dependencies for protected routes

Use python-jose for JWT and passlib for hashing."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Auth Specs:\n{json.dumps(auth_specs, indent=2)}\n\nGenerate auth.py")
        ]
        
        response = await call_llm_with_retry(self.llm, messages)
        return self._extract_code(response.content) or self.templates.get_auth_template()
    
    async def _generate_routes(self, tasks: list[dict], entities: list[dict]) -> str:
        """Generate API routes"""
        system_prompt = """You are an expert FastAPI developer. Generate API routes.

For each entity, create:
- GET /items - List all (with pagination)
- GET /items/{id} - Get one
- POST /items - Create
- PUT /items/{id} - Update
- DELETE /items/{id} - Delete

Include:
- Proper status codes
- Error handling
- Authentication dependencies
- Query parameters for filtering
- Response models

Use APIRouter and follow REST conventions."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Tasks:\n{json.dumps(tasks, indent=2)}\nEntities:\n{json.dumps(entities, indent=2)}\n\nGenerate routes.py")
        ]
        
        response = await call_llm_with_retry(self.llm, messages)
        return self._extract_code(response.content) or self.templates.get_routes_template(entities)
    
    def _generate_config(self) -> str:
        """Generate configuration module"""
        return self.templates.get_config_template()
    
    def _generate_requirements(self) -> str:
        """Generate requirements.txt"""
        return self.templates.get_requirements_template()
    
    async def _generate_tests(self, entities: list[dict]) -> str:
        """Generate test cases"""
        system_prompt = """You are an expert in pytest. Generate test cases.

Include:
- Test fixtures
- Authentication tests
- CRUD endpoint tests for each entity
- Error handling tests

Use pytest-asyncio for async tests."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Entities:\n{json.dumps(entities, indent=2)}\n\nGenerate test_api.py")
        ]
        
        response = await call_llm_with_retry(self.llm, messages)
        return self._extract_code(response.content) or self.templates.get_tests_template()
    
    def _generate_alembic_config(self) -> str:
        """Generate Alembic configuration"""
        return self.templates.get_alembic_template()
    
    def _extract_code(self, response: str) -> str:
        """Extract code from markdown code blocks"""
        if "```python" in response:
            parts = response.split("```python")
            if len(parts) > 1:
                code = parts[1].split("```")[0]
                return code.strip()
        elif "```" in response:
            parts = response.split("```")
            if len(parts) > 1:
                code = parts[1].split("```")[0]
                # Remove language identifier if present
                lines = code.split("\n")
                if lines[0].strip() in ["python", "py"]:
                    lines = lines[1:]
                return "\n".join(lines).strip()
        return response.strip()
    
    async def _validate_code_quality(self, code: dict) -> Dict:
        """Validate generated code for syntax and quality issues"""
        issues = []
        
        for file_name, content in code.items():
            if not isinstance(content, str):
                continue
            
            # Check Python syntax
            try:
                ast.parse(content)
            except SyntaxError as e:
                issues.append({
                    "file": file_name,
                    "error": str(e),
                    "severity": "critical",
                    "line": e.lineno
                })
            
            # Check for dangerous patterns
            if "eval(" in content or "exec(" in content:
                issues.append({
                    "file": file_name,
                    "error": "Unsafe eval/exec usage",
                    "severity": "critical"
                })
            
            # Check for missing imports
            if file_name == "main" and "FastAPI" in content and "from fastapi import" not in content:
                issues.append({
                    "file": file_name,
                    "error": "Missing FastAPI import",
                    "severity": "high"
                })
        
        return {
            "has_critical_issues": any(i["severity"] == "critical" for i in issues),
            "issues": issues
        }
    
    async def _fix_code_issues(self, code: dict, issues: List[Dict]) -> dict:
        """Auto-fix common code issues"""
        fixed_code = code.copy()
        
        for issue in issues:
            if issue["severity"] == "critical":
                file_name = issue["file"]
                if file_name in fixed_code:
                    content = fixed_code[file_name]
                    
                    # Remove eval/exec
                    if "eval" in issue["error"].lower() or "exec" in issue["error"].lower():
                        content = content.replace("eval(", "# REMOVED: eval(")
                        content = content.replace("exec(", "# REMOVED: exec(")
                    
                    # Add missing imports
                    if "Missing" in issue["error"] and "import" in issue["error"]:
                        if "FastAPI" in issue["error"]:
                            content = "from fastapi import FastAPI, Request\n" + content
                    
                    fixed_code[file_name] = content
        
        return fixed_code
    
    async def generate_migrations(self, entities: list[dict]) -> str:
        """Generate Alembic migration scripts"""
        system_prompt = """Generate an Alembic migration script for these database models.
        
Include:
- Table creation with proper column types
- Primary key constraints
- Foreign key relationships with proper cascades
- Indexes for foreign keys and frequently queried fields
- NOT NULL constraints
- Unique constraints where appropriate
- Proper downgrade logic

Use Alembic op.* methods."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Entities:\n{json.dumps(entities, indent=2)}\n\nGenerate migration")
        ]
        
        try:
            response = await call_llm_with_retry(self.llm, messages)
            return self._extract_code(response.content) or self._get_default_migration(entities)
        except Exception:
            return self._get_default_migration(entities)
    
    def _get_default_migration(self, entities: list[dict]) -> str:
        """Generate default migration template"""
        return '''"""Initial migration

Revision ID: 001
Create Date: 2024-01-01

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create tables based on models
    pass

def downgrade():
    # Drop tables
    pass
'''

    async def _generate_express(self, tasks: list[dict], entities: list[dict], specs: dict) -> dict:
        """Generate a complete Node.js/Express backend application"""
        system_prompt = """You are an expert Node.js and Express developer. Generate a complete, production-ready REST API application.
You must output a JSON object mapping relative file paths to their complete file contents.
Do not wrap the JSON in markdown code blocks or add any other text outside the JSON. The JSON keys must be relative file paths, and values must be file contents.

Generate the following files:
1. package.json (with express, cors, dotenv, pg, bcryptjs, jsonwebtoken dependencies)
2. server.js (main entry point, initializes CORS, dotenv, database connection, imports and mounts routers, includes health check)
3. db.js (PostgreSQL pool connection using the 'pg' library)
4. middleware/auth.js (JWT authentication middleware checking the Authorization header)
5. routes/auth.js (endpoints for signup and login with token generation)
6. routes/items.js (generic endpoints for all entities provided: GET, GET by ID, POST, PUT, DELETE, including authentication checks)
7. Dockerfile (Node 18 alpine exposing port 8000 and starting 'node server.js')
8. .dockerignore (ignoring node_modules, etc.)
"""
        messages = [
            SystemMessage(content=system_prompt + f"\nEntities:\n{json.dumps(entities, indent=2)}\n\nTasks:\n{json.dumps(tasks, indent=2)}"),
            HumanMessage(content="Generate the complete file map JSON for the Express application.")
        ]
        try:
            response = await call_llm_with_retry(self.llm, messages)
            clean_content = response.content.strip()
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
            clean_content = clean_content.strip()
            
            files = json.loads(clean_content)
            return {"files": files}
        except Exception:
            return {"files": self._get_express_fallback_files(entities)}

    def _get_express_fallback_files(self, entities: list[dict]) -> dict:
        """Provide fallback files for Node.js/Express backend"""
        pkg_json = """{
  "name": "express-backend",
  "version": "1.0.0",
  "main": "server.js",
  "dependencies": {
    "bcryptjs": "^2.4.3",
    "cors": "^2.8.5",
    "dotenv": "^16.4.5",
    "express": "^4.19.2",
    "jsonwebtoken": "^9.0.2",
    "pg": "^8.11.5"
  }
}"""
        server_js = """const express = require('express');
const cors = require('cors');
require('dotenv').config();

const app = express();
app.use(cors());
app.use(express.json());

app.get('/health', (req, res) => res.json({ status: 'healthy' }));

const port = process.env.PORT || 8000;
app.listen(port, () => console.log(`Server running on port ${port}`));
"""
        db_js = """const { Pool } = require('pg');
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});
module.exports = {
  query: (text, params) => pool.query(text, params),
  pool
};"""
        dockerfile = """FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 8000
CMD ["node", "server.js"]
"""
        return {
            "package.json": pkg_json,
            "server.js": server_js,
            "db.js": db_js,
            "Dockerfile": dockerfile
        }
