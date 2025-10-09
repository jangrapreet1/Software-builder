"""
Simple test to verify Google Gemini API connection
"""
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

# Load environment variables
load_dotenv()

def test_gemini_connection():
    """Test basic Gemini API connection"""
    print("🧪 Testing Google Gemini API Connection...")
    print("=" * 50)
    
    # Get API key from environment
    api_key = os.getenv("GOOGLE_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY not found in environment")
        print("Please check your .env file")
        return False
    
    if api_key == "your-google-api-key-here":
        print("❌ ERROR: GOOGLE_API_KEY is still set to placeholder value")
        print("Please replace with your actual Gemini API key")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...")
    print(f"✅ Model: {model_name}")
    
    try:
        # Initialize the LLM (same as coordinator uses)
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.7,
            google_api_key=api_key
        )
        
        print("\n📡 Testing API call...")
        
        # Simple test message
        messages = [
            SystemMessage(content="You are a helpful assistant. Respond briefly."),
            HumanMessage(content="Say 'Hello, API test successful!' and nothing else.")
        ]
        
        # Make the API call
        response = llm.invoke(messages)
        
        print(f"✅ API Response: {response.content}")
        print("\n🎉 Gemini API connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = test_gemini_connection()
    if success:
        print("\n✅ Your Gemini API is working correctly!")
        print("The coordinator should be able to make API calls.")
    else:
        print("\n❌ Gemini API test failed.")
        print("Check your API key and internet connection.")