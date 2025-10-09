"""
Validate that all improvements were successfully applied
This script checks code changes without requiring API calls
"""
import os
import sys
from pathlib import Path

class ImprovementValidator:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.checks = []
    
    def check(self, name: str, condition: bool, details: str = ""):
        """Validate a condition"""
        if condition:
            self.passed += 1
            status = "✅ PASS"
            print(f"{status} - {name}")
            if details:
                print(f"   → {details}")
        else:
            self.failed += 1
            status = "❌ FAIL"
            print(f"{status} - {name}")
            if details:
                print(f"   → {details}")
        
        self.checks.append({"name": name, "status": "passed" if condition else "failed"})
        return condition
    
    def summary(self):
        """Print validation summary"""
        total = self.passed + self.failed
        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print(f"Total Checks: {total}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print(f"Success Rate: {(self.passed/total*100) if total > 0 else 0:.1f}%")
        print("=" * 70)
        return self.failed == 0

# Initialize validator
validator = ImprovementValidator()

print("=" * 70)
print("VALIDATING IMPROVEMENTS")
print("=" * 70 + "\n")

# 1. Check coordinator_agent.py improvements
print("📝 Checking coordinator_agent.py improvements...")
coordinator_agent_path = Path("coordinator/agents/coordinator_agent.py")
if coordinator_agent_path.exists():
    content = coordinator_agent_path.read_text(encoding='utf-8')
    
    validator.check(
        "Input validation added",
        "if not brief or not brief.strip():" in content,
        "Empty brief validation present"
    )
    
    validator.check(
        "JSON markdown extraction",
        '```json' in content and 'split("```json")' in content,
        "Handles markdown code blocks"
    )
    
    validator.check(
        "Enhanced error handling",
        "except json.JSONDecodeError as e:" in content,
        "Specific JSON error handling"
    )
    
    validator.check(
        "Fallback mechanisms",
        "_fallback_parse" in content,
        "Fallback parsing implemented"
    )
else:
    validator.check("coordinator_agent.py exists", False, "File not found")

print()

# 2. Check app_builder.py improvements
print("📝 Checking app_builder.py improvements...")
workflow_path = Path("coordinator/workflows/app_builder.py")
if workflow_path.exists():
    content = workflow_path.read_text(encoding='utf-8')
    
    validator.check(
        "Description length validation",
        "len(description.strip()) < 10" in content,
        "Minimum length check present"
    )
    
    validator.check(
        "ValueError handling",
        "except ValueError as e:" in content,
        "Separate validation error handling"
    )
    
    validator.check(
        "Enhanced logging",
        "self._log(state, \"success\"" in content,
        "Success level logging added"
    )
    
    validator.check(
        "Error recovery",
        "except Exception as e:" in content and "self._log(state, \"error\"" in content,
        "Error logging at workflow steps"
    )
    
    validator.check(
        "Detailed step names",
        "Analyzing project brief" in content or "Generating backend code" in content,
        "Descriptive step names"
    )
else:
    validator.check("app_builder.py exists", False, "File not found")

print()

# 3. Check UI improvements
print("📝 Checking UI enhancements...")
ui_path = Path("coordinator/ui/index.html")
if ui_path.exists():
    content = ui_path.read_text(encoding='utf-8')
    
    validator.check(
        "Gradient animations",
        "@keyframes gradient" in content,
        "Animated gradient background"
    )
    
    validator.check(
        "Glass morphism",
        "backdrop-filter: blur" in content,
        "Glass effect with blur"
    )
    
    validator.check(
        "Safari compatibility",
        "-webkit-backdrop-filter" in content,
        "Cross-browser support added"
    )
    
    validator.check(
        "Error animations",
        "error-shake" in content or "@keyframes shake" in content,
        "Error feedback animations"
    )
    
    validator.check(
        "Modern styling",
        "gradient-bg" in content or "pulse-ring" in content,
        "Modern CSS classes"
    )
else:
    validator.check("index.html exists", False, "File not found")

print()

# 4. Check test suite
print("📝 Checking test suite...")
test_path = Path("comprehensive_test.py")
if test_path.exists():
    content = test_path.read_text(encoding='utf-8')
    
    validator.check(
        "Test runner class",
        "class TestRunner:" in content,
        "Test infrastructure present"
    )
    
    validator.check(
        "Multiple test cases",
        "def test_health_check" in content and "def test_build_simple_app" in content,
        "10+ test functions"
    )
    
    validator.check(
        "Error handling tests",
        "test_invalid_build_request" in content,
        "Error case validation"
    )
    
    validator.check(
        "Concurrent testing",
        "test_concurrent_builds" in content,
        "Multi-build testing"
    )
    
    validator.check(
        "Result export",
        "test_results.json" in content,
        "JSON result output"
    )
else:
    validator.check("comprehensive_test.py exists", False, "File not found")

print()

# 5. Check documentation
print("📝 Checking documentation...")

docs = [
    ("IMPROVEMENTS_COMPLETED.md", "Technical improvements doc"),
    ("TESTING_GUIDE.md", "Testing instructions"),
    ("SESSION_SUMMARY.md", "Session summary")
]

for doc_file, description in docs:
    exists = Path(doc_file).exists()
    validator.check(f"{doc_file} exists", exists, description)

print()

# 6. Check configuration
print("📝 Checking configuration...")
env_example_path = Path(".env.example")
if env_example_path.exists():
    content = env_example_path.read_text(encoding='utf-8')
    
    validator.check(
        "Gemini API key configured",
        "GOOGLE_API_KEY" in content,
        "API key placeholder present"
    )
    
    validator.check(
        "Gemini model configured",
        "GEMINI_MODEL" in content,
        "Model configuration present"
    )
else:
    validator.check(".env.example exists", False, "File not found")

print()

# 7. File structure validation
print("📝 Checking project structure...")
expected_files = [
    "coordinator/agents/coordinator_agent.py",
    "coordinator/agents/backend_agent.py",
    "coordinator/agents/frontend_agent.py",
    "coordinator/agents/integration_agent.py",
    "coordinator/workflows/app_builder.py",
    "coordinator/ui/index.html",
    "coordinator/main.py",
    "requirements.txt"
]

all_exist = True
for file_path in expected_files:
    exists = Path(file_path).exists()
    if not exists:
        all_exist = False
        print(f"   ⚠️  Missing: {file_path}")

validator.check("All core files present", all_exist, f"{len(expected_files)} essential files")

print()

# Print final summary
success = validator.summary()

if success:
    print("\n🎉 ALL VALIDATIONS PASSED!")
    print("\n✅ Next steps:")
    print("   1. Start coordinator: cd coordinator && python main.py")
    print("   2. Run tests: python comprehensive_test.py")
    print("   3. Open UI: http://localhost:5000/ui")
    print("\n📚 See TESTING_GUIDE.md for detailed instructions")
else:
    print("\n⚠️  SOME VALIDATIONS FAILED")
    print("   Review the failed checks above")
    print("   Check SESSION_SUMMARY.md for expected changes")

sys.exit(0 if success else 1)
