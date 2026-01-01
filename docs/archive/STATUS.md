# Platform Status

## ✅ Currently Running

### Coordinator (Backend)
- **Status**: Running
- **URL**: http://localhost:5000
- **API Docs**: http://localhost:5000/docs (if available)
- **Health Check**: http://localhost:5000/health
- **UI**: http://localhost:5000/ui

### Configuration
- **LLM Provider**: Google Gemini
- **Model**: gemini-pro
- **API Key**: Configured ✓

## 🚀 How to Use

### Option 1: Web UI (Easiest)
1. Open: http://localhost:5000/ui
2. Enter a project description like:
   - "Build a task management app with user authentication"
   - "Create a blog with posts and comments"
   - "Build a recipe sharing platform"
3. Click "Build Application"
4. Watch real-time progress
5. Access your generated app when complete

### Option 2: Python Script
```python
import requests

response = requests.post('http://localhost:5000/api/build', json={
    'description': 'Build a notes app with categories',
    'name': 'my-notes-app'
})

print(response.json())
```

### Option 3: Command Line (curl)
```bash
curl -X POST http://localhost:5000/api/build \
  -H "Content-Type: application/json" \
  -d '{"description": "Build a simple blog", "name": "my-blog"}'
```

## 📁 Generated Apps Location

Generated applications will be created in:
```
c:\Users\Lenovo\Code\Software builder\generated\
```

Each app includes:
- `backend/` - FastAPI backend
- `frontend/` - React frontend
- `docker-compose.yml` - Docker setup
- `README.md` - Instructions

## 🏃 Running Generated Apps

After an app is generated:

```bash
cd generated/your-app-name
docker-compose up --build
```

Then access:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 🛑 Stopping Services

### Stop Coordinator
Press `Ctrl+C` in the terminal running the coordinator

### Stop Generated App
```bash
cd generated/your-app-name
docker-compose down
```

## 📊 API Endpoints

### Health Check
```
GET /health
```

### Build Application
```
POST /api/build
Body: {
  "description": "string",
  "name": "string (optional)",
  "requirements": ["string"] (optional)
}
```

### Get Build Status
```
GET /api/build/{build_id}/status
```

### List All Builds
```
GET /api/builds
```

### Delete Build
```
DELETE /api/build/{build_id}
```

## 🔧 Troubleshooting

### Coordinator Won't Start
1. Check if `.env` file exists with `GOOGLE_API_KEY`
2. Verify API key is valid
3. Check if port 5000 is available

### Build Fails
1. Check logs in the UI
2. Verify Gemini API has credits
3. Check internet connection
4. Try a simpler project description

### Generated App Won't Start
1. Ensure Docker is running
2. Check ports 3000, 8000, 5432 are available
3. Review the app's README.md
4. Check Docker logs: `docker-compose logs`

## 📝 Example Project Briefs

### Simple
- "Build a todo list app"
- "Create a notes app with categories"
- "Build a simple blog"

### Moderate
- "Build a task management app with user authentication and task sharing"
- "Create a recipe sharing platform with ratings and comments"
- "Build an event management system with RSVP tracking"

### Advanced
- "Build a project management tool with teams, projects, tasks, and file attachments"
- "Create a social media platform with posts, likes, comments, and messaging"

## 🎯 Next Steps

1. **Try the UI**: Open http://localhost:5000/ui
2. **Build your first app**: Use one of the example briefs
3. **Explore generated code**: Check the `generated/` folder
4. **Run the app**: Use Docker Compose
5. **Customize**: Modify the generated code as needed

## 📚 Documentation

- [README.md](README.md) - Main documentation
- [QUICKSTART.md](QUICKSTART.md) - Getting started guide
- [docs/architecture.md](docs/architecture.md) - System architecture
- [docs/api.md](docs/api.md) - API reference
- [docs/workflows.md](docs/workflows.md) - Build workflows

## ⚙️ Configuration

Current settings (from `.env`):
- `GOOGLE_API_KEY`: ✓ Configured
- `GEMINI_MODEL`: gemini-pro
- `COORDINATOR_PORT`: 5000
- `GENERATED_APPS_DIR`: ./generated

## 🌟 Features

✅ Natural language project briefs
✅ Automatic code generation
✅ FastAPI backend with authentication
✅ React frontend with TailwindCSS
✅ PostgreSQL database
✅ Docker deployment
✅ Real-time progress tracking
✅ Complete documentation
✅ Test suites included

---

**Platform is ready to use!** 🚀

Start building applications at: http://localhost:5000/ui
