"""
Phase 1 Validation Script

Validates that all Phase 1 components are properly implemented and accessible.
This script performs static validation without running the coordinator.
"""

import sys
from pathlib import Path
from importlib import import_module


def check_file_exists(filepath: str) -> bool:
    """Check if a file exists"""
    return Path(filepath).exists()


def check_module_imports(module_path: str, expected_exports: list) -> bool:
    """Check if module can be imported and has expected exports"""
    try:
        parts = module_path.split('.')
        if 'coordinator' in parts:
            # Add coordinator to path
            coordinator_dir = Path(__file__).parent / 'coordinator'
            if str(coordinator_dir) not in sys.path:
                sys.path.insert(0, str(coordinator_dir))
        
        module = import_module(module_path)
        
        for export in expected_exports:
            if not hasattr(module, export):
                print(f"  ❌ Missing export: {export}")
                return False
        
        return True
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return False


def main():
    """Run validation checks"""
    print("="*60)
    print("PHASE 1 VALIDATION")
    print("="*60)
    
    total_checks = 0
    passed_checks = 0
    
    # 1. Check service files exist
    print("\n📁 Checking service files...")
    service_files = [
        "coordinator/services/__init__.py",
        "coordinator/services/repository_detector.py",
        "coordinator/services/sandbox_orchestrator.py",
        "coordinator/services/session_manager.py",
        "coordinator/services/audit_logger.py",
    ]
    
    for filepath in service_files:
        total_checks += 1
        if check_file_exists(filepath):
            print(f"  ✅ {filepath}")
            passed_checks += 1
        else:
            print(f"  ❌ Missing: {filepath}")
    
    # 2. Check test files exist
    print("\n🧪 Checking test files...")
    test_files = [
        "tests/api/test_sandbox_api.py",
        "tests/conftest.py",
    ]
    
    for filepath in test_files:
        total_checks += 1
        if check_file_exists(filepath):
            print(f"  ✅ {filepath}")
            passed_checks += 1
        else:
            print(f"  ❌ Missing: {filepath}")
    
    # 3. Check documentation files exist
    print("\n📚 Checking documentation...")
    doc_files = [
        "docs/phase1_sandbox_orchestration.md",
        "PHASE1_SUMMARY.md",
        "examples/phase1_demo.py",
    ]
    
    for filepath in doc_files:
        total_checks += 1
        if check_file_exists(filepath):
            print(f"  ✅ {filepath}")
            passed_checks += 1
        else:
            print(f"  ❌ Missing: {filepath}")
    
    # 4. Check module imports
    print("\n🔌 Checking module imports...")
    
    modules_to_check = [
        ("services.repository_detector", ["RepositoryDetector"]),
        ("services.sandbox_orchestrator", ["SandboxOrchestrator"]),
        ("services.session_manager", ["SessionManager"]),
        ("services.audit_logger", ["AuditLogger", "AuditEventType", "audit_logger"]),
    ]
    
    for module_path, exports in modules_to_check:
        total_checks += 1
        print(f"\n  Checking {module_path}...")
        if check_module_imports(module_path, exports):
            print(f"  ✅ {module_path} - all exports present")
            passed_checks += 1
        else:
            print(f"  ❌ {module_path} - validation failed")
    
    # 5. Check main.py has new endpoints
    print("\n🌐 Checking API endpoints in main.py...")
    
    main_file = Path("coordinator/main.py")
    if main_file.exists():
        content = main_file.read_text(encoding='utf-8')
        
        endpoints = [
            "/api/repo/detect",
            "/api/app/preview",
            "/api/app/launch",
            "/api/app/stop",
            "/api/app/download",
            "/api/sandbox/instances",
            "/api/sandbox/health",
            "/api/sessions/stats",
            "/api/audit/recent",
            "/api/audit/stats",
        ]
        
        for endpoint in endpoints:
            total_checks += 1
            if endpoint in content:
                print(f"  ✅ {endpoint}")
                passed_checks += 1
            else:
                print(f"  ❌ Missing endpoint: {endpoint}")
    else:
        print("  ❌ coordinator/main.py not found")
        total_checks += 1
    
    # 6. Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    
    print(f"\n✅ Passed: {passed_checks}/{total_checks} ({success_rate:.1f}%)")
    
    if passed_checks == total_checks:
        print("\n🎉 ALL CHECKS PASSED - Phase 1 implementation is complete!")
        print("\nNext steps:")
        print("  1. Start coordinator: python coordinator/main.py")
        print("  2. Run tests: pytest tests/api/test_sandbox_api.py -v")
        print("  3. Run demo: python examples/phase1_demo.py ./generated/my-app")
        print("  4. Read docs: docs/phase1_sandbox_orchestration.md")
        return 0
    else:
        print(f"\n⚠️  {total_checks - passed_checks} checks failed")
        print("Please review the errors above and fix missing components.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
