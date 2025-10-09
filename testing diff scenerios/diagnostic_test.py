"""
Diagnostic test for the coordinator workflow
Tests the exact same steps as the main application
"""
import os
import asyncio
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

# Load environment variables
load_dotenv()

async def test_coordinator_step():
    """Test the exact same step that's hanging in the coordinator"""
    print("🔍 Testing Coordinator Agent Step...")
    print("=" * 50)
    
    # Get API key
    api_key = os.getenv("GOOGLE_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    if not api_key:
        print("❌ No API key found")
        return False
    
    print(f"✅ Using model: {model_name}")
    
    try:
        # Initialize LLM (exact same as coordinator)
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.7,
            google_api_key=api_key
        )
        
        # Test the exact same prompt as coordinator
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

        brief = "Build a simple todo list app with user authentication"
        
        print(f"📝 Testing brief: {brief}")
        print("⏳ Making API call...")
        
        # Make the exact same API call as coordinator
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Project Brief: {brief}")
        ]
        
        response = await llm.ainvoke(messages)
        
        print(f"✅ API Response received!")
        print(f"📄 Response length: {len(response.content)} characters")
        print(f"📄 First 200 chars: {response.content[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return False

async def test_langgraph_workflow():
    """Test if LangGraph workflow is the issue"""
    print("\n🔍 Testing LangGraph Workflow...")
    print("=" * 50)
    
    try:
        from langgraph.graph import StateGraph, END
        
        # Create a simple test workflow
        def test_node(state):
            print("✅ Test node executed")
            return {"test": "success"}
        
        # Build workflow
        workflow = StateGraph(dict)
        workflow.add_node("test", test_node)
        workflow.set_entry_point("test")
        workflow.add_edge("test", END)
        
        compiled_workflow = workflow.compile()
        
        print("⏳ Executing workflow...")
        result = await compiled_workflow.ainvoke({"input": "test"})
        
        print(f"✅ Workflow completed: {result}")
        return True
        
    except Exception as e:
        print(f"❌ LangGraph Error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return False

async def main():
    print("🧪 Coordinator Diagnostic Test")
    print("=" * 60)
    
    # Test 1: Basic API call
    api_success = await test_coordinator_step()
    
    # Test 2: LangGraph workflow
    workflow_success = await test_langgraph_workflow()
    
    print("\n" + "=" * 60)
    print("📊 DIAGNOSTIC RESULTS")
    print("=" * 60)
    print(f"API Call Test: {'✅ PASS' if api_success else '❌ FAIL'}")
    print(f"LangGraph Test: {'✅ PASS' if workflow_success else '❌ FAIL'}")
    
    if api_success and workflow_success:
        print("\n🎉 Both tests passed!")
        print("The issue might be in the coordinator workflow execution.")
        print("Try restarting the coordinator or check for async/await issues.")
    elif api_success and not workflow_success:
        print("\n⚠️ API works but LangGraph has issues")
        print("This suggests a LangGraph configuration problem.")
    elif not api_success:
        print("\n❌ API call failed")
        print("This explains why the coordinator hangs.")
    else:
        print("\n🤔 Unexpected results")

if __name__ == "__main__":
    asyncio.run(main())