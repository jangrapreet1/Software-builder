# Quick Start Guide

Get up and running with the Autonomous App-Building Platform in minutes!

## Prerequisites

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Docker Desktop** (optional) - [Download](https://www.docker.com/products/docker-desktop/)
- **OpenAI API Key** - [Get one here](https://platform.openai.com/api-keys)

## Installation

### Option 1: Automated Setup (Recommended)

**Windows:**
```powershell
.\scripts\setup.ps1
```

**Linux/Mac:**
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### Option 2: Manual Setup

1. **Clone or download the repository**

2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
cd coordinator
pip install -r requirements.txt
cd ..
```

3. **Create environment file:**
```bash
cp .env.example .env
```

4. **Edit `.env` and add your OpenAI API key:**
```env
OPENAI_API_KEY=sk-your-api-key-here
```

## Running the Platform

### Start the Coordinator

**Windows:**
```powershell
.\scripts\start.ps1
```

**Linux/Mac:**
```bash
python coordinator/main.py
```

You should see:
```
═══════════════════════════════════════════════════
  Autonomous App-Building Platform - Coordinator
═══════════════════════════════════════════════════

INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:5000
```

### Access the UI

Open your browser and navigate to:
```
http://localhost:5000/ui
```

## Build Your First App

### Using the UI

1. Open http://localhost:5000/ui in your browser
2. Enter a project brief, for example:
   ```
   Build a task management app with user authentication and task sharing
   ```
3. Click **"Build Application"**
4. Watch the real-time progress as agents create your app
5. When complete, access your app at the provided URL

### Using the API

```python
import requests

response = requests.post('http://localhost:5000/api/build', json={
    'description': 'Build a blog platform with comments and likes',
    'name': 'my-blog'
})

print(response.json())
```

### Using the Example Script

```bash
python scripts/example_build.py
```

## What Gets Generated

After the build completes, you'll find your application in the `generated/` directory:

```
generated/
└── your-app-name/
    ├── backend/          # FastAPI backend
    ├── frontend/         # React frontend
    ├── docker-compose.yml
    ├── .env.example
    └── README.md
```

## Running Your Generated App

### With Docker (Recommended)

```bash
cd generated/your-app-name
docker-compose up --build
```

Access your app:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### Without Docker

**Backend:**
```bash
cd generated/your-app-name/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend:**
```bash
cd generated/your-app-name/frontend
npm install
npm run dev
```

## Example Project Briefs

Try these examples to explore the platform's capabilities:

### Simple
- "Build a task management app with user authentication"
- "Create a notes app with categories and search"
- "Build a simple blog with posts and comments"

### Moderate
- "Build a recipe sharing platform with user profiles, recipe uploads, ratings, and comments"
- "Create an event management system with user authentication, event creation, RSVP tracking, and calendar view"
- "Build an e-commerce store with products, shopping cart, checkout, and order history"

### Advanced
- "Build a project management tool with teams, projects, tasks, milestones, file attachments, and real-time notifications"
- "Create a social media platform with posts, likes, comments, friends, messaging, and feeds"

## Troubleshooting

### API Key Not Working

Make sure your OpenAI API key is:
1. Valid and active
2. Has sufficient credits
3. Properly set in the `.env` file
4. Starts with `sk-`

### Port Already in Use

If port 5000 is taken, edit `.env`:
```env
COORDINATOR_PORT=5001
```

### Build Fails

Check the logs in the UI for specific errors. Common issues:
- Invalid project brief (too vague)
- API rate limits
- Network connectivity

### Generated App Won't Start

1. Make sure Docker is running
2. Check port availability (3000, 8000, 5432)
3. Review the app's README.md for specific instructions

## Next Steps

- **Read the [Architecture Guide](docs/architecture.md)** to understand how it works
- **Check the [API Reference](docs/api.md)** for programmatic usage
- **Review [Workflows](docs/workflows.md)** to see the build process
- **Explore [Examples](examples/)** for more complex use cases

## Getting Help

- **Documentation:** See the `docs/` folder
- **Issues:** Check for common problems in README.md
- **Logs:** Review build logs in the UI for debugging

## Pro Tips

1. **Be Specific:** More detailed briefs produce better results
   - ❌ "Build an app"
   - ✓ "Build a task management app with user authentication, task categories, and due dates"

2. **Start Simple:** Begin with core features, iterate later

3. **Review Generated Code:** The code is meant to be modified and extended

4. **Use Docker:** Simplifies deployment and reduces setup issues

5. **Save Your Briefs:** Keep track of successful project descriptions

## What's Next?

Now that you're up and running, try:
1. Building a few sample applications
2. Modifying generated code to your needs
3. Exploring the architecture and workflow
4. Integrating builds into your workflow

Happy Building! 🚀
