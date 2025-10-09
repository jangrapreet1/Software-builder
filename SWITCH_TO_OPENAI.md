# Quick Switch to OpenAI

If you want to switch back to OpenAI, follow these steps:

## 1. Update Dependencies

```powershell
# Edit requirements.txt - replace:
langchain-google-genai>=1.0.0
# with:
langchain-openai>=0.0.5

# Edit requirements.txt - replace:
google-generativeai>=0.3.0
# with:
openai>=1.10.0
```

## 2. Update .env

```env
# Replace:
GOOGLE_API_KEY=your-key
GEMINI_MODEL=gemini-flash-latest

# With:
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-4-turbo-preview
```

## 3. Reinstall Dependencies

```powershell
pip install -r requirements.txt
cd coordinator
pip install -r requirements.txt
```

## 4. Restart Coordinator

```powershell
python coordinator/main.py
```

---

**OR** just tell me and I'll do it automatically for you! 🤖
