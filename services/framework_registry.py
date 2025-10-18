"""
Framework Registry - Multi-framework support system
Manages different frontend and backend framework templates
"""
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass


class FrameworkType(Enum):
    """Framework types"""
    FRONTEND = "frontend"
    BACKEND = "backend"
    FULLSTACK = "fullstack"


class FrameworkCategory(Enum):
    """Framework categories"""
    SPA = "spa"  # Single Page Application
    SSR = "ssr"  # Server Side Rendering
    STATIC = "static"  # Static Site Generator
    API = "api"  # API Framework
    FULLSTACK_FW = "fullstack"  # Full-stack framework


@dataclass
class Framework:
    """Framework definition"""
    id: str
    name: str
    type: FrameworkType
    category: FrameworkCategory
    language: str
    description: str
    version: str
    dependencies: List[str]
    dev_dependencies: List[str]
    build_command: str
    start_command: str
    test_command: str
    features: List[str]
    suitable_for: List[str]  # Project types
    learning_curve: str  # easy, medium, hard
    popularity: int  # 1-10
    performance: int  # 1-10
    documentation_url: str
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "category": self.category.value,
            "language": self.language,
            "description": self.description,
            "version": self.version,
            "dependencies": self.dependencies,
            "dev_dependencies": self.dev_dependencies,
            "build_command": self.build_command,
            "start_command": self.start_command,
            "test_command": self.test_command,
            "features": self.features,
            "suitable_for": self.suitable_for,
            "learning_curve": self.learning_curve,
            "popularity": self.popularity,
            "performance": self.performance,
            "documentation_url": self.documentation_url
        }


class FrameworkRegistry:
    """Registry of supported frameworks"""
    
    def __init__(self):
        self.frameworks: Dict[str, Framework] = {}
        self._register_frameworks()
    
    def _register_frameworks(self):
        """Register all supported frameworks"""
        
        # FRONTEND FRAMEWORKS
        
        # React + Vite
        self.register(Framework(
            id="react-vite",
            name="React + Vite",
            type=FrameworkType.FRONTEND,
            category=FrameworkCategory.SPA,
            language="TypeScript",
            description="Fast and modern React setup with Vite bundler",
            version="18.2.0",
            dependencies=["react", "react-dom", "react-router-dom", "axios"],
            dev_dependencies=["@vitejs/plugin-react", "vite", "typescript", "@types/react"],
            build_command="npm run build",
            start_command="npm run dev",
            test_command="npm test",
            features=["SPA", "Hot Module Replacement", "TypeScript", "Fast builds"],
            suitable_for=["dashboard", "admin-panel", "web-app", "prototype"],
            learning_curve="medium",
            popularity=10,
            performance=9,
            documentation_url="https://react.dev"
        ))
        
        # Next.js
        self.register(Framework(
            id="nextjs",
            name="Next.js",
            type=FrameworkType.FRONTEND,
            category=FrameworkCategory.SSR,
            language="TypeScript",
            description="React framework with SSR, SSG, and API routes",
            version="14.0.0",
            dependencies=["next", "react", "react-dom"],
            dev_dependencies=["@types/react", "@types/node", "typescript"],
            build_command="npm run build",
            start_command="npm run dev",
            test_command="npm test",
            features=["SSR", "SSG", "API Routes", "File-based routing", "SEO-friendly"],
            suitable_for=["marketing-site", "blog", "e-commerce", "content-site"],
            learning_curve="medium",
            popularity=9,
            performance=10,
            documentation_url="https://nextjs.org"
        ))
        
        # Vue 3
        self.register(Framework(
            id="vue3-vite",
            name="Vue 3 + Vite",
            type=FrameworkType.FRONTEND,
            category=FrameworkCategory.SPA,
            language="TypeScript",
            description="Progressive JavaScript framework with composition API",
            version="3.3.0",
            dependencies=["vue", "vue-router", "pinia", "axios"],
            dev_dependencies=["@vitejs/plugin-vue", "vite", "typescript"],
            build_command="npm run build",
            start_command="npm run dev",
            test_command="npm test",
            features=["Composition API", "Reactive", "Single File Components", "TypeScript"],
            suitable_for=["dashboard", "web-app", "admin-panel", "interactive-ui"],
            learning_curve="easy",
            popularity=8,
            performance=9,
            documentation_url="https://vuejs.org"
        ))
        
        # Angular
        self.register(Framework(
            id="angular",
            name="Angular",
            type=FrameworkType.FRONTEND,
            category=FrameworkCategory.SPA,
            language="TypeScript",
            description="Complete framework with dependency injection and RxJS",
            version="17.0.0",
            dependencies=["@angular/core", "@angular/common", "@angular/router", "rxjs"],
            dev_dependencies=["@angular/cli", "@angular-devkit/build-angular", "typescript"],
            build_command="ng build",
            start_command="ng serve",
            test_command="ng test",
            features=["Dependency Injection", "RxJS", "TypeScript-first", "CLI"],
            suitable_for=["enterprise-app", "large-scale", "complex-app"],
            learning_curve="hard",
            popularity=7,
            performance=8,
            documentation_url="https://angular.io"
        ))
        
        # Svelte
        self.register(Framework(
            id="svelte-kit",
            name="SvelteKit",
            type=FrameworkType.FRONTEND,
            category=FrameworkCategory.SSR,
            language="TypeScript",
            description="Cybernetically enhanced web apps with no virtual DOM",
            version="4.0.0",
            dependencies=["svelte", "@sveltejs/kit"],
            dev_dependencies=["@sveltejs/adapter-auto", "vite", "typescript"],
            build_command="npm run build",
            start_command="npm run dev",
            test_command="npm test",
            features=["No Virtual DOM", "Compile-time", "SSR", "File-based routing"],
            suitable_for=["web-app", "marketing-site", "blog", "interactive-ui"],
            learning_curve="easy",
            popularity=7,
            performance=10,
            documentation_url="https://kit.svelte.dev"
        ))
        
        # Solid.js
        self.register(Framework(
            id="solidjs",
            name="Solid.js",
            type=FrameworkType.FRONTEND,
            category=FrameworkCategory.SPA,
            language="TypeScript",
            description="Fine-grained reactive JavaScript framework",
            version="1.8.0",
            dependencies=["solid-js", "solid-router"],
            dev_dependencies=["vite", "vite-plugin-solid", "typescript"],
            build_command="npm run build",
            start_command="npm run dev",
            test_command="npm test",
            features=["Fine-grained reactivity", "No Virtual DOM", "Fast", "Small bundle"],
            suitable_for=["performance-critical", "web-app", "interactive-ui"],
            learning_curve="medium",
            popularity=6,
            performance=10,
            documentation_url="https://www.solidjs.com"
        ))
        
        # BACKEND FRAMEWORKS
        
        # FastAPI
        self.register(Framework(
            id="fastapi",
            name="FastAPI",
            type=FrameworkType.BACKEND,
            category=FrameworkCategory.API,
            language="Python",
            description="Modern, fast web framework for building APIs with Python 3.7+",
            version="0.109.0",
            dependencies=["fastapi", "uvicorn", "sqlalchemy", "pydantic", "python-jose"],
            dev_dependencies=["pytest", "black", "isort"],
            build_command="",
            start_command="uvicorn main:app --reload",
            test_command="pytest",
            features=["Async", "Auto-docs", "Type hints", "Fast", "OpenAPI"],
            suitable_for=["api", "microservice", "backend", "data-science"],
            learning_curve="easy",
            popularity=9,
            performance=10,
            documentation_url="https://fastapi.tiangolo.com"
        ))
        
        # Django + DRF
        self.register(Framework(
            id="django",
            name="Django + Django REST Framework",
            type=FrameworkType.BACKEND,
            category=FrameworkCategory.FULLSTACK_FW,
            language="Python",
            description="High-level Python web framework with batteries included",
            version="5.0.0",
            dependencies=["django", "djangorestframework", "django-cors-headers", "psycopg2-binary"],
            dev_dependencies=["pytest-django", "black"],
            build_command="python manage.py collectstatic --noinput",
            start_command="python manage.py runserver",
            test_command="pytest",
            features=["ORM", "Admin panel", "Authentication", "Full-stack", "Mature"],
            suitable_for=["full-stack-app", "content-site", "admin-heavy", "enterprise"],
            learning_curve="medium",
            popularity=9,
            performance=7,
            documentation_url="https://www.djangoproject.com"
        ))
        
        # Flask
        self.register(Framework(
            id="flask",
            name="Flask",
            type=FrameworkType.BACKEND,
            category=FrameworkCategory.API,
            language="Python",
            description="Lightweight WSGI web application framework",
            version="3.0.0",
            dependencies=["flask", "flask-sqlalchemy", "flask-cors", "flask-jwt-extended"],
            dev_dependencies=["pytest", "black"],
            build_command="",
            start_command="flask run",
            test_command="pytest",
            features=["Lightweight", "Flexible", "Extensions", "Simple"],
            suitable_for=["api", "microservice", "simple-backend", "prototype"],
            learning_curve="easy",
            popularity=8,
            performance=8,
            documentation_url="https://flask.palletsprojects.com"
        ))
        
        # Express.js
        self.register(Framework(
            id="express",
            name="Express.js",
            type=FrameworkType.BACKEND,
            category=FrameworkCategory.API,
            language="TypeScript",
            description="Fast, unopinionated, minimalist web framework for Node.js",
            version="4.18.0",
            dependencies=["express", "cors", "dotenv", "jsonwebtoken"],
            dev_dependencies=["typescript", "@types/express", "@types/node", "ts-node", "nodemon"],
            build_command="tsc",
            start_command="npm run dev",
            test_command="npm test",
            features=["Minimal", "Flexible", "Middleware", "Mature"],
            suitable_for=["api", "microservice", "backend", "real-time"],
            learning_curve="easy",
            popularity=9,
            performance=8,
            documentation_url="https://expressjs.com"
        ))
        
        # NestJS
        self.register(Framework(
            id="nestjs",
            name="NestJS",
            type=FrameworkType.BACKEND,
            category=FrameworkCategory.API,
            language="TypeScript",
            description="Progressive Node.js framework for building efficient and scalable server-side applications",
            version="10.0.0",
            dependencies=["@nestjs/core", "@nestjs/common", "@nestjs/platform-express", "reflect-metadata"],
            dev_dependencies=["@nestjs/cli", "@nestjs/testing", "typescript"],
            build_command="npm run build",
            start_command="npm run start:dev",
            test_command="npm test",
            features=["TypeScript", "Dependency Injection", "Modular", "Decorators", "Enterprise"],
            suitable_for=["enterprise-api", "microservices", "large-scale", "complex-backend"],
            learning_curve="hard",
            popularity=8,
            performance=9,
            documentation_url="https://nestjs.com"
        ))
        
        # Go + Gin
        self.register(Framework(
            id="go-gin",
            name="Go + Gin",
            type=FrameworkType.BACKEND,
            category=FrameworkCategory.API,
            language="Go",
            description="High-performance HTTP web framework written in Go",
            version="1.9.0",
            dependencies=["github.com/gin-gonic/gin", "gorm.io/gorm", "gorm.io/driver/postgres"],
            dev_dependencies=[],
            build_command="go build",
            start_command="go run main.go",
            test_command="go test",
            features=["Fast", "Low memory", "Middleware", "JSON validation"],
            suitable_for=["high-performance-api", "microservice", "backend", "concurrent"],
            learning_curve="medium",
            popularity=7,
            performance=10,
            documentation_url="https://gin-gonic.com"
        ))
        
        # Rust + Actix
        self.register(Framework(
            id="rust-actix",
            name="Rust + Actix Web",
            type=FrameworkType.BACKEND,
            category=FrameworkCategory.API,
            language="Rust",
            description="Powerful, pragmatic, and extremely fast web framework for Rust",
            version="4.4.0",
            dependencies=["actix-web", "tokio", "serde", "sqlx"],
            dev_dependencies=[],
            build_command="cargo build --release",
            start_command="cargo run",
            test_command="cargo test",
            features=["Extremely fast", "Type safe", "Async", "Memory safe"],
            suitable_for=["high-performance-api", "systems-programming", "performance-critical"],
            learning_curve="hard",
            popularity=6,
            performance=10,
            documentation_url="https://actix.rs"
        ))
    
    def register(self, framework: Framework):
        """Register a framework"""
        self.frameworks[framework.id] = framework
    
    def get(self, framework_id: str) -> Optional[Framework]:
        """Get framework by ID"""
        return self.frameworks.get(framework_id)
    
    def get_all(self, framework_type: Optional[FrameworkType] = None) -> List[Framework]:
        """Get all frameworks, optionally filtered by type"""
        if framework_type:
            return [f for f in self.frameworks.values() if f.type == framework_type]
        return list(self.frameworks.values())
    
    def get_by_language(self, language: str) -> List[Framework]:
        """Get frameworks by language"""
        return [f for f in self.frameworks.values() if f.language.lower() == language.lower()]
    
    def get_suitable_for(self, project_type: str) -> List[Framework]:
        """Get frameworks suitable for project type"""
        return [
            f for f in self.frameworks.values()
            if project_type.lower() in [s.lower() for s in f.suitable_for]
        ]
    
    def recommend_framework(
        self,
        project_type: str,
        framework_type: FrameworkType,
        preferences: Optional[Dict] = None
    ) -> Optional[Framework]:
        """Recommend best framework based on criteria"""
        preferences = preferences or {}
        
        # Get suitable frameworks
        candidates = self.get_suitable_for(project_type)
        candidates = [f for f in candidates if f.type == framework_type]
        
        if not candidates:
            # Fallback to type-based selection
            candidates = self.get_all(framework_type)
        
        if not candidates:
            return None
        
        # Score candidates
        def score_framework(fw: Framework) -> float:
            score = 0.0
            
            # Popularity weight
            score += fw.popularity * 0.3
            
            # Performance weight
            score += fw.performance * 0.3
            
            # Learning curve preference
            if preferences.get("easy_learning"):
                score += (10 if fw.learning_curve == "easy" else 5 if fw.learning_curve == "medium" else 0) * 0.2
            
            # Language preference
            if preferences.get("language") and fw.language.lower() == preferences["language"].lower():
                score += 10 * 0.2
            
            return score
        
        # Sort by score
        scored = [(fw, score_framework(fw)) for fw in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return scored[0][0] if scored else None
    
    def get_statistics(self) -> Dict:
        """Get registry statistics"""
        total = len(self.frameworks)
        by_type = {}
        by_language = {}
        
        for fw in self.frameworks.values():
            by_type[fw.type.value] = by_type.get(fw.type.value, 0) + 1
            by_language[fw.language] = by_language.get(fw.language, 0) + 1
        
        return {
            "total_frameworks": total,
            "by_type": by_type,
            "by_language": by_language,
            "frontend_count": by_type.get(FrameworkType.FRONTEND.value, 0),
            "backend_count": by_type.get(FrameworkType.BACKEND.value, 0)
        }


# Global instance
_framework_registry = None

def get_framework_registry() -> FrameworkRegistry:
    """Get or create global framework registry"""
    global _framework_registry
    if _framework_registry is None:
        _framework_registry = FrameworkRegistry()
    return _framework_registry
