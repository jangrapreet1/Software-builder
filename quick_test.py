"""
Quick test of the platform with Gemini Flash
"""
import os
import requests
import time

API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")

print("=" * 70)
print("🚀 Testing Autonomous App Builder with Gemini Flash Latest")
print("=" * 70)

# Test 1: Health Check
print("\n✓ Step 1: Health Check")
response = requests.get(f"{API_URL}/health")
print(f"   Status: {response.json()}")

# Test 2: Build a simple app
print("\n✓ Step 2: Building a Simple Todo App")
print("   This will test the Gemini Flash model...")

build_response = requests.post(f"{API_URL}/api/build", json={
    "description": "Build a simple todo list app with add, delete, and mark complete features",
    "name": "simple-todo"
})

if build_response.status_code == 200:
    result = build_response.json()
    build_id = result['build_id']
    print(f"   ✓ Build started: {build_id}")
    
    # Monitor progress
    print("\n✓ Step 3: Monitoring Build Progress")
    print("   " + "-" * 66)
    
    last_step = ""
    while True:
        try:
            status_response = requests.get(f"{API_URL}/api/build/{build_id}/status")
            status = status_response.json()
            
            progress = status.get('progress', 0)
            current_step = status.get('current_step', 'Processing...')
            build_status = status.get('status', 'building')
            
            if current_step != last_step:
                print(f"   [{progress:3d}%] {current_step}")
                last_step = current_step
            
            if build_status in ['success', 'failed']:
                print("   " + "-" * 66)
                if build_status == 'success':
                    print(f"\n🎉 BUILD SUCCESSFUL!")
                    print(f"   App URL: {status.get('app_url', 'http://localhost:3000')}")
                    print(f"   Source: {status.get('source_path', './generated/simple-todo')}")
                    print(f"\n   To run your app:")
                    print(f"   cd {status.get('source_path', './generated/simple-todo')}")
                    print(f"   docker-compose up --build")
                else:
                    print(f"\n❌ BUILD FAILED")
                    logs = status.get('logs', [])
                    if logs:
                        print("\n   Last logs:")
                        for log in logs[-5:]:
                            print(f"   - {log.get('message', '')}")
                break
            
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Monitoring stopped by user")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            break
else:
    print(f"\n❌ Build failed to start: {build_response.json()}")

print("\n" + "=" * 70)
print("Test Complete!")
print("=" * 70)
