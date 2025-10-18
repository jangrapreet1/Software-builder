"""
CI/CD Pipeline Generator - Generate CI/CD configurations
Phase 3C.2 from analysis
"""
from typing import Dict, List, Optional, Tuple

from agents.base_agent import BaseAgent, ExecutionContext, ExecutionResult, AgentStatus, AgentCapability


class CICDGenerator(BaseAgent):
    """
    Generates CI/CD pipeline configurations for:
    - GitHub Actions
    - GitLab CI
    - CircleCI
    - Jenkins
    """
    
    def get_capabilities(self) -> List[AgentCapability]:
        return [AgentCapability.CODE_GENERATION, AgentCapability.INTEGRATION]
    
    def validate_input(self, request_data: Dict) -> Tuple[bool, Optional[str]]:
        if "ci_platform" not in request_data:
            return False, "ci_platform is required"
        return True, None
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """Generate CI/CD pipeline configuration"""
        ci_platform = context.request_data["ci_platform"]
        project_type = context.request_data.get("project_type", "fullstack")
        deploy_platform = context.request_data.get("deploy_platform", "")
        
        pipeline_files = {}
        
        if ci_platform == "github-actions":
            pipeline_files = self._generate_github_actions(project_type, deploy_platform)
        elif ci_platform == "gitlab-ci":
            pipeline_files = self._generate_gitlab_ci(project_type, deploy_platform)
        elif ci_platform == "circleci":
            pipeline_files = self._generate_circleci(project_type, deploy_platform)
        else:
            return ExecutionResult(
                status=AgentStatus.FAILED,
                output=None,
                errors=[f"Unsupported CI platform: {ci_platform}"]
            )
        
        return ExecutionResult(
            status=AgentStatus.COMPLETED,
            output={
                "pipeline_files": pipeline_files,
                "platform": ci_platform,
                "features": [
                    "Automated testing",
                    "Code quality checks",
                    "Security scanning",
                    "Automated deployment",
                    "Build caching"
                ]
            },
            metadata={
                "platform": ci_platform,
                "files_generated": len(pipeline_files)
            }
        )
    
    def _generate_github_actions(self, project_type: str, deploy_platform: str) -> Dict[str, str]:
        """Generate GitHub Actions workflows"""
        workflows = {}
        
        # CI workflow
        workflows[".github/workflows/ci.yml"] = f'''name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        cache: 'pip'
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
    
    - name: Run linting
      run: |
        cd backend
        pip install black isort flake8
        black --check .
        isort --check-only .
        flake8 .
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/testdb
      run: |
        cd backend
        pytest --cov=. --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml
  
  frontend-test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: frontend/package-lock.json
    
    - name: Install dependencies
      run: |
        cd frontend
        npm ci
    
    - name: Run linting
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
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'
'''
        
        # CD workflow
        if deploy_platform:
            workflows[".github/workflows/cd.yml"] = self._generate_cd_workflow(deploy_platform)
        
        # Dependabot config
        workflows[".github/dependabot.yml"] = '''version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
  
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
  
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
'''
        
        return workflows
    
    def _generate_cd_workflow(self, deploy_platform: str) -> str:
        """Generate CD workflow based on deployment platform"""
        
        if deploy_platform == "vercel":
            return '''name: Deploy to Vercel

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to Vercel
      uses: amondnet/vercel-action@v25
      with:
        vercel-token: ${{ secrets.VERCEL_TOKEN }}
        vercel-org-id: ${{ secrets.ORG_ID }}
        vercel-project-id: ${{ secrets.PROJECT_ID }}
        vercel-args: '--prod'
'''
        
        elif deploy_platform == "aws":
            return '''name: Deploy to AWS

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1
    
    - name: Build and push Docker image
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: app
        IMAGE_TAG: ${{ github.sha }}
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
    
    - name: Deploy to ECS
      run: |
        aws ecs update-service --cluster app-cluster --service app-service --force-new-deployment
'''
        
        else:
            return '''name: Deploy

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy
      run: echo "Configure deployment for your platform"
'''
    
    def _generate_gitlab_ci(self, project_type: str, deploy_platform: str) -> Dict[str, str]:
        """Generate GitLab CI configuration"""
        return {
            ".gitlab-ci.yml": f'''stages:
  - test
  - security
  - build
  - deploy

variables:
  POSTGRES_DB: testdb
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: postgres

backend-test:
  stage: test
  image: python:3.11
  
  services:
    - postgres:15
  
  variables:
    DATABASE_URL: postgresql://postgres:postgres@postgres:5432/testdb
  
  before_script:
    - cd backend
    - pip install -r requirements.txt
  
  script:
    - black --check .
    - isort --check-only .
    - flake8 .
    - pytest --cov=. --cov-report=xml
  
  coverage: '/(?i)total.*? (100(?:\\.0+)?\\%|[1-9]?\\d(?:\\.\\d+)?\\%)$/'
  
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: backend/coverage.xml

frontend-test:
  stage: test
  image: node:18
  
  before_script:
    - cd frontend
    - npm ci
  
  script:
    - npm run lint
    - npm test -- --coverage
    - npm run build
  
  artifacts:
    paths:
      - frontend/dist

security-scan:
  stage: security
  image: aquasec/trivy:latest
  
  script:
    - trivy fs --format json --output trivy-report.json .
  
  artifacts:
    reports:
      container_scanning: trivy-report.json

{"deploy" if deploy_platform else "# Add deployment stage"}:
  stage: deploy
  script:
    - echo "Add deployment commands"
  only:
    - main
'''
        }
    
    def _generate_circleci(self, project_type: str, deploy_platform: str) -> Dict[str, str]:
        """Generate CircleCI configuration"""
        return {
            ".circleci/config.yml": f'''version: 2.1

orbs:
  node: circleci/node@5.0
  python: circleci/python@2.0

jobs:
  backend-test:
    docker:
      - image: cimg/python:3.11
      - image: cimg/postgres:15.0
        environment:
          POSTGRES_DB: testdb
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
    
    steps:
      - checkout
      
      - restore_cache:
          keys:
            - v1-backend-deps-{{{{ checksum "backend/requirements.txt" }}}}
      
      - run:
          name: Install dependencies
          command: |
            cd backend
            pip install -r requirements.txt
      
      - save_cache:
          key: v1-backend-deps-{{{{ checksum "backend/requirements.txt" }}}}
          paths:
            - ~/.cache/pip
      
      - run:
          name: Run tests
          command: |
            cd backend
            pytest --cov=. --cov-report=xml
      
      - store_test_results:
          path: backend/test-results
      
      - store_artifacts:
          path: backend/coverage.xml

  frontend-test:
    docker:
      - image: cimg/node:18.0
    
    steps:
      - checkout
      
      - node/install-packages:
          pkg-manager: npm
          app-dir: frontend
      
      - run:
          name: Run linting
          command: cd frontend && npm run lint
      
      - run:
          name: Run tests
          command: cd frontend && npm test
      
      - run:
          name: Build
          command: cd frontend && npm run build
      
      - store_artifacts:
          path: frontend/dist

workflows:
  test-and-deploy:
    jobs:
      - backend-test
      - frontend-test
      {"- deploy:" if deploy_platform else "# Add deployment job"}
          requires:
            - backend-test
            - frontend-test
          filters:
            branches:
              only: main
'''
        }
