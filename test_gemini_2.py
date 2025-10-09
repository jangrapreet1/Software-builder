"""
Test with Gemini 2.0 Flash Experimental
"""
import requests
import time

API_URL = "http://localhost:5000"

print("=" * 70)
print("🚀 Testing with Gemini 2.0 Flash Experimental")
print("=" * 70)

# Health check
print("\n✓ Health Check")
response = requests.get(f"{API_URL}/health")
print(f"   Status: {response.json()}")

# Build test
print("\n✓ Building Simple App with Gemini 2.0...")
build_response = requests.post(f"{API_URL}/api/build", json={
    "description": "Build a simple notes app with add and delete features",
    "name": "notes-app-test"
})

if build_response.status_code == 200:
    result = build_response.json()
    build_id = result['build_id']
    print(f"   ✓ Build started: {build_id}")
    print(f"   Using model: gemini-2.0-flash-exp")
    
    print("\n✓ Monitoring Progress...")
    print("   " + "-" * 66)
    
    last_step = ""
    for i in range(60):  # Monitor for up to 2 minutes
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
                    print(f"\n🎉 SUCCESS! Gemini 2.0 Flash Experimental worked!")
                    print(f"   Source: {status.get('source_path', './generated/notes-app-test')}")
                else:
                    print(f"\n❌ Build failed")
                    logs = status.get('logs', [])
                    if logs:
                        print("\n   Last logs:")
                        for log in logs[-3:]:
                            print(f"   - {log.get('message', '')}")
                break
            
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Stopped by user")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            break
else:
    print(f"\n❌ Build failed to start")
    print(f"   Error: {build_response.json()}")

print("\n" + "=" * 70)
