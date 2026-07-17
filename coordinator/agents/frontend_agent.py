"""
Frontend Agent - Generates React frontend code
"""
import json
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import Settings
from .templates.frontend_templates import FrontendTemplates


class FrontendAgent:
    """
    Specialized agent for generating React + Vite frontend code
    """
    
    def __init__(self, llm: ChatGoogleGenerativeAI, settings: Settings):
        self.llm = llm
        self.settings = settings
        self.templates = FrontendTemplates()
    
    async def generate_code(
        self,
        tasks: list[dict],
        user_flows: list[dict],
        specs: dict,
        backend_code: dict
    ) -> dict:
        """
        Generate complete frontend code based on tasks and specifications
        """
        # Extract API endpoints from backend
        api_endpoints = self._extract_api_endpoints(backend_code)
        
        code = {
            "index_html": self._generate_index_html(),
            "main": await self._generate_main_tsx(),
            "app": await self._generate_app_tsx(user_flows),
            "router": await self._generate_router(user_flows),
            "api_client": await self._generate_api_client(api_endpoints),
            "auth_context": await self._generate_auth_context(),
            "pages": await self._generate_pages(user_flows, tasks),
            "components": await self._generate_components(tasks),
            "types": await self._generate_types(specs),
            "utils": self._generate_utils(),
            "styles": self._generate_styles(),
            "config": self._generate_config(),
            "package_json": self._generate_package_json(),
            "vite_config": self._generate_vite_config(),
            "tailwind_config": self._generate_tailwind_config(),
            "tsconfig": self._generate_tsconfig()
        }
        
        return code
    
    async def _generate_main_tsx(self) -> str:
        """Generate main.tsx entry point"""
        return self.templates.get_main_template()
    
    async def _generate_app_tsx(self, user_flows: list[dict]) -> str:
        """Generate App.tsx root component"""
        system_prompt = """You are an expert React developer. Generate App.tsx root component.

Include:
- React Router setup
- Auth context provider
- Global layout structure
- Error boundary
- Loading states

Use React 18+ with TypeScript and modern hooks."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User Flows:\n{json.dumps(user_flows, indent=2)}\n\nGenerate App.tsx")
        ]
        
        response = await self.llm.ainvoke(messages)
        return self._extract_code(response.content) or self.templates.get_app_template()
    
    async def _generate_router(self, user_flows: list[dict]) -> str:
        """Generate React Router configuration"""
        system_prompt = """You are an expert in React Router. Generate router configuration.

Include:
- Route definitions for all pages
- Protected route wrapper
- 404 page
- Lazy loading for code splitting

Use React Router v6+ with TypeScript."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User Flows:\n{json.dumps(user_flows, indent=2)}\n\nGenerate router.tsx")
        ]
        
        response = await self.llm.ainvoke(messages)
        return self._extract_code(response.content) or self.templates.get_router_template()
    
    async def _generate_api_client(self, endpoints: list[dict]) -> str:
        """Generate API client with axios"""
        system_prompt = """You are an expert in API integration. Generate API client module.

Include:
- Axios instance with base configuration
- Request/response interceptors
- Auth token handling
- Error handling
- Type-safe API methods for all endpoints

Use axios with TypeScript generics."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"API Endpoints:\n{json.dumps(endpoints, indent=2)}\n\nGenerate api.ts")
        ]
        
        response = await self.llm.ainvoke(messages)
        return self._extract_code(response.content) or self.templates.get_api_client_template()
    
    async def _generate_auth_context(self) -> str:
        """Generate authentication context"""
        system_prompt = """You are an expert React developer. Generate authentication context.

Include:
- AuthContext with user state
- Login, logout, register functions
- Token management (localStorage)
- Protected route component
- useAuth hook

Use React Context API with TypeScript."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="Generate AuthContext.tsx with full authentication logic")
        ]
        
        response = await self.llm.ainvoke(messages)
        return self._extract_code(response.content) or self.templates.get_auth_context_template()
    
    async def _generate_pages(self, user_flows: list[dict], tasks: list[dict]) -> dict:
        """Generate page components"""
        system_prompt = """You are an expert React developer. Generate page components.

For each page, create a complete component with:
- TypeScript types
- State management with hooks
- API integration
- Form handling with validation
- Loading and error states
- TailwindCSS styling
- Responsive design

Use modern React patterns and best practices."""

        pages = {}
        
        # Generate common pages
        for page_name in ["Home", "Login", "Register", "Dashboard", "NotFound"]:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"User Flows:\n{json.dumps(user_flows, indent=2)}\n\nGenerate {page_name}.tsx page")
            ]
            
            response = await self.llm.ainvoke(messages)
            pages[page_name] = self._extract_code(response.content) or self.templates.get_page_template(page_name)
        
        return pages
    
    async def _generate_components(self, tasks: list[dict]) -> dict:
        """Generate reusable components"""
        system_prompt = """You are an expert React developer. Generate reusable components.

Create production-ready components with:
- TypeScript props interface
- Proper prop validation
- Accessibility features
- TailwindCSS styling
- Responsive design

Follow component best practices."""

        components = {}
        
        # Generate common components
        for component_name in ["Header", "Footer", "Navigation", "Button", "Input", "Card", "Modal", "Loading"]:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Generate {component_name}.tsx component")
            ]
            
            response = await self.llm.ainvoke(messages)
            components[component_name] = self._extract_code(response.content) or self.templates.get_component_template(component_name)
        
        return components
    
    async def _generate_types(self, specs: dict) -> str:
        """Generate TypeScript type definitions"""
        system_prompt = """You are a TypeScript expert. Generate type definitions.

Include:
- API response types
- Entity types matching backend models
- Form input types
- Auth types
- Utility types

Use TypeScript best practices with strict typing."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Specifications:\n{json.dumps(specs, indent=2)}\n\nGenerate types.ts")
        ]
        
        response = await self.llm.ainvoke(messages)
        return self._extract_code(response.content) or self.templates.get_types_template()
    
    def _generate_index_html(self) -> str:
        """Generate index.html"""
        return self.templates.get_index_html_template()
    
    def _generate_utils(self) -> str:
        """Generate utility functions"""
        return self.templates.get_utils_template()
    
    def _generate_styles(self) -> str:
        """Generate global styles"""
        return self.templates.get_styles_template()
    
    def _generate_config(self) -> str:
        """Generate frontend configuration"""
        return self.templates.get_config_template()
    
    def _generate_package_json(self) -> str:
        """Generate package.json"""
        return self.templates.get_package_json_template()
    
    def _generate_vite_config(self) -> str:
        """Generate vite.config.ts"""
        return self.templates.get_vite_config_template()
    
    def _generate_tailwind_config(self) -> str:
        """Generate tailwind.config.js"""
        return self.templates.get_tailwind_config_template()
    
    def _generate_tsconfig(self) -> str:
        """Generate tsconfig.json"""
        return self.templates.get_tsconfig_template()
    
    def _extract_api_endpoints(self, backend_code: dict) -> list[dict]:
        """Extract API endpoints from backend code"""
        # Simple extraction - in production, parse the actual routes
        return [
            {"method": "POST", "path": "/api/auth/register", "description": "Register"},
            {"method": "POST", "path": "/api/auth/login", "description": "Login"},
            {"method": "GET", "path": "/api/auth/me", "description": "Get current user"},
        ]
    
    def _extract_code(self, response: str) -> str:
        """Extract code from markdown code blocks"""
        # Check for TypeScript/TSX blocks
        for lang in ["tsx", "typescript", "ts", "jsx", "javascript", "js"]:
            marker = f"```{lang}"
            if marker in response:
                parts = response.split(marker)
                if len(parts) > 1:
                    code = parts[1].split("```")[0]
                    return code.strip()
        
        # Check for generic code blocks
        if "```" in response:
            parts = response.split("```")
            if len(parts) > 1:
                code = parts[1].split("```")[0]
                lines = code.split("\n")
                # Remove language identifier if present
                if lines[0].strip() in ["tsx", "typescript", "ts", "jsx", "javascript", "js"]:
                    lines = lines[1:]
                return "\n".join(lines).strip()
        
        return response.strip()
