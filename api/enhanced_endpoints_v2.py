"""
Enhanced API Endpoints V2 - All new features integrated
Comprehensive API for all Phase 3 enhancements
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional
from pathlib import Path

# Import all new services
from services.agent_memory_system import get_memory_system
from services.learning_engine import get_learning_engine
from services.framework_registry import get_framework_registry
from services.template_library import get_template_library
from services.persistent_build_storage import get_build_storage
from services.error_message_enhancer import get_error_enhancer
from services.agent_performance_dashboard import get_performance_tracker
from services.enhanced_conversation_context import get_conversation_context

# Import agents
from agents.code_review_agent import CodeReviewAgent
from agents.comprehensive_test_generator import ComprehensiveTestGenerator
from agents.quality_assurance_agent import QualityAssuranceAgent
from agents.deployment_agent import DeploymentAgent
from agents.cicd_generator import CICDGenerator
from agents.base_agent import ExecutionContext

router = APIRouter(prefix="/api/v2", tags=["Enhanced Features V2"])


# Module-level references for optional integrations
_enhanced_workflow = None
_settings = None


def initialize_enhanced_services(workflow, settings):
    """Store references to enhanced workflow/settings and warm key services."""
    global _enhanced_workflow, _settings
    _enhanced_workflow = workflow
    _settings = settings

    # Warm commonly used singletons so first request is snappy
    get_memory_system()
    get_learning_engine()
    get_framework_registry()
    get_template_library()
    get_build_storage()
    get_error_enhancer()
    get_performance_tracker()
    get_conversation_context()


# ========== Request/Response Models ==========

class FrameworkRecommendationRequest(BaseModel):
    project_type: str
    framework_type: str  # "frontend" or "backend"
    preferences: Optional[Dict] = None


class TemplateSearchRequest(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    difficulty: Optional[str] = None


class CodeReviewRequest(BaseModel):
    code_path: str
    language: Optional[str] = "auto"


class TestGenerationRequest(BaseModel):
    project_path: str
    entities: List[Dict]
    backend_framework: Optional[str] = "fastapi"
    frontend_framework: Optional[str] = "react-vite"


class QARequest(BaseModel):
    project_path: str


class DeploymentRequest(BaseModel):
    project_path: str
    platform: str
    project_name: str


class CICDRequest(BaseModel):
    ci_platform: str
    project_type: Optional[str] = "fullstack"
    deploy_platform: Optional[str] = ""


class ErrorEnhanceRequest(BaseModel):
    error_message: str


class BuildRecommendationRequest(BaseModel):
    brief: str
    requirements: List[str]


# ========== Framework & Template Endpoints ==========

@router.get("/frameworks")
async def list_frameworks(framework_type: Optional[str] = None):
    """List all supported frameworks"""
    registry = get_framework_registry()
    
    if framework_type:
        from services.framework_registry import FrameworkType
        fw_type = FrameworkType(framework_type)
        frameworks = registry.get_all(fw_type)
    else:
        frameworks = registry.get_all()
    
    return {
        "frameworks": [f.to_dict() for f in frameworks],
        "total": len(frameworks),
        "statistics": registry.get_statistics()
    }


@router.post("/frameworks/recommend")
async def recommend_framework(request: FrameworkRecommendationRequest):
    """Recommend best framework for project"""
    registry = get_framework_registry()
    from services.framework_registry import FrameworkType
    
    fw_type = FrameworkType(request.framework_type)
    framework = registry.recommend_framework(
        request.project_type,
        fw_type,
        request.preferences
    )
    
    if not framework:
        raise HTTPException(status_code=404, detail="No suitable framework found")
    
    return {
        "recommended": framework.to_dict(),
        "reason": "Best match based on popularity, performance, and preferences"
    }


@router.get("/templates")
async def list_templates(
    category: Optional[str] = None,
    difficulty: Optional[str] = None
):
    """List all application templates"""
    library = get_template_library()
    
    if category or difficulty:
        templates = library.search(category=category, difficulty=difficulty)
    else:
        templates = library.get_all()
    
    return {
        "templates": [t.to_dict() for t in templates],
        "total": len(templates),
        "statistics": library.get_statistics()
    }


@router.post("/templates/search")
async def search_templates(request: TemplateSearchRequest):
    """Search templates"""
    library = get_template_library()
    
    templates = library.search(
        query=request.query,
        category=request.category,
        tags=request.tags,
        difficulty=request.difficulty
    )
    
    return {
        "templates": [t.to_dict() for t in templates],
        "total": len(templates)
    }


@router.post("/templates/{template_id}/use")
async def use_template(template_id: str):
    """Use a template to create build spec"""
    library = get_template_library()
    spec = library.use_template(template_id)
    
    if not spec:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "success": True,
        "build_spec": spec,
        "message": "Template ready to use"
    }


# ========== Code Quality Endpoints ==========

@router.post("/code-review")
async def review_code(request: CodeReviewRequest):
    """Perform code review"""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from config.settings import Settings
    
    settings = Settings()
    llm = ChatGoogleGenerativeAI(model=settings.gemini_model, google_api_key=settings.google_api_key)
    
    agent = CodeReviewAgent(llm, settings)
    context = ExecutionContext(
        build_id="code-review",
        request_data={"code_path": request.code_path, "language": request.language}
    )
    
    result = await agent.execute_safe(context)
    
    return {
        "success": result.is_success(),
        "review": result.output,
        "metadata": result.metadata
    }


@router.post("/generate-tests")
async def generate_tests(request: TestGenerationRequest):
    """Generate comprehensive test suite"""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from config.settings import Settings
    
    settings = Settings()
    llm = ChatGoogleGenerativeAI(model=settings.gemini_model, google_api_key=settings.google_api_key)
    
    agent = ComprehensiveTestGenerator(llm, settings)
    context = ExecutionContext(
        build_id="test-gen",
        request_data={
            "project_path": request.project_path,
            "entities": request.entities,
            "backend_framework": request.backend_framework,
            "frontend_framework": request.frontend_framework
        }
    )
    
    result = await agent.execute_safe(context)
    
    return {
        "success": result.is_success(),
        "tests": result.output,
        "metadata": result.metadata
    }


@router.post("/quality-assurance")
async def quality_assurance(request: QARequest):
    """Run comprehensive QA checks"""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from config.settings import Settings
    
    settings = Settings()
    llm = ChatGoogleGenerativeAI(model=settings.gemini_model, google_api_key=settings.google_api_key)
    
    agent = QualityAssuranceAgent(llm, settings)
    context = ExecutionContext(
        build_id="qa",
        request_data={"project_path": request.project_path}
    )
    
    result = await agent.execute_safe(context)
    
    return {
        "success": result.is_success(),
        "qa_results": result.output,
        "warnings": result.warnings
    }


# ========== Deployment Endpoints ==========

@router.post("/deployment/configure")
async def configure_deployment(request: DeploymentRequest):
    """Generate deployment configuration"""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from config.settings import Settings
    
    settings = Settings()
    llm = ChatGoogleGenerativeAI(model=settings.gemini_model, google_api_key=settings.google_api_key)
    
    agent = DeploymentAgent(llm, settings)
    context = ExecutionContext(
        build_id="deploy",
        request_data={
            "project_path": request.project_path,
            "platform": request.platform,
            "project_name": request.project_name
        }
    )
    
    result = await agent.execute_safe(context)
    
    return {
        "success": result.is_success(),
        "deployment": result.output
    }


@router.post("/cicd/generate")
async def generate_cicd(request: CICDRequest):
    """Generate CI/CD pipeline configuration"""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from config.settings import Settings
    
    settings = Settings()
    llm = ChatGoogleGenerativeAI(model=settings.gemini_model, google_api_key=settings.google_api_key)
    
    agent = CICDGenerator(llm, settings)
    context = ExecutionContext(
        build_id="cicd",
        request_data={
            "ci_platform": request.ci_platform,
            "project_type": request.project_type,
            "deploy_platform": request.deploy_platform
        }
    )
    
    result = await agent.execute_safe(context)
    
    return {
        "success": result.is_success(),
        "pipeline": result.output
    }


# ========== Learning & Memory Endpoints ==========

@router.get("/learning/statistics")
async def get_learning_stats():
    """Get learning engine statistics"""
    engine = get_learning_engine()
    return engine.get_statistics()


@router.post("/learning/recommendations")
async def get_build_recommendations(request: BuildRecommendationRequest):
    """Get AI recommendations for build"""
    engine = get_learning_engine()
    recommendations = engine.get_build_recommendations(
        request.brief,
        request.requirements
    )
    
    return {
        "recommendations": recommendations,
        "confidence": recommendations.get("confidence", 0)
    }


@router.get("/memory/statistics")
async def get_memory_stats():
    """Get memory system statistics"""
    memory = get_memory_system()
    return memory.get_statistics()


# ========== Error Enhancement Endpoint ==========

@router.post("/errors/enhance")
async def enhance_error(request: ErrorEnhanceRequest):
    """Enhance error message with helpful info"""
    enhancer = get_error_enhancer()
    enhanced = enhancer.enhance_error(request.error_message)
    formatted = enhancer.format_for_display(enhanced)
    
    return {
        **enhanced,
        "formatted": formatted
    }


# ========== Performance Dashboard Endpoints ==========

@router.get("/performance/dashboard")
async def get_performance_dashboard(days: int = 30):
    """Get agent performance dashboard data"""
    tracker = get_performance_tracker()
    return tracker.get_dashboard_data(days)


@router.get("/performance/agent/{agent_name}")
async def get_agent_performance(agent_name: str, days: int = 30):
    """Get performance stats for specific agent"""
    tracker = get_performance_tracker()
    return tracker.get_agent_statistics(agent_name, days)


@router.get("/performance/bottlenecks")
async def get_bottlenecks(days: int = 30):
    """Identify performance bottlenecks"""
    tracker = get_performance_tracker()
    return {
        "bottlenecks": tracker.identify_bottlenecks(days),
        "period_days": days
    }


@router.get("/performance/errors")
async def get_error_trends(days: int = 30):
    """Get error trends"""
    tracker = get_performance_tracker()
    return tracker.get_error_trends(days)


# ========== Build Storage Endpoints ==========

@router.get("/builds/persistent")
async def list_persistent_builds(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List builds from persistent storage"""
    storage = get_build_storage()
    builds = storage.list_builds(status, limit, offset)
    
    return {
        "builds": builds,
        "total": len(builds),
        "statistics": storage.get_statistics()
    }


@router.get("/builds/persistent/{build_id}")
async def get_persistent_build(build_id: str):
    """Get build from persistent storage"""
    storage = get_build_storage()
    build = storage.get_build(build_id)
    
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    
    return build


@router.get("/builds/persistent/{build_id}/logs")
async def get_build_logs(build_id: str, limit: int = 100):
    """Get build logs"""
    storage = get_build_storage()
    logs = storage.get_logs(build_id, limit)
    
    return {
        "build_id": build_id,
        "logs": logs,
        "total": len(logs)
    }


@router.get("/builds/persistent/{build_id}/metrics")
async def get_build_metrics(build_id: str):
    """Get build metrics"""
    storage = get_build_storage()
    metrics = storage.get_metrics(build_id)
    
    if not metrics:
        raise HTTPException(status_code=404, detail="Metrics not found")
    
    return metrics


# ========== Conversation Context Endpoints ==========

@router.get("/conversation/threads")
async def list_threads(build_id: Optional[str] = None):
    """List conversation threads"""
    context = get_conversation_context()
    
    if build_id:
        threads = context.get_build_threads(build_id)
    else:
        threads = list(context.threads.values())
    
    return {
        "threads": [t.to_dict() for t in threads],
        "total": len(threads),
        "statistics": context.get_statistics()
    }


@router.get("/conversation/context/{agent_name}")
async def get_agent_conversation_context(
    agent_name: str,
    build_id: Optional[str] = None,
    limit: int = 10
):
    """Get conversation context for agent"""
    context = get_conversation_context()
    return context.get_agent_context(agent_name, build_id, limit)


# ========== System Health Endpoint ==========

@router.get("/system/health")
async def system_health():
    """Get overall system health"""
    memory = get_memory_system()
    tracker = get_performance_tracker()
    storage = get_build_storage()
    
    return {
        "status": "healthy",
        "components": {
            "memory_system": {
                "status": "operational",
                "stats": memory.get_statistics()
            },
            "performance_tracker": {
                "status": "operational",
                "recent_executions": len(tracker.executions)
            },
            "build_storage": {
                "status": "operational",
                "stats": storage.get_statistics()
            }
        },
        "timestamp": "2025-01-01T00:00:00Z"
    }
