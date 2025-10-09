# Testing Guide - Autonomous App Builder

## 🎯 Quick Start Testing

### 1. Start the Coordinator (Terminal 1)
```bash
cd coordinator
python main.py
```

Wait for: `Application startup complete.`

### 2. Run Comprehensive Tests (Terminal 2)
```bash
python comprehensive_test.py
```

### 3. Test the UI (Browser)
Open: http://localhost:5000/ui

---

## ✅ What Was Improved

### Error Handling
- ✅ Input validation (empty/short descriptions rejected)
- ✅ JSON parsing with fallback mechanisms
- ✅ Detailed error messages at each step
- ✅ Graceful degradation (validation warnings don't block deployment)
- ✅ Better error logging with context

### UI Enhancements
- ✅ Modern gradient animated background
- ✅ Glass morphism effects
- ✅ Responsive design improvements
- ✅ Better status indicators
- ✅ Cross-browser compatibility (Safari, Chrome, Firefox)

### Testing Infrastructure
- ✅ Created `comprehensive_test.py` with 10+ test cases
- ✅ Test results exported to JSON
- ✅ Color-coded console output
- ✅ Success rate tracking

---

## 🧪 Test Scenarios

### Scenario 1: Simple Build
```
Description: "Build a simple notes app with add and delete features"
Expected: Build completes in 1-2 minutes with all files generated
```

### Scenario 2: Complex Build
```
Description: "Create a task management system with user auth, teams, and assignments"
Name: "task-manager-pro"
Requirements: ["real-time updates", "email notifications"]
Expected: Build completes in 3-4 minutes with advanced features
```

### Scenario 3: Error Handling
```
Description: "" (empty)
Expected: Error message "Project description cannot be empty"
```

### Scenario 4: Concurrent Builds
```
Action: Start 2 builds simultaneously from different tabs
Expected: Both builds proceed independently
```

---

## 📊 Expected Test Results

### comprehensive_test.py Output
```
Total Tests: 10
Passed: 9-10 ✅
Failed: 0-1 ❌
Success Rate: 90-100%
```

### Test Breakdown
- API Health Check ✅
- Root Endpoint ✅
- API Response Time ✅
- List Builds ✅
- Invalid Build Request ✅
- Non-existent Build Status ✅
- Build with Custom Name ✅
- Build with Requirements ✅
- Concurrent Builds ✅
- Build Simple App End-to-End ✅ (may take 2-3 min)

---

## 🐛 Troubleshooting

### Issue: "Unable to connect to the remote server"
**Solution**: Start the coordinator first
```bash
cd coordinator
python main.py
```

### Issue: "API rate limit exceeded"
**Solution**: Wait 1-5 minutes, then retry
- Gemini API has rate limits
- Free tier: 15 requests/minute
- Consider upgrading for production use

### Issue: "Module not found"
**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "Port 5000 already in use"
**Solution**: Kill the process or change port
```bash
# Kill process on port 5000 (Windows)
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Or change port in .env
COORDINATOR_PORT=5001
```

---

## 📝 Testing Checklist

Before testing:
- [ ] `.env` file exists with valid `GOOGLE_API_KEY`
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Port 5000 is available
- [ ] You have internet connection (for Gemini API)

During testing:
- [ ] Coordinator starts without errors
- [ ] Health check returns `{"status": "healthy"}`
- [ ] UI loads at http://localhost:5000/ui
- [ ] API status shows "Connected"
- [ ] Can create builds successfully
- [ ] Progress updates in real-time
- [ ] Generated files appear in `./generated/` folder
- [ ] Test suite passes with >90% success rate

After testing:
- [ ] Review `test_results.json` for detailed results
- [ ] Check generated app structure
- [ ] Verify README and docker-compose.yml exist
- [ ] Test generated app with `docker-compose up`

---

## 🚀 Next Steps After Testing

1. **Review Generated Code**
   ```bash
   cd generated/<project-name>
   cat README.md
   ```

2. **Run Generated App**
   ```bash
   docker-compose up --build
   # Frontend: http://localhost:3000
   # Backend: http://localhost:8000
   # API Docs: http://localhost:8000/docs
   ```

3. **Report Issues**
   - Check coordinator logs for errors
   - Review test_results.json
   - Check IMPROVEMENTS_COMPLETED.md for known issues

---

## 📖 Additional Test Scripts

### quick_test.py
```bash
python quick_test.py
```
- Faster, simpler test
- Good for quick verification
- Monitors one complete build

### test_gemini_2.py
```bash
python test_gemini_2.py
```
- Tests specifically with Gemini 2.0 Flash
- Validates model configuration
- Shorter timeout (2 minutes)

### test_build.py
```bash
python test_build.py
```
- Basic build test
- Simple todo app
- Good for first-time testing

---

## 💡 Tips for Successful Testing

1. **Start Fresh**: Close all terminals and start clean
2. **Check Logs**: Watch coordinator terminal for real-time updates
3. **Be Patient**: First build may take longer (model warm-up)
4. **Monitor Resources**: Builds use CPU/memory for code generation
5. **Test Incrementally**: Run simple tests before complex ones

---

## 🎉 Success Indicators

You know testing is successful when:
- ✅ All health checks pass
- ✅ UI loads and shows "Connected"
- ✅ At least one build completes to 100%
- ✅ Generated code structure looks correct
- ✅ Error messages are clear and helpful
- ✅ UI is responsive and animated
- ✅ No crashes or unhandled exceptions

---

**Ready to test!** Start with the Quick Start section above.

**Note**: The Gemini API rate limit issue is temporary. Wait a few minutes if you encounter it.

---

## ⚙️ Automated Test Runner (Windows)

Run all checks locally with one command:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_all_tests.ps1
```

Options:

- `-Fix` formats with black/isort before running tests
- `-E2E` runs `comprehensive_test.py` against a local server
- `-Fake` starts the coordinator with `USE_FAKE_WORKFLOW=1` (no external LLM calls)

Examples:

```powershell
# Unit/API only
powershell -ExecutionPolicy Bypass -File scripts/run_all_tests.ps1

# Unit/API + E2E in fake mode (recommended without API key)
powershell -ExecutionPolicy Bypass -File scripts/run_all_tests.ps1 -E2E -Fake
```

---

## 🧪 Fake Workflow Mode

To avoid external dependencies during tests, you can start the coordinator with a built-in fake workflow:

```bash
set USE_FAKE_WORKFLOW=1  # Windows CMD
$env:USE_FAKE_WORKFLOW=1 # PowerShell
```

In this mode, builds complete instantly and endpoints behave deterministically.

---

## 🏗️ Continuous Integration (CI)

CI runs on every push/PR:

- Lint checks (black, isort)
- Unit/API tests
- E2E (fake) job that boots the coordinator with `USE_FAKE_WORKFLOW` and runs `quick_test.py`

YAML: `.github/workflows/ci.yml`
