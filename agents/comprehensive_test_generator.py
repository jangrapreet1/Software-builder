"""
Comprehensive Test Generator - Generate unit, integration, and E2E tests
Phase 3B.1 from analysis
"""
from typing import Dict, List, Optional
from pathlib import Path

from agents.base_agent import BaseAgent, ExecutionContext, ExecutionResult, AgentStatus, AgentCapability


class ComprehensiveTestGenerator(BaseAgent):
    """
    Generates comprehensive test suites:
    - Unit tests for all components
    - Integration tests for APIs
    - E2E tests with Playwright
    - API tests with test clients
    """
    
    def get_capabilities(self) -> List[AgentCapability]:
        return [AgentCapability.TESTING, AgentCapability.CODE_GENERATION]
    
    def validate_input(self, request_data: Dict) -> tuple[bool, Optional[str]]:
        if "project_path" not in request_data:
            return False, "project_path is required"
        if "entities" not in request_data:
            return False, "entities are required"
        return True, None
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """Generate comprehensive test suite"""
        project_path = Path(context.request_data["project_path"])
        entities = context.request_data["entities"]
        framework = context.request_data.get("backend_framework", "fastapi")
        frontend_framework = context.request_data.get("frontend_framework", "react-vite")
        
        generated_tests = {}
        
        # Generate backend unit tests
        context.add_telemetry("generating_backend_tests", {"entity_count": len(entities)})
        backend_tests = self._generate_backend_unit_tests(entities, framework)
        generated_tests.update(backend_tests)
        
        # Generate frontend unit tests
        context.add_telemetry("generating_frontend_tests", {"entity_count": len(entities)})
        frontend_tests = self._generate_frontend_unit_tests(entities, frontend_framework)
        generated_tests.update(frontend_tests)
        
        # Generate integration tests
        context.add_telemetry("generating_integration_tests", {})
        integration_tests = self._generate_integration_tests(entities, framework)
        generated_tests.update(integration_tests)
        
        # Generate E2E tests
        context.add_telemetry("generating_e2e_tests", {})
        e2e_tests = self._generate_e2e_tests(entities)
        generated_tests.update(e2e_tests)
        
        # Generate test configuration
        test_config = self._generate_test_config(framework, frontend_framework)
        generated_tests.update(test_config)
        
        return ExecutionResult(
            status=AgentStatus.COMPLETED,
            output={
                "tests": generated_tests,
                "summary": {
                    "total_files": len(generated_tests),
                    "backend_tests": len(backend_tests),
                    "frontend_tests": len(frontend_tests),
                    "integration_tests": len(integration_tests),
                    "e2e_tests": len(e2e_tests),
                    "coverage_target": "90%"
                }
            },
            metadata={
                "entities_covered": len(entities),
                "test_types": ["unit", "integration", "e2e"]
            }
        )
    
    def _generate_backend_unit_tests(self, entities: List[Dict], framework: str) -> Dict[str, str]:
        """Generate backend unit tests"""
        tests = {}
        
        if framework == "fastapi":
            # Test configuration
            tests["backend/tests/conftest.py"] = '''import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def auth_token(client):
    # Create test user and get token
    response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    return response.json()["access_token"]
'''
            
            # Generate tests for each entity
            for entity in entities:
                entity_name = entity["name"]
                entity_lower = entity_name.lower()
                
                tests[f"backend/tests/test_{entity_lower}.py"] = f'''import pytest
from fastapi.testclient import TestClient

def test_create_{entity_lower}(client, auth_token):
    """Test creating {entity_lower}"""
    headers = {{"Authorization": f"Bearer {{auth_token}}"}}
    response = client.post("/api/{entity_lower}s", json={{
        {self._generate_test_data(entity)}
    }}, headers=headers)
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["id"] is not None

def test_read_{entity_lower}(client, auth_token):
    """Test reading {entity_lower}"""
    # First create one
    headers = {{"Authorization": f"Bearer {{auth_token}}"}}
    create_response = client.post("/api/{entity_lower}s", json={{
        {self._generate_test_data(entity)}
    }}, headers=headers)
    {entity_lower}_id = create_response.json()["id"]
    
    # Then read it
    response = client.get(f"/api/{entity_lower}s/{{' + entity_lower + '_id}}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == {entity_lower}_id

def test_update_{entity_lower}(client, auth_token):
    """Test updating {entity_lower}"""
    headers = {{"Authorization": f"Bearer {{auth_token}}"}}
    # Create
    create_response = client.post("/api/{entity_lower}s", json={{
        {self._generate_test_data(entity)}
    }}, headers=headers)
    {entity_lower}_id = create_response.json()["id"]
    
    # Update
    update_data = {{{self._generate_test_data(entity, prefix="updated_")}}}
    response = client.put(f"/api/{entity_lower}s/{{' + entity_lower + '_id}}", json=update_data, headers=headers)
    assert response.status_code == 200

def test_delete_{entity_lower}(client, auth_token):
    """Test deleting {entity_lower}"""
    headers = {{"Authorization": f"Bearer {{auth_token}}"}}
    # Create
    create_response = client.post("/api/{entity_lower}s", json={{
        {self._generate_test_data(entity)}
    }}, headers=headers)
    {entity_lower}_id = create_response.json()["id"]
    
    # Delete
    response = client.delete(f"/api/{entity_lower}s/{{' + entity_lower + '_id}}", headers=headers)
    assert response.status_code == 200
    
    # Verify deletion
    get_response = client.get(f"/api/{entity_lower}s/{{' + entity_lower + '_id}}", headers=headers)
    assert get_response.status_code == 404

def test_list_{entity_lower}s(client, auth_token):
    """Test listing {entity_lower}s"""
    headers = {{"Authorization": f"Bearer {{auth_token}}"}}
    response = client.get("/api/{entity_lower}s", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list) or "items" in data
'''
        
        return tests
    
    def _generate_test_data(self, entity: Dict, prefix: str = "") -> str:
        """Generate test data for entity"""
        fields = entity.get("fields", [])
        data_parts = []
        
        for field in fields[:3]:  # Limit to first 3 fields
            field_name = field["name"]
            field_type = field.get("type", "string")
            
            if field_type == "string":
                value = f'"{prefix}{field_name}_test"'
            elif field_type == "int":
                value = "42"
            elif field_type == "float":
                value = "3.14"
            elif field_type == "bool":
                value = "true"
            elif field_type == "datetime":
                value = '"2024-01-01T00:00:00Z"'
            else:
                value = f'"{prefix}{field_name}_value"'
            
            data_parts.append(f'        "{field_name}": {value}')
        
        return ",\n".join(data_parts) if data_parts else '        "name": "test"'
    
    def _generate_frontend_unit_tests(self, entities: List[Dict], framework: str) -> Dict[str, str]:
        """Generate frontend unit tests"""
        tests = {}
        
        if "react" in framework.lower():
            # Test setup
            tests["frontend/src/setupTests.ts"] = '''import '@testing-library/jest-dom'
'''
            
            # Generate component tests for each entity
            for entity in entities:
                entity_name = entity["name"]
                
                tests[f"frontend/src/components/{entity_name}List.test.tsx"] = f'''import {{ render, screen, waitFor }} from '@testing-library/react'
import {{ {entity_name}List }} from './{entity_name}List'

jest.mock('../lib/api', () => ({{
  get: jest.fn(() => Promise.resolve({{ data: [] }}))
}}))

describe('{entity_name}List', () => {{
  it('renders without crashing', () => {{
    render(<{entity_name}List />)
    expect(screen.getByText(/{entity_name}/i)).toBeInTheDocument()
  }})

  it('displays loading state', () => {{
    render(<{entity_name}List />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  }})

  it('renders {entity_name.lower()} items', async () => {{
    const mockData = [
      {{ id: 1, name: 'Test {entity_name} 1' }},
      {{ id: 2, name: 'Test {entity_name} 2' }}
    ]
    
    const api = require('../lib/api')
    api.get.mockResolvedValueOnce({{ data: mockData }})
    
    render(<{entity_name}List />)
    
    await waitFor(() => {{
      expect(screen.getByText('Test {entity_name} 1')).toBeInTheDocument()
      expect(screen.getByText('Test {entity_name} 2')).toBeInTheDocument()
    }})
  }})
}})
'''
        
        return tests
    
    def _generate_integration_tests(self, entities: List[Dict], framework: str) -> Dict[str, str]:
        """Generate integration tests"""
        tests = {}
        
        tests["backend/tests/test_integration.py"] = f'''import pytest
from fastapi.testclient import TestClient

def test_full_crud_workflow(client, auth_token):
    """Test complete CRUD workflow across multiple entities"""
    headers = {{"Authorization": f"Bearer {{auth_token}}"}}
    
    # Create entities
    created_ids = {{}}
    
    {self._generate_integration_test_body(entities)}
    
    # Verify all created
    for entity_type, entity_id in created_ids.items():
        response = client.get(f"/api/{{entity_type}}/{{entity_id}}", headers=headers)
        assert response.status_code == 200

def test_api_error_handling(client):
    """Test API error handling"""
    # Test without authentication
    response = client.get("/api/protected-endpoint")
    assert response.status_code == 401
    
    # Test with invalid data
    response = client.post("/api/endpoint", json={{}})
    assert response.status_code in [400, 422]

def test_api_pagination(client, auth_token):
    """Test API pagination"""
    headers = {{"Authorization": f"Bearer {{auth_token}}"}}
    
    # Create multiple items
    for i in range(25):
        client.post("/api/items", json={{"name": f"Item {{i}}"}}, headers=headers)
    
    # Test pagination
    response = client.get("/api/items?page=1&limit=10", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
'''
        
        return tests
    
    def _generate_integration_test_body(self, entities: List[Dict]) -> str:
        """Generate integration test body"""
        lines = []
        for entity in entities[:2]:  # Limit to first 2 entities
            entity_lower = entity["name"].lower()
            lines.append(f'''    response = client.post("/api/{entity_lower}s", json={{
        {self._generate_test_data(entity)}
    }}, headers=headers)
    assert response.status_code == 201
    created_ids["{entity_lower}s"] = response.json()["id"]
''')
        return "\n".join(lines) if lines else "    pass"
    
    def _generate_e2e_tests(self, entities: List[Dict]) -> Dict[str, str]:
        """Generate E2E tests with Playwright"""
        tests = {}
        
        # Playwright config
        tests["frontend/playwright.config.ts"] = '''import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
})
'''
        
        # E2E tests
        tests["frontend/e2e/auth.spec.ts"] = '''import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test('user can login', async ({ page }) => {
    await page.goto('/login')
    
    await page.fill('[name="email"]', 'test@example.com')
    await page.fill('[name="password"]', 'testpassword123')
    await page.click('button[type="submit"]')
    
    await expect(page).toHaveURL('/dashboard')
    await expect(page.locator('text=Welcome')).toBeVisible()
  })

  test('user can register', async ({ page }) => {
    await page.goto('/register')
    
    await page.fill('[name="email"]', 'newuser@example.com')
    await page.fill('[name="password"]', 'password123')
    await page.fill('[name="confirmPassword"]', 'password123')
    await page.click('button[type="submit"]')
    
    await expect(page).toHaveURL('/dashboard')
  })
})
'''
        
        for entity in entities[:2]:  # Generate for first 2 entities
            entity_name = entity["name"]
            entity_lower = entity_name.lower()
            
            tests[f"frontend/e2e/{entity_lower}.spec.ts"] = f'''import {{ test, expect }} from '@playwright/test'

test.describe('{entity_name} Management', () => {{
  test.beforeEach(async ({{ page }}) => {{
    // Login first
    await page.goto('/login')
    await page.fill('[name="email"]', 'test@example.com')
    await page.fill('[name="password"]', 'testpassword123')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/dashboard')
  }})

  test('can create {entity_lower}', async ({{ page }}) => {{
    await page.goto('/{entity_lower}s')
    await page.click('text=Create {entity_name}')
    
    // Fill form (adjust based on actual fields)
    await page.fill('[name="name"]', 'Test {entity_name}')
    await page.click('button[type="submit"]')
    
    await expect(page.locator('text=Test {entity_name}')).toBeVisible()
  }})

  test('can view {entity_lower} list', async ({{ page }}) => {{
    await page.goto('/{entity_lower}s')
    
    await expect(page.locator('h1')).toContainText('{entity_name}')
  }})

  test('can edit {entity_lower}', async ({{ page }}) => {{
    await page.goto('/{entity_lower}s')
    
    // Click first edit button
    await page.click('button[aria-label="Edit"]:first-of-type')
    
    await page.fill('[name="name"]', 'Updated {entity_name}')
    await page.click('button[type="submit"]')
    
    await expect(page.locator('text=Updated {entity_name}')).toBeVisible()
  }})
}})
'''
        
        return tests
    
    def _generate_test_config(self, backend_framework: str, frontend_framework: str) -> Dict[str, str]:
        """Generate test configuration files"""
        config = {}
        
        # Backend test config
        if backend_framework == "fastapi":
            config["backend/pytest.ini"] = '''[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
'''
        
        # Frontend test config
        if "react" in frontend_framework.lower():
            config["frontend/jest.config.js"] = '''module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  moduleNameMapper: {
    '\\\\.(css|less|scss|sass)$': 'identity-obj-proxy',
  },
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/index.tsx',
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
}
'''
        
        return config
