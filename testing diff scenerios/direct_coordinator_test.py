"""
Quick fix test - bypass LangGraph workflow
Tests if the issue is with the workflow execution
"""
import os
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

load_dotenv()

async def test_direct_coordinator():
    """Test coordinator agent directly without LangGraph"""
    print("🚀 Testing Direct Coordinator Agent...")
    print("=" * 50)
    
    try:
        # Add coordinator directory to path
        coordinator_path = Path(__file__).parent.parent / "coordinator"
        sys.path.insert(0, str(coordinator_path))
        
        from config.settings import Settings
        from agents.coordinator_agent import CoordinatorAgent
        
        # Initialize settings and LLM
        settings = Settings()
        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            temperature=0.7,
            google_api_key=settings.google_api_key
        )
        
        # Create coordinator agent
        coordinator = CoordinatorAgent(llm, settings)
        
        print("⏳ Testing analyze_brief directly...")
        
        # Test the exact same call that's hanging
        result = await coordinator.analyze_brief("Build a simple todo list app with user authentication")
        
        print(f"✅ Analysis completed!")
        print(f"📊 Features: {len(result.get('features', []))}")
        print(f"📊 Entities: {len(result.get('entities', []))}")
        print(f"📊 User flows: {len(result.get('user_flows', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_direct_coordinator())