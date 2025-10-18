"""
Deployment Agent - Multi-cloud deployment support
Phase 3C.1 from analysis
"""
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from agents.base_agent import BaseAgent, ExecutionContext, ExecutionResult, AgentStatus, AgentCapability


class DeploymentAgent(BaseAgent):
    """
    Handles deployment to multiple platforms:
    - Vercel/Netlify (Frontend)
    - AWS (ECS, Lambda, RDS)
    - Azure (App Service, Container Instances)
    - Google Cloud (Cloud Run, Cloud SQL)
    """
    
    def get_capabilities(self) -> List[AgentCapability]:
        return [AgentCapability.CODE_GENERATION, AgentCapability.INTEGRATION]
    
    def validate_input(self, request_data: Dict) -> Tuple[bool, Optional[str]]:
        if "project_path" not in request_data:
            return False, "project_path is required"
        if "platform" not in request_data:
            return False, "platform is required"
        return True, None
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """Generate deployment configuration"""
        project_path = Path(context.request_data["project_path"])
        platform = context.request_data["platform"]
        project_name = context.request_data.get("project_name", "app")
        
        deployment_files = {}
        
        if platform == "vercel":
            deployment_files = self._generate_vercel_config(project_name)
        elif platform == "netlify":
            deployment_files = self._generate_netlify_config(project_name)
        elif platform == "aws":
            deployment_files = self._generate_aws_config(project_name)
        elif platform == "azure":
            deployment_files = self._generate_azure_config(project_name)
        elif platform == "gcp":
            deployment_files = self._generate_gcp_config(project_name)
        else:
            return ExecutionResult(
                status=AgentStatus.FAILED,
                output=None,
                errors=[f"Unsupported platform: {platform}"]
            )
        
        return ExecutionResult(
            status=AgentStatus.COMPLETED,
            output={
                "deployment_files": deployment_files,
                "platform": platform,
                "instructions": self._get_deployment_instructions(platform),
                "estimated_cost": self._estimate_cost(platform)
            },
            metadata={
                "platform": platform,
                "files_generated": len(deployment_files)
            }
        )
    
    def _generate_vercel_config(self, project_name: str) -> Dict[str, str]:
        """Generate Vercel deployment config"""
        return {
            "vercel.json": '''{
  "version": 2,
  "builds": [
    {
      "src": "package.json",
      "use": "@vercel/static-build",
      "config": {
        "distDir": "dist"
      }
    }
  ],
  "routes": [
    {
      "handle": "filesystem"
    },
    {
      "src": "/(.*)",
      "dest": "/index.html"
    }
  ],
  "env": {
    "NEXT_PUBLIC_API_URL": "@api-url"
  }
}''',
            ".vercelignore": '''node_modules
.env.local
.env
*.log
''',
            "README_DEPLOY.md": '''# Deploying to Vercel

## Prerequisites
- Vercel account
- Vercel CLI: `npm i -g vercel`

## Steps
1. Login: `vercel login`
2. Deploy: `vercel --prod`
3. Set environment variables in Vercel dashboard

## Environment Variables
- NEXT_PUBLIC_API_URL: Your backend API URL

## Automatic Deployments
Connect your GitHub repository for automatic deployments on push.
'''
        }
    
    def _generate_netlify_config(self, project_name: str) -> Dict[str, str]:
        """Generate Netlify deployment config"""
        return {
            "netlify.toml": '''[build]
  command = "npm run build"
  publish = "dist"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[build.environment]
  NODE_VERSION = "18"

[[plugins]]
  package = "@netlify/plugin-sitemap"
''',
            ".netlifyignore": '''node_modules
.env.local
.env
*.log
''',
            "README_DEPLOY.md": '''# Deploying to Netlify

## Prerequisites
- Netlify account
- Netlify CLI: `npm i -g netlify-cli`

## Steps
1. Login: `netlify login`
2. Initialize: `netlify init`
3. Deploy: `netlify deploy --prod`

## Environment Variables
Set in Netlify dashboard under Site settings > Environment variables

## Automatic Deployments
Connect your Git repository for continuous deployment.
'''
        }
    
    def _generate_aws_config(self, project_name: str) -> Dict[str, str]:
        """Generate AWS deployment config"""
        return {
            "aws/ecs-task-definition.json": f'''{{
  "family": "{project_name}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {{
      "name": "{project_name}-backend",
      "image": "{project_name}:latest",
      "portMappings": [
        {{
          "containerPort": 8000,
          "protocol": "tcp"
        }}
      ],
      "environment": [
        {{
          "name": "DATABASE_URL",
          "value": "postgresql://user:pass@db:5432/dbname"
        }}
      ],
      "logConfiguration": {{
        "logDriver": "awslogs",
        "options": {{
          "awslogs-group": "/ecs/{project_name}",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }}
      }}
    }}
  ]
}}''',
            "aws/cloudformation.yaml": f'''AWSTemplateFormatVersion: '2010-09-09'
Description: '{project_name} infrastructure'

Parameters:
  DBPassword:
    Type: String
    NoEcho: true
    Description: Database password

Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      Tags:
        - Key: Name
          Value: {project_name}-vpc

  Database:
    Type: AWS::RDS::DBInstance
    Properties:
      DBInstanceIdentifier: {project_name}-db
      Engine: postgres
      EngineVersion: '15.0'
      DBInstanceClass: db.t3.micro
      AllocatedStorage: 20
      MasterUsername: admin
      MasterUserPassword: !Ref DBPassword
      VPCSecurityGroups:
        - !Ref DBSecurityGroup

  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: {project_name}-cluster

  LoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Name: {project_name}-alb
      Subnets:
        - !Ref PublicSubnet1
        - !Ref PublicSubnet2
      SecurityGroups:
        - !Ref ALBSecurityGroup
''',
            "aws/deploy.sh": '''#!/bin/bash
set -e

PROJECT_NAME="${1:-app}"
AWS_REGION="${2:-us-east-1}"

echo "Deploying to AWS..."

# Build and push Docker image
docker build -t $PROJECT_NAME:latest .
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com
docker tag $PROJECT_NAME:latest $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME:latest
docker push $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME:latest

# Deploy CloudFormation stack
aws cloudformation deploy \\
  --template-file aws/cloudformation.yaml \\
  --stack-name $PROJECT_NAME-stack \\
  --parameter-overrides DBPassword=$DB_PASSWORD \\
  --capabilities CAPABILITY_IAM \\
  --region $AWS_REGION

# Update ECS service
aws ecs update-service \\
  --cluster $PROJECT_NAME-cluster \\
  --service $PROJECT_NAME-service \\
  --force-new-deployment \\
  --region $AWS_REGION

echo "Deployment complete!"
''',
            "README_AWS_DEPLOY.md": '''# AWS Deployment Guide

## Prerequisites
- AWS CLI configured
- Docker installed
- AWS account with appropriate permissions

## Infrastructure
- ECS Fargate for container hosting
- RDS PostgreSQL for database
- Application Load Balancer
- CloudWatch for logging

## Deployment Steps
1. Set environment variables:
   ```bash
   export DB_PASSWORD=your-secure-password
   ```

2. Deploy infrastructure:
   ```bash
   chmod +x aws/deploy.sh
   ./aws/deploy.sh your-app-name us-east-1
   ```

3. Get ALB DNS:
   ```bash
   aws elbv2 describe-load-balancers --names your-app-name-alb
   ```

## Costs
Estimated monthly cost: $30-100 (t3.micro instances)
'''
        }
    
    def _generate_azure_config(self, project_name: str) -> Dict[str, str]:
        """Generate Azure deployment config"""
        return {
            "azure/app-service.bicep": f'''param location string = resourceGroup().location
param appName string = '{project_name}'

resource appServicePlan 'Microsoft.Web/serverfarms@2021-02-01' = {{
  name: '${{appName}}-plan'
  location: location
  sku: {{
    name: 'B1'
    tier: 'Basic'
  }}
  kind: 'linux'
  properties: {{
    reserved: true
  }}
}}

resource webApp 'Microsoft.Web/sites@2021-02-01' = {{
  name: '${{appName}}-app'
  location: location
  properties: {{
    serverFarmId: appServicePlan.id
    siteConfig: {{
      linuxFxVersion: 'DOCKER|{project_name}:latest'
      appSettings: [
        {{
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }}
      ]
    }}
  }}
}}

resource database 'Microsoft.DBforPostgreSQL/servers@2017-12-01' = {{
  name: '${{appName}}-db'
  location: location
  sku: {{
    name: 'B_Gen5_1'
    tier: 'Basic'
  }}
  properties: {{
    version: '11'
    administratorLogin: 'dbadmin'
    administratorLoginPassword: 'SecurePassword123!'
  }}
}}
''',
            "azure/deploy.sh": '''#!/bin/bash
set -e

RESOURCE_GROUP="${1:-app-rg}"
LOCATION="${2:-eastus}"

az group create --name $RESOURCE_GROUP --location $LOCATION

az deployment group create \\
  --resource-group $RESOURCE_GROUP \\
  --template-file azure/app-service.bicep

echo "Deployment complete!"
''',
            "README_AZURE_DEPLOY.md": '''# Azure Deployment Guide

## Prerequisites
- Azure CLI installed and logged in
- Docker installed

## Deploy
```bash
chmod +x azure/deploy.sh
./azure/deploy.sh my-resource-group eastus
```

## Cost
Estimated: $15-50/month (Basic tier)
'''
        }
    
    def _generate_gcp_config(self, project_name: str) -> Dict[str, str]:
        """Generate Google Cloud deployment config"""
        return {
            "gcp/cloudrun.yaml": f'''apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: {project_name}
spec:
  template:
    spec:
      containers:
      - image: gcr.io/PROJECT_ID/{project_name}
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          value: postgresql://user:pass@/dbname?host=/cloudsql/PROJECT_ID:REGION:INSTANCE
''',
            "gcp/deploy.sh": '''#!/bin/bash
set -e

PROJECT_ID="${1}"
SERVICE_NAME="${2:-app}"
REGION="${3:-us-central1}"

# Build container
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \\
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \\
  --platform managed \\
  --region $REGION \\
  --allow-unauthenticated

echo "Deployment complete!"
gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)'
''',
            "README_GCP_DEPLOY.md": '''# Google Cloud Deployment

## Prerequisites
- gcloud CLI installed
- GCP project created

## Deploy
```bash
chmod +x gcp/deploy.sh
./gcp/deploy.sh your-project-id app-name us-central1
```

## Cost
Estimated: $5-30/month (Cloud Run with minimal traffic)
'''
        }
    
    def _get_deployment_instructions(self, platform: str) -> str:
        """Get platform-specific instructions"""
        instructions = {
            "vercel": "Run 'vercel --prod' to deploy",
            "netlify": "Run 'netlify deploy --prod' to deploy",
            "aws": "Run './aws/deploy.sh' to deploy to AWS ECS",
            "azure": "Run './azure/deploy.sh' to deploy to Azure",
            "gcp": "Run './gcp/deploy.sh PROJECT_ID' to deploy to Google Cloud Run"
        }
        return instructions.get(platform, "Check README_DEPLOY.md for instructions")
    
    def _estimate_cost(self, platform: str) -> str:
        """Estimate monthly cost"""
        costs = {
            "vercel": "Free tier available, Pro: $20/month",
            "netlify": "Free tier available, Pro: $19/month",
            "aws": "$30-100/month (t3.micro instances + RDS)",
            "azure": "$15-50/month (Basic tier)",
            "gcp": "$5-30/month (Cloud Run minimal traffic)"
        }
        return costs.get(platform, "Varies by usage")
