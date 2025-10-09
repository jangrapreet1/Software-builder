"""
Backend Agent - Generates FastAPI backend code
"""
import json
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

from config.settings import Settings
from .templates.backend_templates import BackendTemplates


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
        
        response = await self.llm.ainvoke(messages)
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
        
        response = await self.llm.ainvoke(messages)
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
        
        response = await self.llm.ainvoke(messages)
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
        
        response = await self.llm.ainvoke(messages)
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
        
        response = await self.llm.ainvoke(messages)
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
        
        response = await self.llm.ainvoke(messages)
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
