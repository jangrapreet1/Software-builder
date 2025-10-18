"""
Template Library - Pre-built templates for common applications
Quick Win #1 from analysis
"""
import json
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime


class ApplicationTemplate:
    """Application template definition"""
    
    def __init__(
        self,
        template_id: str,
        name: str,
        description: str,
        category: str,
        brief: str,
        entities: List[Dict],
        features: List[str],
        technical_specs: Dict,
        tags: List[str],
        difficulty: str = "medium",
        estimated_time: int = 5
    ):
        self.template_id = template_id
        self.name = name
        self.description = description
        self.category = category
        self.brief = brief
        self.entities = entities
        self.features = features
        self.technical_specs = technical_specs
        self.tags = tags
        self.difficulty = difficulty
        self.estimated_time = estimated_time
        self.created_at = datetime.utcnow().isoformat() + "Z"
        self.usage_count = 0
    
    def to_dict(self) -> Dict:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "brief": self.brief,
            "entities": self.entities,
            "features": self.features,
            "technical_specs": self.technical_specs,
            "tags": self.tags,
            "difficulty": self.difficulty,
            "estimated_time": self.estimated_time,
            "created_at": self.created_at,
            "usage_count": self.usage_count
        }


class TemplateLibrary:
    """Library of pre-built application templates"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = Path(storage_path) if storage_path else Path(".sb_artifacts/templates")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.templates: Dict[str, ApplicationTemplate] = {}
        self._register_default_templates()
        self._load_custom_templates()
    
    def _register_default_templates(self):
        """Register built-in templates"""
        
        # Todo/Task Manager
        self.register(ApplicationTemplate(
            template_id="todo-app",
            name="Todo & Task Manager",
            description="Simple todo list application with task management",
            category="productivity",
            brief="Build a task management application with user authentication, task creation, editing, deletion, categories, and due dates",
            entities=[
                {
                    "name": "Task",
                    "fields": [
                        {"name": "title", "type": "string", "required": True},
                        {"name": "description", "type": "text", "required": False},
                        {"name": "completed", "type": "bool", "default": False},
                        {"name": "due_date", "type": "datetime", "required": False},
                        {"name": "priority", "type": "string", "default": "medium"}
                    ]
                },
                {
                    "name": "Category",
                    "fields": [
                        {"name": "name", "type": "string", "required": True},
                        {"name": "color", "type": "string", "required": False}
                    ]
                }
            ],
            features=[
                "User authentication (JWT)",
                "Create, read, update, delete tasks",
                "Task categories",
                "Task filtering and sorting",
                "Due date reminders",
                "Task completion tracking"
            ],
            technical_specs={
                "backend_framework": "fastapi",
                "frontend_framework": "react-vite",
                "database": "postgresql",
                "authentication": "jwt"
            },
            tags=["productivity", "tasks", "todo", "simple"],
            difficulty="easy",
            estimated_time=3
        ))
        
        # Blog Platform
        self.register(ApplicationTemplate(
            template_id="blog-platform",
            name="Blog Platform",
            description="Content publishing platform with posts, comments, and categories",
            category="content",
            brief="Build a blog platform with posts, comments, categories, tags, user authentication, and markdown support",
            entities=[
                {
                    "name": "Post",
                    "fields": [
                        {"name": "title", "type": "string", "required": True},
                        {"name": "slug", "type": "string", "required": True},
                        {"name": "content", "type": "text", "required": True},
                        {"name": "excerpt", "type": "text", "required": False},
                        {"name": "published", "type": "bool", "default": False},
                        {"name": "published_at", "type": "datetime", "required": False}
                    ]
                },
                {
                    "name": "Comment",
                    "fields": [
                        {"name": "content", "type": "text", "required": True},
                        {"name": "approved", "type": "bool", "default": False}
                    ]
                },
                {
                    "name": "Category",
                    "fields": [
                        {"name": "name", "type": "string", "required": True},
                        {"name": "slug", "type": "string", "required": True}
                    ]
                }
            ],
            features=[
                "User authentication",
                "Create and publish posts",
                "Markdown support",
                "Comments system",
                "Categories and tags",
                "Search functionality",
                "SEO-friendly URLs"
            ],
            technical_specs={
                "backend_framework": "fastapi",
                "frontend_framework": "nextjs",
                "database": "postgresql",
                "authentication": "jwt"
            },
            tags=["blog", "content", "publishing", "cms"],
            difficulty="medium",
            estimated_time=5
        ))
        
        # E-commerce Store
        self.register(ApplicationTemplate(
            template_id="ecommerce-store",
            name="E-commerce Store",
            description="Online store with products, cart, and order management",
            category="ecommerce",
            brief="Build an e-commerce platform with product catalog, shopping cart, order management, and payment processing",
            entities=[
                {
                    "name": "Product",
                    "fields": [
                        {"name": "name", "type": "string", "required": True},
                        {"name": "description", "type": "text", "required": True},
                        {"name": "price", "type": "float", "required": True},
                        {"name": "stock", "type": "int", "default": 0},
                        {"name": "image_url", "type": "url", "required": False},
                        {"name": "active", "type": "bool", "default": True}
                    ]
                },
                {
                    "name": "Order",
                    "fields": [
                        {"name": "total_amount", "type": "float", "required": True},
                        {"name": "status", "type": "string", "default": "pending"},
                        {"name": "shipping_address", "type": "text", "required": True}
                    ]
                },
                {
                    "name": "OrderItem",
                    "fields": [
                        {"name": "quantity", "type": "int", "required": True},
                        {"name": "price", "type": "float", "required": True}
                    ]
                }
            ],
            features=[
                "Product catalog with search",
                "Shopping cart",
                "Order management",
                "User authentication",
                "Product reviews",
                "Inventory management",
                "Order tracking"
            ],
            technical_specs={
                "backend_framework": "fastapi",
                "frontend_framework": "react-vite",
                "database": "postgresql",
                "authentication": "jwt"
            },
            tags=["ecommerce", "store", "shopping", "products"],
            difficulty="hard",
            estimated_time=8
        ))
        
        # Social Media App
        self.register(ApplicationTemplate(
            template_id="social-media",
            name="Social Media Platform",
            description="Social networking app with posts, likes, and follows",
            category="social",
            brief="Build a social media platform with user profiles, posts, likes, comments, following system, and feed",
            entities=[
                {
                    "name": "Post",
                    "fields": [
                        {"name": "content", "type": "text", "required": True},
                        {"name": "image_url", "type": "url", "required": False},
                        {"name": "likes_count", "type": "int", "default": 0}
                    ]
                },
                {
                    "name": "Comment",
                    "fields": [
                        {"name": "content", "type": "text", "required": True}
                    ]
                },
                {
                    "name": "Follow",
                    "fields": [
                        {"name": "follower_id", "type": "int", "required": True},
                        {"name": "following_id", "type": "int", "required": True}
                    ]
                }
            ],
            features=[
                "User profiles",
                "Create and share posts",
                "Like and comment on posts",
                "Follow/unfollow users",
                "News feed algorithm",
                "Notifications",
                "User search"
            ],
            technical_specs={
                "backend_framework": "fastapi",
                "frontend_framework": "react-vite",
                "database": "postgresql",
                "authentication": "jwt"
            },
            tags=["social", "networking", "posts", "likes"],
            difficulty="hard",
            estimated_time=10
        ))
        
        # Project Management Tool
        self.register(ApplicationTemplate(
            template_id="project-management",
            name="Project Management Tool",
            description="Team collaboration tool with projects, tasks, and milestones",
            category="productivity",
            brief="Build a project management system with teams, projects, tasks, milestones, file attachments, and collaboration features",
            entities=[
                {
                    "name": "Project",
                    "fields": [
                        {"name": "name", "type": "string", "required": True},
                        {"name": "description", "type": "text", "required": False},
                        {"name": "start_date", "type": "date", "required": False},
                        {"name": "end_date", "type": "date", "required": False},
                        {"name": "status", "type": "string", "default": "active"}
                    ]
                },
                {
                    "name": "Task",
                    "fields": [
                        {"name": "title", "type": "string", "required": True},
                        {"name": "description", "type": "text", "required": False},
                        {"name": "status", "type": "string", "default": "todo"},
                        {"name": "priority", "type": "string", "default": "medium"},
                        {"name": "due_date", "type": "datetime", "required": False}
                    ]
                },
                {
                    "name": "Team",
                    "fields": [
                        {"name": "name", "type": "string", "required": True},
                        {"name": "description", "type": "text", "required": False}
                    ]
                }
            ],
            features=[
                "Multi-project management",
                "Task assignment and tracking",
                "Team collaboration",
                "Milestones and deadlines",
                "File attachments",
                "Activity timeline",
                "Reports and analytics"
            ],
            technical_specs={
                "backend_framework": "fastapi",
                "frontend_framework": "react-vite",
                "database": "postgresql",
                "authentication": "jwt"
            },
            tags=["project-management", "collaboration", "teams", "tasks"],
            difficulty="hard",
            estimated_time=10
        ))
        
        # Dashboard/Analytics App
        self.register(ApplicationTemplate(
            template_id="analytics-dashboard",
            name="Analytics Dashboard",
            description="Data visualization dashboard with charts and metrics",
            category="analytics",
            brief="Build an analytics dashboard with real-time data visualization, charts, metrics, and reporting capabilities",
            entities=[
                {
                    "name": "Metric",
                    "fields": [
                        {"name": "name", "type": "string", "required": True},
                        {"name": "value", "type": "float", "required": True},
                        {"name": "unit", "type": "string", "required": False},
                        {"name": "timestamp", "type": "datetime", "required": True}
                    ]
                },
                {
                    "name": "Dashboard",
                    "fields": [
                        {"name": "name", "type": "string", "required": True},
                        {"name": "description", "type": "text", "required": False}
                    ]
                },
                {
                    "name": "Widget",
                    "fields": [
                        {"name": "title", "type": "string", "required": True},
                        {"name": "type", "type": "string", "required": True},
                        {"name": "config", "type": "dict", "required": True}
                    ]
                }
            ],
            features=[
                "Real-time data visualization",
                "Multiple chart types",
                "Customizable dashboards",
                "Metric tracking",
                "Export reports",
                "Alerts and notifications",
                "Data filtering"
            ],
            technical_specs={
                "backend_framework": "fastapi",
                "frontend_framework": "react-vite",
                "database": "postgresql",
                "authentication": "jwt"
            },
            tags=["dashboard", "analytics", "visualization", "metrics"],
            difficulty="medium",
            estimated_time=6
        ))
    
    def register(self, template: ApplicationTemplate):
        """Register a template"""
        self.templates[template.template_id] = template
        self._save_template(template)
    
    def _save_template(self, template: ApplicationTemplate):
        """Save template to disk"""
        file_path = self.storage_path / f"{template.template_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(template.to_dict(), f, indent=2)
    
    def _load_custom_templates(self):
        """Load custom templates from disk"""
        if not self.storage_path.exists():
            return
        
        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Only load if not a default template
                    if data["template_id"] not in self.templates:
                        template = ApplicationTemplate(**data)
                        self.templates[template.template_id] = template
            except Exception:
                pass  # Skip invalid templates
    
    def get(self, template_id: str) -> Optional[ApplicationTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)
    
    def get_all(self) -> List[ApplicationTemplate]:
        """Get all templates"""
        return list(self.templates.values())
    
    def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        difficulty: Optional[str] = None
    ) -> List[ApplicationTemplate]:
        """Search templates"""
        results = list(self.templates.values())
        
        if query:
            query_lower = query.lower()
            results = [
                t for t in results
                if query_lower in t.name.lower() or query_lower in t.description.lower()
            ]
        
        if category:
            results = [t for t in results if t.category == category]
        
        if tags:
            results = [
                t for t in results
                if any(tag in t.tags for tag in tags)
            ]
        
        if difficulty:
            results = [t for t in results if t.difficulty == difficulty]
        
        return results
    
    def get_by_category(self, category: str) -> List[ApplicationTemplate]:
        """Get templates by category"""
        return [t for t in self.templates.values() if t.category == category]
    
    def use_template(self, template_id: str) -> Optional[Dict]:
        """Use a template (returns build specification)"""
        template = self.get(template_id)
        if not template:
            return None
        
        template.usage_count += 1
        self._save_template(template)
        
        return {
            "description": template.brief,
            "name": template.name.lower().replace(" ", "-"),
            "requirements": template.features,
            "entities": template.entities,
            "technical_specs": template.technical_specs,
            "template_id": template.template_id
        }
    
    def save_build_as_template(
        self,
        name: str,
        description: str,
        category: str,
        build_data: Dict,
        tags: Optional[List[str]] = None
    ) -> ApplicationTemplate:
        """Save a successful build as a template"""
        template_id = name.lower().replace(" ", "-") + "-custom"
        
        template = ApplicationTemplate(
            template_id=template_id,
            name=name,
            description=description,
            category=category,
            brief=build_data.get("brief", ""),
            entities=build_data.get("entities", []),
            features=build_data.get("features", []),
            technical_specs=build_data.get("technical_specs", {}),
            tags=tags or [],
            difficulty="medium"
        )
        
        self.register(template)
        return template
    
    def get_statistics(self) -> Dict:
        """Get library statistics"""
        total = len(self.templates)
        by_category = {}
        by_difficulty = {}
        
        for template in self.templates.values():
            by_category[template.category] = by_category.get(template.category, 0) + 1
            by_difficulty[template.difficulty] = by_difficulty.get(template.difficulty, 0) + 1
        
        return {
            "total_templates": total,
            "by_category": by_category,
            "by_difficulty": by_difficulty,
            "most_used": sorted(
                self.templates.values(),
                key=lambda t: t.usage_count,
                reverse=True
            )[:5]
        }


# Global instance
_template_library = None

def get_template_library() -> TemplateLibrary:
    """Get or create global template library"""
    global _template_library
    if _template_library is None:
        _template_library = TemplateLibrary()
    return _template_library
