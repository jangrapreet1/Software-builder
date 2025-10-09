# Testing Guide

## Overview

This guide covers how to test the Autonomous App-Building Platform and generated applications.

## Testing the Platform

### Unit Tests

Run platform unit tests:

```bash
# Test coordinator
cd coordinator
pytest tests/

# Test agents
pytest tests/test_agents.py

# Test workflows
pytest tests/test_workflows.py
```

### Integration Tests

Test the full build workflow:

```bash
pytest tests/integration/test_build_workflow.py -v
```

### API Tests

Test the coordinator API:

```bash
# Using pytest
pytest tests/test_api.py

# Using the provided test script
python scripts/test_api.py
```

Example API test:

```python
import requests

def test_health_check():
    response = requests.get('http://localhost:5000/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'

def test_build_app():
    response = requests.post('http://localhost:5000/api/build', json={
        'description': 'Build a simple todo app'
    })
    assert response.status_code == 200
    assert 'build_id' in response.json()
```

## Testing Generated Applications

### Backend Tests

Generated backends include pytest test suites:

```bash
cd generated/your-app/backend
pytest
```

Test structure:
```python
# tests/test_api.py
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_register_user():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/auth/register", json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "password123"
        })
        assert response.status_code == 201
```

### Frontend Tests

Add tests to generated frontends:

```bash
cd generated/your-app/frontend
npm test
```

Example test:
```typescript
// src/components/Button.test.tsx
import { render, screen } from '@testing-library/react';
import Button from './Button';

test('renders button with text', () => {
  render(<Button>Click me</Button>);
  expect(screen.getByText('Click me')).toBeInTheDocument();
});
```

### End-to-End Tests

Use Playwright for E2E testing:

```bash
cd generated/your-app
npx playwright install
npx playwright test
```

Example E2E test:
```typescript
// e2e/auth.spec.ts
import { test, expect } from '@playwright/test';

test('user can register and login', async ({ page }) => {
  await page.goto('http://localhost:3000/register');
  
  await page.fill('[name="email"]', 'test@example.com');
  await page.fill('[name="username"]', 'testuser');
  await page.fill('[name="password"]', 'password123');
  await page.click('button[type="submit"]');
  
  await expect(page).toHaveURL('/dashboard');
});
```

## Manual Testing

### Test Checklist for Generated Apps

#### Authentication
- [ ] User registration works
- [ ] User login works
- [ ] Logout works
- [ ] Protected routes require authentication
- [ ] Invalid credentials show error
- [ ] Token refresh works

#### CRUD Operations
- [ ] Create new items
- [ ] Read/list items
- [ ] Update existing items
- [ ] Delete items
- [ ] Pagination works
- [ ] Filtering works
- [ ] Sorting works

#### UI/UX
- [ ] Responsive on mobile
- [ ] Responsive on tablet
- [ ] Responsive on desktop
- [ ] Forms validate input
- [ ] Error messages display correctly
- [ ] Loading states work
- [ ] Success messages appear

#### API
- [ ] All endpoints respond
- [ ] Correct status codes returned
- [ ] Error handling works
- [ ] API documentation is accurate
- [ ] CORS configured correctly

## Performance Testing

### Load Testing

Use tools like `locust` or `k6`:

```python
# locustfile.py
from locust import HttpUser, task, between

class AppUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def build_app(self):
        self.client.post("/api/build", json={
            "description": "Build a test app"
        })
```

Run:
```bash
locust -f locustfile.py --host=http://localhost:5000
```

### Benchmarking

Benchmark build times:

```python
import time
import requests

def benchmark_build():
    start = time.time()
    
    response = requests.post('http://localhost:5000/api/build', json={
        'description': 'Build a simple app'
    })
    
    build_id = response.json()['build_id']
    
    # Wait for completion
    while True:
        status = requests.get(f'http://localhost:5000/api/build/{build_id}/status')
        if status.json()['status'] in ['success', 'failed']:
            break
        time.sleep(2)
    
    elapsed = time.time() - start
    print(f"Build completed in {elapsed:.2f} seconds")

benchmark_build()
```

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          cd coordinator && pip install -r requirements.txt
      
      - name: Run tests
        run: pytest tests/ -v
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      
      - name: Test build workflow
        run: python scripts/example_build.py
```

## Test Data

### Sample Project Briefs

Use these for consistent testing:

```python
TEST_BRIEFS = [
    "Build a todo app with user authentication",
    "Create a blog with posts and comments",
    "Build a recipe sharing platform",
    "Create an event management system"
]
```

### Mock Responses

Mock LLM responses for testing:

```python
MOCK_ANALYSIS = {
    "features": [
        {"name": "Authentication", "priority": "high"}
    ],
    "entities": [
        {"name": "User", "fields": [...]}
    ],
    "user_flows": [...]
}
```

## Debugging

### Enable Debug Logging

```python
# coordinator/main.py
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Debug Agent Communication

```python
# Log all agent messages
collaboration_manager.on_message = lambda msg: print(f"Agent Message: {msg}")
```

### Inspect Generated Code

```python
# Save generated code for inspection
with open('debug_output.py', 'w') as f:
    f.write(backend_code['main'])
```

## Common Issues

### Test Failures

**Issue:** Tests fail randomly
**Solution:** Use deterministic seeds, mock external services

**Issue:** Async tests hang
**Solution:** Set proper timeouts, check event loops

**Issue:** Database tests interfere
**Solution:** Use test database, transactions, fixtures

### Generated App Issues

**Issue:** App won't start
**Solution:** Check logs, verify dependencies, validate Docker config

**Issue:** API returns 500 errors
**Solution:** Check database connection, verify environment variables

**Issue:** Frontend can't connect to backend
**Solution:** Check CORS settings, verify API URL configuration

## Test Coverage

Measure code coverage:

```bash
pytest --cov=coordinator --cov-report=html tests/
```

View coverage report:
```bash
open htmlcov/index.html
```

## Best Practices

1. **Write tests first** for new features (TDD)
2. **Mock external services** (OpenAI API)
3. **Use fixtures** for common test data
4. **Test edge cases** and error conditions
5. **Keep tests fast** - use unit tests over integration tests
6. **Run tests in CI** before merging
7. **Test generated code** in isolation
8. **Monitor test coverage** - aim for >80%

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [React Testing Library](https://testing-library.com/react)
- [Playwright](https://playwright.dev/)
