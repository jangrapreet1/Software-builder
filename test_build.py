"""
Quick test to build an application
"""
import requests
import time
import json

API_URL = "http://localhost:5000"

print("Testing Autonomous App Builder with Google Gemini...")
print("=" * 60)

# Test health
print("\n1. Checking API health...")
response = requests.get(f"{API_URL}/health")
print(f"   Status: {response.json()}")

# Build a simple app
print("\n2. Building a simple todo app...")
build_response = requests.post(f"{API_URL}/api/build", json={
    "description": "Build a simple todo list app with user authentication",
    "name": "todo-app"
})

if build_response.status_code == 200:
    result = build_response.json()
    build_id = result['build_id']
    print(f"   ✓ Build started: {build_id}")
    
    # Monitor progress
    print("\n3. Monitoring build progress...")
    while True:
        status_response = requests.get(f"{API_URL}/api/build/{build_id}/status")
        status = status_response.json()
        
        progress = status.get('progress', 0)
        current_step = status.get('current_step', 'Processing...')
        build_status = status.get('status', 'building')
        
        print(f"   [{progress}%] {current_step}")
        
        if build_status in ['success', 'failed']:
            print(f"\n   Build {build_status}!")
            if build_status == 'success':
                print(f"   App URL: {status.get('app_url', 'N/A')}")
                print(f"   Source: {status.get('source_path', 'N/A')}")
            break
        
        time.sleep(3)
else:
    print(f"   ✗ Error: {build_response.json()}")

print("\n" + "=" * 60)
print("Test complete!")
