"""
Test with timeout to see if workflow hangs
"""
import os
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

async def test_workflow_with_timeout():
    """Test the workflow with a timeout"""
    print("⏰ Testing Workflow with Timeout...")
    print("=" * 50)
    
    try:
        # Add coordinator directory to path
        coordinator_path = Path(__file__).parent.parent / "coordinator"
        sys.path.insert(0, str(coordinator_path))
        
        from workflows.app_builder import AppBuilderWorkflow
        from config.settings import Settings
        
        # Initialize workflow
        settings = Settings()
        workflow = AppBuilderWorkflow(settings)
        
        print("⏳ Starting workflow with 30-second timeout...")
        
        # Run workflow with timeout
        try:
            result = await asyncio.wait_for(
                workflow.build_from_brief(
                    description="Build a simple todo list app with user authentication",
                    name="test-timeout"
                ),
                timeout=30.0  # 30 second timeout
            )
            
            print(f"✅ Workflow completed: {result}")
            return True
            
        except asyncio.TimeoutError:
            print("❌ Workflow timed out after 30 seconds")
            print("This confirms the workflow is hanging")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_workflow_with_timeout())