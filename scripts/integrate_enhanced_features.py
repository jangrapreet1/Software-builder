"""
Integration Script - Add enhanced features to coordinator main.py
This script patches the main.py to include enhanced workflow and API endpoints
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def integrate_enhanced_features():
    """Add enhanced features to the coordinator"""
    
    coordinator_main = Path(__file__).parent.parent / "coordinator" / "main.py"
    
    if not coordinator_main.exists():
        print(f"Error: {coordinator_main} not found")
        return False
    
    print(f"Reading {coordinator_main}...")
    with open(coordinator_main, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already integrated
    if "EnhancedAppBuilderWorkflow" in content:
        print("Enhanced features already integrated!")
        return True
    
    # Add imports after existing imports
    import_addition = """
# Enhanced features
try:
    from workflows.app_builder_enhanced import EnhancedAppBuilderWorkflow
    from api.enhanced_endpoints import router as enhanced_router, initialize_enhanced_services
    ENHANCED_FEATURES_AVAILABLE = True
    console.print("[green]✓ Enhanced features available[/green]")
except ImportError as e:
    console.print(f"[yellow]⚠ Enhanced features unavailable: {e}[/yellow]")
    ENHANCED_FEATURES_AVAILABLE = False
"""
    
    # Find where to add import (after other imports)
    import_marker = "from agents.tester_agent import TesterAgent"
    if import_marker in content:
        content = content.replace(
            import_marker,
            import_marker + import_addition
        )
    
    # Add enhanced workflow initialization
    workflow_addition = """
# Initialize enhanced workflow if available
enhanced_workflow = None
if ENHANCED_FEATURES_AVAILABLE:
    try:
        enhanced_workflow = EnhancedAppBuilderWorkflow(settings)
        initialize_enhanced_services(enhanced_workflow, settings)
        console.print("[green]✓ Enhanced workflow initialized[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠ Enhanced workflow initialization failed: {e}[/yellow]")
        enhanced_workflow = None
"""
    
    # Find where to add workflow (after workflow initialization)
    workflow_marker = "    workflow = AppBuilderWorkflowFixed(settings, build_registry)"
    if workflow_marker in content:
        content = content.replace(
            workflow_marker,
            workflow_marker + "\n" + workflow_addition
        )
    
    # Add enhanced router to app
    router_addition = """
# Include enhanced API router if available
if ENHANCED_FEATURES_AVAILABLE:
    try:
        app.include_router(enhanced_router)
        console.print("[green]✓ Enhanced API endpoints registered[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠ Enhanced API registration failed: {e}[/yellow]")
"""
    
    # Find where to add router (before or after other route definitions)
    # Add after the app initialization
    app_marker = 'app.add_middleware(\n    CORSMiddleware,'
    if app_marker in content:
        # Find the end of middleware setup
        middleware_end = content.find(')', content.find(app_marker)) + 1
        content = content[:middleware_end] + "\n\n" + router_addition + "\n" + content[middleware_end:]
    
    # Write updated content
    print(f"Writing updated content to {coordinator_main}...")
    with open(coordinator_main, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ Enhanced features integrated successfully!")
    print("\nNew features added:")
    print("  - Enhanced workflow with persistent state management")
    print("  - Comprehensive validation system")
    print("  - Error feedback loops")
    print("  - Metrics collection")
    print("  - Enhanced API endpoints at /api/enhanced/*")
    print("\nRestart the coordinator to activate new features.")
    
    return True


if __name__ == "__main__":
    success = integrate_enhanced_features()
    sys.exit(0 if success else 1)
