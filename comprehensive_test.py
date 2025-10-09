"""
Comprehensive end-to-end testing for the Autonomous App Builder
Tests Gemini integration, error handling, and all features
"""
import os
import requests
import time
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests_run = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        symbols = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️",
            "TEST": "🧪"
        }
        symbol = symbols.get(level, "•")
        print(f"[{timestamp}] {symbol} {message}")
    
    def test(self, name: str, func):
        """Run a test function"""
        self.log(f"Running: {name}", "TEST")
        try:
            result = func()
            if result:
                self.passed += 1
                self.log(f"PASSED: {name}", "SUCCESS")
                self.tests_run.append({"name": name, "status": "passed"})
                return True
            else:
                self.failed += 1
                self.log(f"FAILED: {name}", "ERROR")
                self.tests_run.append({"name": name, "status": "failed"})
                return False
        except Exception as e:
            self.failed += 1
            self.log(f"FAILED: {name} - {str(e)}", "ERROR")
            self.tests_run.append({"name": name, "status": "error", "error": str(e)})
            return False
    
    def summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print(f"Success Rate: {(self.passed/total*100) if total > 0 else 0:.1f}%")
        print("=" * 70 + "\n")

# Initialize test runner
runner = TestRunner()

# Test 1: API Health Check
def test_health_check():
    """Test if the API is running and healthy"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200 and response.json().get("status") == "healthy"
    except Exception as e:
        runner.log(f"Health check failed: {e}", "ERROR")
        return False

# Test 2: API Root Endpoint
def test_root_endpoint():
    """Test the root endpoint"""
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        data = response.json()
        return response.status_code == 200 and "service" in data
    except:
        return False

# Test 3: Build Simple App
def test_build_simple_app():
    """Test building a simple application"""
    try:
        response = requests.post(
            f"{API_URL}/api/build",
            json={
                "description": "Build a simple notes app with add and delete features",
                "name": "test-notes-app"
            },
            timeout=10
        )
        
        if response.status_code != 200:
            runner.log(f"Build request failed with status {response.status_code}", "ERROR")
            return False
        
        data = response.json()
        build_id = data.get("build_id")
        
        if not build_id:
            runner.log("No build_id returned", "ERROR")
            return False
        
        runner.log(f"Build started: {build_id}", "INFO")
        
        # Monitor build for up to 3 minutes
        for i in range(90):
            time.sleep(2)
            status_response = requests.get(f"{API_URL}/api/build/{build_id}/status", timeout=5)
            
            if status_response.status_code != 200:
                continue
            
            status = status_response.json()
            build_status = status.get("status")
            progress = status.get("progress", 0)
            current_step = status.get("current_step", "Processing...")
            
            if i % 5 == 0:  # Log every 10 seconds
                runner.log(f"Progress: {progress}% - {current_step}", "INFO")
            
            if build_status == "success":
                runner.log(f"Build completed successfully in {i*2} seconds", "SUCCESS")
                return True
            elif build_status == "failed":
                logs = status.get("logs", [])
                if logs:
                    runner.log(f"Build failed. Last log: {logs[-1].get('message', 'Unknown error')}", "ERROR")
                return False
        
        runner.log("Build timed out after 3 minutes", "WARNING")
        return False
        
    except Exception as e:
        runner.log(f"Build test exception: {e}", "ERROR")
        return False

# Test 4: List Builds
def test_list_builds():
    """Test listing all builds"""
    try:
        response = requests.get(f"{API_URL}/api/builds", timeout=5)
        data = response.json()
        return response.status_code == 200 and "builds" in data
    except:
        return False

# Test 5: Invalid Build Request
def test_invalid_build_request():
    """Test error handling for invalid build requests"""
    try:
        response = requests.post(
            f"{API_URL}/api/build",
            json={"description": ""},  # Empty description
            timeout=5
        )
        # Should fail validation
        return response.status_code in [400, 422, 500]
    except:
        return False

# Test 6: Get Non-existent Build Status
def test_nonexistent_build():
    """Test getting status of non-existent build"""
    try:
        response = requests.get(f"{API_URL}/api/build/nonexistent-id/status", timeout=5)
        return response.status_code == 404
    except:
        return False

# Test 7: Build with Custom Name
def test_build_with_custom_name():
    """Test building with custom project name"""
    try:
        response = requests.post(
            f"{API_URL}/api/build",
            json={
                "description": "Simple todo app",
                "name": "custom-todo-app"
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return False
        
        data = response.json()
        return "build_id" in data
    except:
        return False

# Test 8: Build with Requirements
def test_build_with_requirements():
    """Test building with additional requirements"""
    try:
        response = requests.post(
            f"{API_URL}/api/build",
            json={
                "description": "Task management app",
                "name": "task-app-req",
                "requirements": ["user authentication", "email notifications"]
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return False
        
        data = response.json()
        return "build_id" in data
    except:
        return False

# Test 9: Concurrent Build Requests
def test_concurrent_builds():
    """Test handling multiple concurrent build requests"""
    try:
        # Start two builds concurrently
        import concurrent.futures
        
        def start_build(name):
            response = requests.post(
                f"{API_URL}/api/build",
                json={
                    "description": f"Simple app {name}",
                    "name": f"concurrent-{name}"
                },
                timeout=10
            )
            return response.status_code == 200
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(start_build, "1")
            future2 = executor.submit(start_build, "2")
            
            result1 = future1.result()
            result2 = future2.result()
            
        return result1 and result2
    except:
        return False

# Test 10: API Response Time
def test_api_response_time():
    """Test API response time"""
    try:
        start_time = time.time()
        response = requests.get(f"{API_URL}/health", timeout=5)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to ms
        runner.log(f"API response time: {response_time:.2f}ms", "INFO")
        
        return response.status_code == 200 and response_time < 1000  # Under 1 second
    except:
        return False

# Main execution
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("COMPREHENSIVE TEST SUITE - AUTONOMOUS APP BUILDER")
    print("Testing Gemini Integration & Error Handling")
    print("=" * 70 + "\n")
    
    runner.log("Starting test suite...", "INFO")
    runner.log(f"API URL: {API_URL}", "INFO")
    print()
    
    # Run all tests
    runner.test("API Health Check", test_health_check)
    runner.test("Root Endpoint", test_root_endpoint)
    runner.test("API Response Time", test_api_response_time)
    runner.test("List Builds", test_list_builds)
    runner.test("Invalid Build Request", test_invalid_build_request)
    runner.test("Non-existent Build Status", test_nonexistent_build)
    runner.test("Build with Custom Name", test_build_with_custom_name)
    runner.test("Build with Requirements", test_build_with_requirements)
    runner.test("Concurrent Builds", test_concurrent_builds)
    
    # Run the main build test last (takes longest)
    runner.log("\nRunning main build test (this may take 2-3 minutes)...", "INFO")
    runner.test("Build Simple App End-to-End", test_build_simple_app)
    
    # Print summary
    runner.summary()
    
    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "total": runner.passed + runner.failed,
        "passed": runner.passed,
        "failed": runner.failed,
        "tests": runner.tests_run
    }
    
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    runner.log("Test results saved to test_results.json", "SUCCESS")
    
    # Exit with appropriate code
    sys.exit(0 if runner.failed == 0 else 1)
