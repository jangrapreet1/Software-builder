"""
Terminal chat interface with Google Gemini
Uses the same API setup as the coordinator
"""
import os
import asyncio
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

# Load environment variables
load_dotenv()

class GeminiChat:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        if not self.api_key or self.api_key == "your-google-api-key-here":
            raise ValueError("Please set GOOGLE_API_KEY in your .env file")
        
        # Initialize LLM (same as coordinator)
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=0.7,
            google_api_key=self.api_key
        )
        
        self.conversation_history = []
    
    async def chat(self, user_input: str) -> str:
        """Send a message to Gemini and get response"""
        try:
            # Add user message to history
            self.conversation_history.append(HumanMessage(content=user_input))
            
            # Make API call
            response = await self.llm.ainvoke(self.conversation_history)
            
            # Add response to history
            self.conversation_history.append(response)
            
            return response.content
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        print("🧹 Conversation history cleared!")

async def main():
    print("🤖 Gemini Chat Terminal")
    print("=" * 40)
    print("Commands:")
    print("  /clear - Clear conversation history")
    print("  /quit  - Exit chat")
    print("=" * 40)
    
    try:
        chat = GeminiChat()
        print(f"✅ Connected to {chat.model_name}")
        print()
        
        while True:
            user_input = input("You: ").strip()
            
            if user_input.lower() == "/quit":
                print("👋 Goodbye!")
                break
            elif user_input.lower() == "/clear":
                chat.clear_history()
                continue
            elif not user_input:
                continue
            
            print("🤖 Gemini: ", end="", flush=True)
            
            try:
                response = await chat.chat(user_input)
                print(response)
            except Exception as e:
                print(f"❌ Error: {e}")
            
            print()
    
    except ValueError as e:
        print(f"❌ Setup Error: {e}")
    except KeyboardInterrupt:
        print("\n👋 Chat interrupted. Goodbye!")

if __name__ == "__main__":
    asyncio.run(main())