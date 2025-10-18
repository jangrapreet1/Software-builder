"""
Enhanced API Endpoints - Expose new robustness features
Provides metrics, error analytics, state management, and enhanced workflows
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from workflows.app_builder_enhanced import EnhancedAppBuilderWorkflow
from services.metrics_collector import get_metrics_collector
from services.error_feedback_system import ErrorFeedbackSystem
from services.enhanced_state_manager import EnhancedStateManager
from config.settings import Settings
from pathlib import Path


# Initialize router
router = APIRouter(prefix="/api/enhanced", tags=["enhanced"])

# Initialize services (will be set by main app)
enhanced_workflow: Optional[EnhancedAppBuilderWorkflow] = None
settings: Optional[Settings] = None


def initialize_enhanced_services(workflow: EnhancedAppBuilderWorkflow, app_settings: Settings):
    """Initialize enhanced services"""
    global enhanced_workflow, settings
    enhanced_workflow = workflow
    settings = app_settings


# Request/Response Models
class EnhancedBuildRequest(BaseModel):
    """Enhanced build request with all options"""
    description: str = Field(..., min_length=10, description="Project description")
    name: Optional[str] = Field(None, description="Project name")
    requirements: Optional[List[str]] = Field(default_factory=list, description="Additional requirements")
    enable_auto_resolution: bool = Field(True, description="Enable automatic problem resolution")
    run_tests: bool = Field(False, description="Run tests after build")


class StateUpdateRequest(BaseModel):
    """State update request"""
    updates: Dict[str, Any] = Field(..., description="State updates to apply")


# Build Management Endpoints
@router.post("/builds")
async def create_enhanced_build(
    request: EnhancedBuildRequest,
    background_tasks: BackgroundTasks
):
    """
    Create a new build with enhanced robustness features
    
    Features:
    - Persistent state with crash recovery
    - Comprehensive validation
    - Error feedback loops
    - Automatic problem resolution
    - Metrics collection
    """
    if not enhanced_workflow:
        raise HTTPException(status_code=503, detail="Enhanced workflow not initialized")
    
    try:
        result = await enhanced_workflow.build_from_brief(
            description=request.description,
            name=request.name,
            requirements=request.requirements,
            enable_auto_resolution=request.enable_auto_resolution,
            run_tests=request.run_tests
        )
        
        return {
            "success": True,
            "data": result,
            "message": "Build created successfully with enhanced features"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Build creation failed: {str(e)}")


@router.get("/builds/{build_id}")
async def get_enhanced_build_status(build_id: str):
    """Get enhanced build status with detailed information"""
    if not enhanced_workflow:
        raise HTTPException(status_code=503, detail="Enhanced workflow not initialized")
    
    status = await enhanced_workflow.get_build_status(build_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Build not found")
    
    return {
        "success": True,
        "data": status
    }


@router.get("/builds")
async def list_enhanced_builds():
    """List all builds with enhanced information"""
    if not enhanced_workflow:
        raise HTTPException(status_code=503, detail="Enhanced workflow not initialized")
    
    builds = await enhanced_workflow.list_builds()
    
    return {
        "success": True,
        "data": builds,
        "count": len(builds)
    }


@router.delete("/builds/{build_id}")
async def delete_enhanced_build(build_id: str):
    """Delete a build and its state"""
    if not enhanced_workflow:
        raise HTTPException(status_code=503, detail="Enhanced workflow not initialized")
    
    result = await enhanced_workflow.delete_build(build_id)
    
    return {
        "success": result["success"],
        "message": result["message"]
    }


@router.post("/builds/{build_id}/recover")
async def recover_build(build_id: str):
    """Recover a build from backup"""
    if not enhanced_workflow:
        raise HTTPException(status_code=503, detail="Enhanced workflow not initialized")
    
    result = await enhanced_workflow.recover_build(build_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="No backup found for build")
    
    return {
        "success": True,
        "data": result,
        "message": "Build recovered successfully"
    }


# State Management Endpoints
@router.get("/state/{build_id}")
async def get_build_state(build_id: str):
    """Get complete build state"""
    if not enhanced_workflow:
        raise HTTPException(status_code=503, detail="Enhanced workflow not initialized")
    
    state = enhanced_workflow.state_manager.get_state(build_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    
    return {
        "success": True,
        "data": state
    }


@router.patch("/state/{build_id}")
async def update_build_state(build_id: str, request: StateUpdateRequest):
    """Update specific fields in build state"""
    if not enhanced_workflow:
        raise HTTPException(status_code=503, detail="Enhanced workflow not initialized")
    
    success = enhanced_workflow.state_manager.update_state(build_id, request.updates)
    
    if not success:
        raise HTTPException(status_code=404, detail="State not found or update failed")
    
    return {
        "success": True,
        "message": "State updated successfully"
    }


@router.get("/state")
async def list_all_states():
    """List all available build states"""
    if not enhanced_workflow:
        raise HTTPException(status_code=503, detail="Enhanced workflow not initialized")
    
    states = enhanced_workflow.state_manager.list_all_states()
    
    return {
        "success": True,
        "data": states,
        "count": len(states)
    }


# Metrics Endpoints
@router.get("/metrics")
async def get_metrics():
    """Get all current metrics"""
    metrics_collector = get_metrics_collector()
    metrics = metrics_collector.get_all_metrics()
    
    return {
        "success": True,
        "data": metrics
    }


@router.get("/metrics/summary")
async def get_metrics_summary():
    """Get metrics summary and performance report"""
    if not enhanced_workflow:
        raise HTTPException(status_code=503, detail="Enhanced workflow not initialized")
    
    summary = enhanced_workflow.get_metrics_summary()
    
    return {
        "success": True,
        "data": summary
    }


@router.get("/metrics/agent/{agent_name}")
async def get_agent_metrics(agent_name: str):
    """Get metrics for a specific agent"""
    metrics_collector = get_metrics_collector()
    agent_metrics = metrics_collector.get_agent_metrics(agent_name)
    
    return {
        "success": True,
        "data": agent_metrics
    }


@router.get("/metrics/builds")
async def get_build_metrics():
    """Get build-related metrics"""
    metrics_collector = get_metrics_collector()
    build_metrics = metrics_collector.get_build_metrics()
    
    return {
        "success": True,
        "data": build_metrics
    }


@router.get("/metrics/health")
async def get_system_health():
    """Get overall system health"""
    metrics_collector = get_metrics_collector()
    health = metrics_collector.get_system_health()
    
    return {
        "success": True,
        "data": health
    }


@router.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """Get metrics in Prometheus format"""
    metrics_collector = get_metrics_collector()
    prometheus_format = metrics_collector.export_prometheus_format()
    
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=prometheus_format)


@router.post("/metrics/export")
async def export_metrics():
    """Export metrics to file"""
    metrics_collector = get_metrics_collector()
    
    try:
        filepath = metrics_collector.export_to_file()
        
        return {
            "success": True,
            "message": "Metrics exported successfully",
            "filepath": filepath
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.delete("/metrics")
async def reset_metrics():
    """Reset all metrics (use with caution)"""
    metrics_collector = get_metrics_collector()
    metrics_collector.reset_metrics()
    
    return {
        "success": True,
        "message": "All metrics reset"
    }


# Error Analytics Endpoints
@router.get("/errors/analytics")
async def get_error_analytics():
    """Get comprehensive error analytics"""
    if not enhanced_workflow:
        raise HTTPException(status_code=503, detail="Enhanced workflow not initialized")
    
    analytics = enhanced_workflow.get_error_analytics()
    
    return {
        "success": True,
        "data": analytics
    }


@router.get("/errors/feedback")
async def get_error_feedback():
    """Get error feedback for planning"""
    if not enhanced_workflow:
        raise HTTPException(status_code=503, detail="Enhanced workflow not initialized")
    
    feedback = enhanced_workflow.error_feedback.get_feedback_for_planning()
    
    return {
        "success": True,
        "data": feedback
    }


@router.get("/errors/statistics")
async def get_error_statistics():
    """Get error category statistics"""
    if not enhanced_workflow:
        raise HTTPException(status_code=503, detail="Enhanced workflow not initialized")
    
    stats = enhanced_workflow.error_feedback.get_category_statistics()
    
    return {
        "success": True,
        "data": stats
    }


@router.get("/errors/resolution-rates")
async def get_resolution_rates():
    """Get resolution success rates by category"""
    if not enhanced_workflow:
        raise HTTPException(status_code=503, detail="Enhanced workflow not initialized")
    
    rates = enhanced_workflow.error_feedback.get_resolution_success_rate()
    
    return {
        "success": True,
        "data": rates
    }


@router.get("/errors/preventive-specs")
async def get_preventive_specs():
    """Get preventive spec additions based on error patterns"""
    if not enhanced_workflow:
        raise HTTPException(status_code=503, detail="Enhanced workflow not initialized")
    
    specs = enhanced_workflow.error_feedback.generate_preventive_spec_additions()
    
    return {
        "success": True,
        "data": specs,
        "count": len(specs)
    }


@router.get("/errors/build/{build_id}")
async def get_build_errors(build_id: str):
    """Get error history for a specific build"""
    if not enhanced_workflow:
        raise HTTPException(status_code=503, detail="Enhanced workflow not initialized")
    
    errors = enhanced_workflow.error_feedback.get_build_error_history(build_id)
    
    return {
        "success": True,
        "data": errors,
        "count": len(errors)
    }


# Validation Endpoints
@router.post("/validate")
async def validate_application(source_path: str):
    """Run comprehensive validation on an application"""
    from services.build_validator import BuildValidator
    
    try:
        validator = BuildValidator()
        results = await validator.validate_build(source_path)
        
        return {
            "success": True,
            "data": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


# Dashboard Endpoint
@router.get("/dashboard")
async def get_dashboard_data():
    """Get comprehensive dashboard data"""
    if not enhanced_workflow:
        raise HTTPException(status_code=503, detail="Enhanced workflow not initialized")
    
    metrics_collector = get_metrics_collector()
    
    dashboard_data = {
        "system_health": metrics_collector.get_system_health(),
        "build_metrics": metrics_collector.get_build_metrics(),
        "error_statistics": enhanced_workflow.error_feedback.get_category_statistics(),
        "resolution_rates": enhanced_workflow.error_feedback.get_resolution_success_rate(),
        "recent_builds": await enhanced_workflow.list_builds(),
        "performance_summary": enhanced_workflow.get_metrics_summary(),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    return {
        "success": True,
        "data": dashboard_data
    }


# Health Check
@router.get("/health")
async def health_check():
    """Enhanced health check endpoint"""
    if not enhanced_workflow:
        return {
            "status": "degraded",
            "message": "Enhanced workflow not initialized",
            "components": {
                "workflow": "unavailable",
                "state_manager": "unavailable",
                "metrics": "available",
                "error_feedback": "unavailable"
            }
        }
    
    metrics_collector = get_metrics_collector()
    system_health = metrics_collector.get_system_health()
    
    return {
        "status": system_health.get("status", "unknown"),
        "message": "Enhanced features operational",
        "components": {
            "workflow": "available",
            "state_manager": "available",
            "metrics": "available",
            "error_feedback": "available"
        },
        "metrics": {
            "success_rate": system_health.get("success_rate", 0),
            "active_builds": system_health.get("active_builds", 0),
            "total_builds": system_health.get("total_builds", 0)
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
