"""
Monitor coordinator logs during build
"""
import requests
import time
import json

def monitor_build():
    """Monitor a build request"""
    print("📊 Monitoring Build Request...")
    print("=" * 50)
    
    # Start build
    response = requests.post("http://localhost:5000/api/build", json={
        "description": "Build a simple todo list app with user authentication",
        "name": "monitor-test"
    })
    
    if response.status_code != 200:
        print(f"❌ Build failed to start: {response.text}")
        return
    
    build_id = response.json()["build_id"]
    print(f"✅ Build started: {build_id}")
    
    # Monitor for 60 seconds
    for i in range(30):  # 30 iterations × 2 seconds = 60 seconds
        time.sleep(2)
        
        try:
            status_response = requests.get(f"http://localhost:5000/api/build/{build_id}/status")
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"[{i*2:2d}s] {status.get('current_step', 'Unknown')} - {status.get('progress', 0)}%")
                
                if status.get('status') in ['success', 'failed']:
                    print(f"🏁 Build {status.get('status')}!")
                    break
            else:
                print(f"[{i*2:2d}s] Status check failed: {status_response.status_code}")
        except Exception as e:
            print(f"[{i*2:2d}s] Error: {e}")
    
    print("⏰ Monitoring complete")

if __name__ == "__main__":
    monitor_build()