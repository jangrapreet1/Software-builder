"""
Frontend Agent - Generates React frontend code
"""
import json
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

from config.settings import Settings
from .templates.frontend_templates import FrontendTemplates
from services.retry_utils import call_llm_with_retry
from services.framework_registry import get_framework_manifest


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
        if (specs.get("preferred_frontend") or "").lower().strip() == "nextjs":
            return await self._generate_nextjs(tasks, user_flows, specs, backend_code)

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
        
        # Enforce React/Vite manifest on package.json
        manifest = get_framework_manifest("react-vite") or {}
        pkg_raw = code.get("package_json") or "{}"
        try:
            pkg = json.loads(pkg_raw)
            scripts = pkg.setdefault("scripts", {})
            for k, v in (manifest.get("required_scripts") or {}).items():
                scripts.setdefault(k, v)
            deps = pkg.setdefault("dependencies", {})
            for d in (manifest.get("required_dependencies") or []):
                if d not in deps:
                    deps[d] = "^18.2.0" if d.startswith("react") else "^1.0.0"
            dev = pkg.setdefault("devDependencies", {})
            for d in (manifest.get("required_dev_dependencies") or []):
                if d not in dev:
                    dev[d] = "^5.0.0" if d == "vite" else "^1.0.0"
            code["package_json"] = json.dumps(pkg, indent=2)
        except Exception:
            # Leave as-is if not valid JSON
            pass
        
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
        
        response = await call_llm_with_retry(self.llm, messages)
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
        
        response = await call_llm_with_retry(self.llm, messages)
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
        
        response = await call_llm_with_retry(self.llm, messages)
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
        
        response = await call_llm_with_retry(self.llm, messages)
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
            
            response = await call_llm_with_retry(self.llm, messages)
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
            
            response = await call_llm_with_retry(self.llm, messages)
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
        
        response = await call_llm_with_retry(self.llm, messages)
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

    async def _generate_nextjs(
        self,
        tasks: list[dict],
        user_flows: list[dict],
        specs: dict,
        backend_code: dict
    ) -> dict:
        """Generate a complete Next.js frontend application"""
        system_prompt = """You are an expert Next.js developer. Generate a complete, production-ready React frontend application using Next.js App Router.
You must output a JSON object mapping relative file paths to their complete file contents.
Do not wrap the JSON in markdown code blocks or add any other text outside the JSON. The JSON keys must be relative file paths, and values must be file contents.

Generate the following files:
1. package.json (with next, react, react-dom, tailwindcss, postcss, autoprefixer, lucide-react dependencies)
2. next.config.js (Next.js configurations, redirects or rewrites if any, CORS headers)
3. tailwind.config.js and postcss.config.js (standard Tailwind configuration)
4. tsconfig.json (standard TS config for Next.js)
5. src/app/layout.tsx (App router root layout, styling imports, provider mounts)
6. src/app/page.tsx (App router homepage, index page displaying hero sections or project lists)
7. src/app/login/page.tsx (standard login page with sign-in flow)
8. src/app/dashboard/page.tsx (dashboard panel page showing CRUD interface controls)
9. Dockerfile (Node 18 alpine exposing port 3000 and starting 'npm run dev' or running 'npm run build' and starting Node)
10. .dockerignore (ignoring node_modules, etc.)
"""
        messages = [
            SystemMessage(content=system_prompt + f"\nUser Flows:\n{json.dumps(user_flows, indent=2)}\n\nTasks:\n{json.dumps(tasks, indent=2)}"),
            HumanMessage(content="Generate the complete file map JSON for the Next.js application.")
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
            return {"files": self._get_nextjs_fallback_files()}

    def _get_nextjs_fallback_files(self) -> dict:
        """Provide fallback files for Next.js frontend"""
        pkg_json = """{
  "name": "nextjs-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  }
}"""
        layout_tsx = """import './globals.css';
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div class="min-h-screen bg-gray-50">{children}</div>
      </body>
    </html>
  );
}"""
        page_tsx = """export default function Home() {
  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>Auto-Generated App (Next.js)</h1>
      <p>Welcome to your new Next.js application.</p>
    </div>
  );
}"""
        globals_css = """@tailwind base;
@tailwind components;
@tailwind utilities;"""
        dockerfile = """FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]
"""
        return {
            "package.json": pkg_json,
            "src/app/layout.tsx": layout_tsx,
            "src/app/page.tsx": page_tsx,
            "src/app/globals.css": globals_css,
            "Dockerfile": dockerfile
        }
