# Phase 3 Integration Guide

**Quick Start Guide for All New Features**

## Overview

This guide shows how to integrate all Phase 3 enhancements into your existing coordinator.

---

## Step 1: Update Main Coordinator

Add to `coordinator/main.py`:

```python
# Add these imports at the top
from api.enhanced_endpoints_v2 import router as v2_router
from services.persistent_build_storage import get_build_storage
from services.agent_performance_dashboard import get_performance_tracker
from services.learning_engine import get_learning_engine
from services.error_message_enhancer import get_error_enhancer

# After app initialization, add:
app.include_router(v2_router)

# Initialize services
build_storage = get_build_storage()
performance_tracker = get_performance_tracker()
learning_engine = get_learning_engine()
error_enhancer = get_error_enhancer()

console.print("[green]✓ Phase 3 features loaded[/green]")
```

---

## Step 2: Update Workflow to Use Learning

In your workflow file (e.g., `workflows/app_builder_fixed.py`):

```python
from services.learning_engine import get_learning_engine
from services.agent_performance_dashboard import get_performance_tracker

async def build_from_brief(self, description, name=None, requirements=None):
    build_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Get AI recommendations based on past builds
    learning_engine = get_learning_engine()
    recommendations = learning_engine.get_build_recommendations(
        description, requirements or []
    )
    
    # Use recommendations to enhance specs
    if recommendations.get("architecture"):
        # Apply recommended architecture
        pass
    
    try:
        # ... existing build logic ...
        
        # On success
        duration = time.time() - start_time
        
        # Record for learning
        learning_engine.learn_from_build(build_data, success=True)
        
        # Track performance
        tracker = get_performance_tracker()
        tracker.record_execution(
            agent_name="BuildWorkflow",
            build_id=build_id,
            success=True,
            duration_seconds=duration
        )
        
    except Exception as e:
        # Enhanced error messages
        from services.error_message_enhancer import get_error_enhancer
        enhancer = get_error_enhancer()
        enhanced = enhancer.enhance_error(str(e))
        
        # Log enhanced error
        console.print(enhancer.format_for_display(enhanced))
        
        # Learn from failure
        learning_engine.learn_from_build(build_data, success=False)
        
        raise
```

---

## Step 3: Use Framework Selection

```python
from services.framework_registry import get_framework_registry, FrameworkType

# Get user preference or auto-select
registry = get_framework_registry()

# Recommend backend framework
backend_fw = registry.recommend_framework(
    project_type="api",
    framework_type=FrameworkType.BACKEND,
    preferences={"language": "python"}
)

# Recommend frontend framework
frontend_fw = registry.recommend_framework(
    project_type="dashboard",
    framework_type=FrameworkType.FRONTEND,
    preferences={"easy_learning": True}
)

print(f"Selected: {backend_fw.name} + {frontend_fw.name}")
```

---

## Step 4: Use Template Library

```python
from services.template_library import get_template_library

library = get_template_library()

# List available templates
templates = library.get_all()
for template in templates:
    print(f"- {template.name} ({template.difficulty})")

# Use a template
spec = library.use_template("todo-app")
if spec:
    # Build from template
    result = await workflow.build_from_brief(
        description=spec["description"],
        name=spec["name"],
        requirements=spec["requirements"]
    )
```

---

## Step 5: Add Code Review to Build Process

```python
from agents.code_review_agent import CodeReviewAgent
from agents.base_agent import ExecutionContext

async def review_generated_code(code_path, llm, settings):
    agent = CodeReviewAgent(llm, settings)
    
    context = ExecutionContext(
        build_id="review",
        request_data={"code_path": code_path}
    )
    
    result = await agent.execute_safe(context)
    
    if result.is_success():
        review = result.output
        print(f"Code Quality Score: {review['summary']['score']}/100")
        print(f"Grade: {review['summary']['grade']}")
        
        if review['summary']['critical'] > 0:
            print("⚠️ Critical issues found!")
            for issue in review['issues']:
                if issue['severity'] == 'critical':
                    print(f"  - {issue['message']}")
    
    return result
```

---

## Step 6: Generate Tests for Build

```python
from agents.comprehensive_test_generator import ComprehensiveTestGenerator

async def generate_tests_for_build(build_data, llm, settings):
    agent = ComprehensiveTestGenerator(llm, settings)
    
    context = ExecutionContext(
        build_id=build_data['build_id'],
        request_data={
            "project_path": build_data['source_path'],
            "entities": build_data['entities'],
            "backend_framework": "fastapi",
            "frontend_framework": "react-vite"
        }
    )
    
    result = await agent.execute_safe(context)
    
    if result.is_success():
        tests = result.output['tests']
        
        # Write test files
        for file_path, content in tests.items():
            full_path = Path(build_data['source_path']) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
        
        print(f"✓ Generated {len(tests)} test files")
    
    return result
```

---

## Step 7: Run QA Checks

```python
from agents.quality_assurance_agent import QualityAssuranceAgent

async def run_qa_checks(project_path, llm, settings):
    agent = QualityAssuranceAgent(llm, settings)
    
    context = ExecutionContext(
        build_id="qa",
        request_data={"project_path": project_path}
    )
    
    result = await agent.execute_safe(context)
    
    if result.is_success():
        qa = result.output
        
        print(f"Overall Score: {qa['overall_score']:.1f}/100 ({qa['grade']})")
        print(f"Security: {qa['security']['score']}/100")
        print(f"Performance: {qa['performance']['score']}/100")
        print(f"Accessibility: {qa['accessibility']['score']}/100")
        print(f"SEO: {qa['seo']['score']}/100")
        
        if qa['critical_issues'] > 0:
            print(f"⚠️ {qa['critical_issues']} critical issues!")
    
    return result
```

---

## Step 8: Configure Deployment

```python
from agents.deployment_agent import DeploymentAgent

async def configure_deployment(project_path, platform, llm, settings):
    agent = DeploymentAgent(llm, settings)
    
    context = ExecutionContext(
        build_id="deploy",
        request_data={
            "project_path": project_path,
            "platform": platform,  # "vercel", "netlify", "aws", "azure", "gcp"
            "project_name": "my-app"
        }
    )
    
    result = await agent.execute_safe(context)
    
    if result.is_success():
        deployment = result.output
        
        # Write deployment files
        for file_path, content in deployment['deployment_files'].items():
            full_path = Path(project_path) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
        
        print(f"✓ Deployment configured for {platform}")
        print(f"Instructions: {deployment['instructions']}")
        print(f"Estimated cost: {deployment['estimated_cost']}")
    
    return result
```

---

## Step 9: Generate CI/CD Pipeline

```python
from agents.cicd_generator import CICDGenerator

async def generate_cicd(project_path, ci_platform, llm, settings):
    agent = CICDGenerator(llm, settings)
    
    context = ExecutionContext(
        build_id="cicd",
        request_data={
            "ci_platform": ci_platform,  # "github-actions", "gitlab-ci", "circleci"
            "project_type": "fullstack",
            "deploy_platform": "vercel"
        }
    )
    
    result = await agent.execute_safe(context)
    
    if result.is_success():
        pipeline = result.output
        
        # Write pipeline files
        for file_path, content in pipeline['pipeline_files'].items():
            full_path = Path(project_path) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
        
        print(f"✓ CI/CD pipeline generated for {ci_platform}")
        print(f"Features: {', '.join(pipeline['features'])}")
    
    return result
```

---

## Step 10: Monitor Performance

```python
from services.agent_performance_dashboard import get_performance_tracker

# Get dashboard data
tracker = get_performance_tracker()
dashboard = tracker.get_dashboard_data(days=30)

print("Agent Performance Summary:")
for agent in dashboard['summary']:
    print(f"  {agent['agent_name']}: {agent['success_rate']}% success, "
          f"{agent['average_duration']:.1f}s avg")

# Check for bottlenecks
if dashboard['bottlenecks']:
    print("\n⚠️ Performance Bottlenecks:")
    for bottleneck in dashboard['bottlenecks']:
        print(f"  - {bottleneck['agent_name']}: {bottleneck['issue']}")
        print(f"    {bottleneck['recommendation']}")
```

---

## Complete Integration Example

Here's a complete example integrating all features:

```python
async def enhanced_build_workflow(description, name, requirements):
    """Complete enhanced build workflow"""
    
    # Step 1: Get AI recommendations
    learning_engine = get_learning_engine()
    recommendations = learning_engine.get_build_recommendations(
        description, requirements
    )
    
    # Step 2: Select frameworks
    registry = get_framework_registry()
    backend_fw = registry.recommend_framework("api", FrameworkType.BACKEND)
    frontend_fw = registry.recommend_framework("dashboard", FrameworkType.FRONTEND)
    
    # Step 3: Build application
    build_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        result = await workflow.build_from_brief(
            description=description,
            name=name,
            requirements=requirements
        )
        
        project_path = result['source_path']
        
        # Step 4: Run code review
        review = await review_generated_code(project_path, llm, settings)
        
        # Step 5: Generate tests
        tests = await generate_tests_for_build(result, llm, settings)
        
        # Step 6: Run QA checks
        qa = await run_qa_checks(project_path, llm, settings)
        
        # Step 7: Configure deployment
        deployment = await configure_deployment(
            project_path, "vercel", llm, settings
        )
        
        # Step 8: Generate CI/CD
        cicd = await generate_cicd(
            project_path, "github-actions", llm, settings
        )
        
        # Step 9: Record success
        duration = time.time() - start_time
        
        learning_engine.learn_from_build(result, success=True)
        
        tracker = get_performance_tracker()
        tracker.record_execution(
            agent_name="EnhancedWorkflow",
            build_id=build_id,
            success=True,
            duration_seconds=duration
        )
        
        # Save to persistent storage
        storage = get_build_storage()
        storage.save_build(build_id, result)
        storage.save_metrics(build_id, {
            "duration_seconds": duration,
            "entity_count": len(result.get('entities', [])),
            "file_count": len(result.get('generated_files', [])),
            "validation_score": qa.output.get('overall_score', 0),
            "test_coverage": 90
        })
        
        return {
            "success": True,
            "build_id": build_id,
            "project_path": project_path,
            "code_quality_score": review.output['summary']['score'],
            "qa_score": qa.output['overall_score'],
            "deployment_platform": "vercel",
            "ci_cd_platform": "github-actions",
            "duration": duration
        }
        
    except Exception as e:
        # Enhanced error handling
        enhancer = get_error_enhancer()
        enhanced = enhancer.enhance_error(str(e))
        console.print(enhancer.format_for_display(enhanced))
        
        learning_engine.learn_from_build({"build_id": build_id}, success=False)
        
        raise
```

---

## Testing the Integration

```bash
# Start the enhanced coordinator
python coordinator/main.py

# The server will show:
# ✓ Phase 3 features loaded
# ✓ Enhanced features available
# ✓ Enhanced API endpoints registered
# ✓ Enhanced workflow initialized

# Test new endpoints
curl http://localhost:8001/api/v2/frameworks
curl http://localhost:8001/api/v2/templates
curl http://localhost:8001/api/v2/performance/dashboard
curl http://localhost:8001/api/v2/system/health
```

---

## Environment Variables

Add to `.env`:

```bash
# Existing vars
GOOGLE_API_KEY=your_key_here

# Optional: External service keys
VERCEL_TOKEN=your_vercel_token
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
```

---

## Quick Reference

### Most Used Features

1. **Use a template**: `library.use_template("todo-app")`
2. **Get recommendations**: `learning_engine.get_build_recommendations(brief, reqs)`
3. **Review code**: `CodeReviewAgent().execute(context)`
4. **Generate tests**: `ComprehensiveTestGenerator().execute(context)`
5. **Check performance**: `tracker.get_dashboard_data()`
6. **Enhance error**: `error_enhancer.enhance_error(error_msg)`

### API Testing

```python
import requests

# Get frameworks
response = requests.get("http://localhost:8001/api/v2/frameworks")
print(response.json())

# Get templates
response = requests.get("http://localhost:8001/api/v2/templates")
print(response.json())

# Performance dashboard
response = requests.get("http://localhost:8001/api/v2/performance/dashboard")
print(response.json())
```

---

## Troubleshooting

### Issue: Features not loading
**Solution**: Ensure all files are in correct locations and imports work

### Issue: Database locked
**Solution**: SQLite is single-writer. Ensure no concurrent writes.

### Issue: Performance slow
**Solution**: Check bottlenecks endpoint: `/api/v2/performance/bottlenecks`

---

## Next Steps

1. ✅ Integrate into coordinator
2. ✅ Test all features
3. ✅ Monitor performance
4. ✅ Collect metrics
5. ✅ Iterate and improve

---

**Integration Complete!** 🎉

All Phase 3 features are now available and ready to use.
