"""CI/CD Pipeline Generator"""
from pathlib import Path

class CICDGenerator:
    """Generate CI/CD configurations"""
    
    @staticmethod
    def generate_github_actions(project_name: str) -> str:
        """Generate GitHub Actions workflow"""
        return f"""name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          cd backend
          pytest --cov=. --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml

  frontend-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Run linter
        run: |
          cd frontend
          npm run lint
      
      - name: Run tests
        run: |
          cd frontend
          npm test -- --coverage
      
      - name: Build
        run: |
          cd frontend
          npm run build

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run security scan
        uses: snyk/actions/python@master
        env:
          SNYK_TOKEN: ${{{{ secrets.SNYK_TOKEN }}}}

  deploy:
    needs: [backend-tests, frontend-tests]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to production
        run: |
          echo "Deploying {project_name}"
          # Add deployment logic here
"""
    
    @staticmethod
    def generate_gitlab_ci(project_name: str) -> str:
        """Generate GitLab CI configuration"""
        return f"""stages:
  - test
  - build
  - deploy

variables:
  POSTGRES_DB: test_db
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: postgres

backend-test:
  stage: test
  image: python:3.11
  services:
    - postgres:15
  script:
    - cd backend
    - pip install -r requirements.txt
    - pytest --cov=.
  coverage: '/TOTAL.*\\s+(\\d+%)$/'

frontend-test:
  stage: test
  image: node:18
  script:
    - cd frontend
    - npm ci
    - npm run lint
    - npm test
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: frontend/coverage/cobertura-coverage.xml

build-backend:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - cd backend
    - docker build -t {project_name}-backend:$CI_COMMIT_SHA .
  only:
    - main

build-frontend:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - cd frontend
    - docker build -t {project_name}-frontend:$CI_COMMIT_SHA .
  only:
    - main

deploy-production:
  stage: deploy
  image: alpine:latest
  script:
    - echo "Deploying {project_name} to production"
    # Add deployment commands
  only:
    - main
  when: manual
"""
    
    @staticmethod
    def generate_docker_compose_ci() -> str:
        """Generate Docker Compose for CI"""
        return """version: '3.8'

services:
  backend-test:
    build:
      context: ./backend
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/test_db
      TESTING: "true"
    depends_on:
      - postgres
    command: pytest

  frontend-test:
    build:
      context: ./frontend
    command: npm test

  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: test_db
"""
