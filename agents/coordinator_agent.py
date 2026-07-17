"""
Coordinator Agent - Analyzes briefs and orchestrates the build process
"""
import json
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from services.retry_utils import call_llm_with_retry
from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import Settings


class CoordinatorAgent:
    """
    Main coordinator agent that analyzes project briefs and orchestrates
    the entire app-building process
    """
    
    def __init__(self, llm: ChatGoogleGenerativeAI, settings: Settings):
        self.llm = llm
        self.settings = settings
    
    async def analyze_brief(self, brief: str) -> dict:
        """
        Analyze a project brief and extract features, entities, and user flows
        """
        if not brief or not brief.strip():
            raise ValueError("Project brief cannot be empty")
        
        system_prompt = """You are an expert software architect analyzing project requirements.
        
Your task is to analyze the project brief and extract:
1. **Features**: List of key features the application should have
2. **Entities**: Data models/entities needed (e.g., User, Task, Project)
3. **User Flows**: Key user interactions and workflows

Return your analysis as JSON with this structure:
{
    "features": [
        {"name": "feature name", "description": "detailed description", "priority": "high|medium|low"}
    ],
    "entities": [
        {"name": "entity name", "fields": [{"name": "field", "type": "type", "required": true}], "relationships": []}
    ],
    "user_flows": [
        {"name": "flow name", "steps": ["step 1", "step 2"], "actors": ["user role"]}
    ]
}

Be thorough and infer reasonable requirements from the brief. Return ONLY valid JSON."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Project Brief: {brief}")
            ]
            
            response = await call_llm_with_retry(self.llm, messages)
            
            # Try to extract JSON from response
            content = response.content.strip()
            
            # Remove markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            
            # Validate structure
            if not isinstance(result, dict):
                raise ValueError("Response is not a dictionary")
            if "features" not in result or "entities" not in result or "user_flows" not in result:
                raise ValueError("Missing required keys in response")
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}. Falling back to default structure.")
            return self._fallback_parse(response.content if 'response' in locals() else brief)
        except Exception as e:
            print(f"Error analyzing brief: {e}. Using fallback.")
            return self._fallback_parse(brief)
    
    async def generate_technical_specs(
        self,
        features: list[dict],
        entities: list[dict],
        user_flows: list[dict]
    ) -> dict:
        """
        Generate detailed technical specifications from requirements
        """
        try:
            system_prompt = """You are a technical architect creating detailed specifications.

Given features, entities, and user flows, create comprehensive technical specs including:
1. **Architecture**: System architecture and patterns
2. **API Endpoints**: REST API design
3. **Database Schema**: Table structures and relationships
4. **Authentication**: Auth strategy (JWT, sessions, etc.)
5. **Frontend Structure**: Component hierarchy
6. **Styling**: UI/UX approach
7. **Deployment**: Deployment strategy

Return ONLY valid JSON."""

            context = json.dumps({
                "features": features,
                "entities": entities,
                "user_flows": user_flows
            }, indent=2)
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Requirements:\n{context}\n\nGenerate technical specifications.")
            ]
            
            response = await call_llm_with_retry(self.llm, messages)
            
            # Try to extract JSON
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error in specs generation: {e}. Using defaults.")
            return self._generate_default_specs(features, entities)
        except Exception as e:
            print(f"Error generating specs: {e}. Using defaults.")
            return self._generate_default_specs(features, entities)
    
    async def plan_tasks(self, technical_specs: dict) -> dict:
        """
        Break down technical specs into concrete development tasks
        """
        try:
            system_prompt = """You are a project planner creating development tasks.

Given technical specifications, break them into:
1. **Backend Tasks**: API endpoints, models, auth, database, etc.
2. **Frontend Tasks**: Components, pages, routing, state management, etc.

Each task should have:
- name: Task name
- description: What needs to be built
- dependencies: Other tasks this depends on
- priority: high, medium, or low
- files: List of files to create/modify

Return ONLY valid JSON with "backend" and "frontend" arrays."""

            context = json.dumps(technical_specs, indent=2)
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Technical Specs:\n{context}\n\nCreate task breakdown.")
            ]
            
            response = await call_llm_with_retry(self.llm, messages)
            
            # Try to extract JSON
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            
            # Validate structure
            if "backend" not in result or "frontend" not in result:
                raise ValueError("Missing backend or frontend tasks")
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error in task planning: {e}. Using defaults.")
            return self._generate_default_tasks(technical_specs)
        except Exception as e:
            print(f"Error planning tasks: {e}. Using defaults.")
            return self._generate_default_tasks(technical_specs)
    
    def _fallback_parse(self, content: str) -> dict:
        """Fallback parsing when JSON fails"""
        return {
            "features": [
                {"name": "Core Functionality", "description": "Main application features", "priority": "high"}
            ],
            "entities": [
                {"name": "User", "fields": [{"name": "id", "type": "int", "required": True}], "relationships": []}
            ],
            "user_flows": [
                {"name": "Main Flow", "steps": ["Login", "Use App"], "actors": ["User"]}
            ]
        }
    
    def _generate_default_specs(self, features: list[dict], entities: list[dict]) -> dict:
        """Generate default technical specs"""
        return {
            "architecture": {
                "pattern": "REST API with SPA frontend",
                "backend": "FastAPI + SQLAlchemy + PostgreSQL",
                "frontend": "React + Vite + TailwindCSS",
                "deployment": "Docker Compose"
            },
            "api_endpoints": [
                {"method": "GET", "path": "/api/health", "description": "Health check"},
                {"method": "POST", "path": "/api/auth/register", "description": "User registration"},
                {"method": "POST", "path": "/api/auth/login", "description": "User login"}
            ],
            "database_schema": entities,
            "authentication": {
                "type": "JWT",
                "token_expiry": "24h",
                "refresh_token": True
            },
            "frontend_structure": {
                "pages": ["Home", "Login", "Dashboard"],
                "components": ["Header", "Footer", "Navigation"],
                "state_management": "React Context/Hooks"
            },
            "styling": {
                "framework": "TailwindCSS",
                "approach": "Utility-first responsive design"
            }
        }
    
    def _generate_default_tasks(self, specs: dict) -> dict:
        """Generate default task breakdown"""
        return {
            "backend": [
                {
                    "name": "setup_project",
                    "description": "Initialize FastAPI project structure",
                    "dependencies": [],
                    "priority": "high",
                    "files": ["main.py", "requirements.txt", "config.py"]
                },
                {
                    "name": "database_models",
                    "description": "Create SQLAlchemy models",
                    "dependencies": ["setup_project"],
                    "priority": "high",
                    "files": ["models.py", "database.py"]
                },
                {
                    "name": "auth_endpoints",
                    "description": "Implement authentication endpoints",
                    "dependencies": ["database_models"],
                    "priority": "high",
                    "files": ["auth.py", "security.py"]
                },
                {
                    "name": "crud_endpoints",
                    "description": "Implement CRUD API endpoints",
                    "dependencies": ["auth_endpoints"],
                    "priority": "high",
                    "files": ["routes.py", "schemas.py"]
                }
            ],
            "frontend": [
                {
                    "name": "setup_project",
                    "description": "Initialize React + Vite project",
                    "dependencies": [],
                    "priority": "high",
                    "files": ["package.json", "vite.config.ts", "index.html"]
                },
                {
                    "name": "auth_pages",
                    "description": "Create authentication pages",
                    "dependencies": ["setup_project"],
                    "priority": "high",
                    "files": ["Login.tsx", "Register.tsx"]
                },
                {
                    "name": "main_layout",
                    "description": "Create main layout and navigation",
                    "dependencies": ["setup_project"],
                    "priority": "high",
                    "files": ["Layout.tsx", "Header.tsx", "Navigation.tsx"]
                },
                {
                    "name": "feature_pages",
                    "description": "Create feature-specific pages and components",
                    "dependencies": ["main_layout", "auth_pages"],
                    "priority": "medium",
                    "files": ["Dashboard.tsx", "components/"]
                }
            ]
        }
