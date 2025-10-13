"""
Phase 1 Sandbox Orchestration Demo

This script demonstrates the Phase 1 features:
1. Repository detection
2. Preview session creation
3. Sandbox instance launch
4. Status monitoring
5. Log retrieval
6. Instance cleanup
7. Download application

Usage:
    python examples/phase1_demo.py [app_path]
"""

import asyncio
import httpx
import json
import sys
from pathlib import Path
from typing import Dict


BASE_URL = "http://localhost:5000"


async def detect_repository(app_path: str) -> Dict:
    """Step 1: Detect repository configuration"""
    print("\n" + "="*60)
    print("STEP 1: REPOSITORY DETECTION")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/repo/detect",
            json={"repo_path": app_path},
            timeout=30.0
        )
        
        if response.status_code != 200:
            print(f"❌ Detection failed: {response.text}")
            return None
        
        result = response.json()
        report = result["detection_report"]
        
        print(f"\n✅ Repository detected: {report['repository_root']}")
        print(f"\n📋 Detection Report:")
        print(json.dumps(report, indent=2))
        
        # Show detected commands
        print(f"\n🔧 Detected Build Commands:")
        for cmd in report["build_commands"]["confident"]:
            print(f"  • {cmd}")
        
        print(f"\n▶️  Detected Run Commands:")
        for cmd in report["run_commands"]["confident"]:
            print(f"  • {cmd}")
        
        print(f"\n🧪 Detected Test Commands:")
        for cmd in report["test_commands"]["confident"]:
            print(f"  • {cmd}")
        
        return report


async def create_preview_session(app_path: str) -> Dict:
    """Step 2: Create preview session"""
    print("\n" + "="*60)
    print("STEP 2: CREATE PREVIEW SESSION")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/app/preview",
            json={
                "app_path": app_path,
                "port": 3000,
                "session_duration": 3600
            },
            timeout=30.0
        )
        
        if response.status_code == 503:
            print("⚠️  Session manager not available (Docker required)")
            return None
        
        if response.status_code != 200:
            print(f"❌ Preview session creation failed: {response.text}")
            return None
        
        result = response.json()
        
        print(f"\n✅ Preview session created")
        print(f"📱 Preview URL: {result['preview_url']}")
        print(f"🔑 Session Token: {result['session_token'][:16]}...")
        print(f"⏰ Expires: {result['expires_at']}")
        
        return result


async def launch_sandbox_instance(app_path: str) -> Dict:
    """Step 3: Launch sandbox instance"""
    print("\n" + "="*60)
    print("STEP 3: LAUNCH SANDBOX INSTANCE")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/app/launch",
            json={
                "app_path": app_path,
                "port": 3000,
                "cpu_limit": 0.5,
                "memory_limit": "256m",
                "timeout": 1800,
                "environment": {}
            },
            timeout=120.0  # Longer timeout for Docker build
        )
        
        if response.status_code == 503:
            print("⚠️  Sandbox orchestrator not available (Docker required)")
            return None
        
        if response.status_code != 200:
            print(f"❌ Instance launch failed: {response.text}")
            return None
        
        result = response.json()
        
        print(f"\n✅ Sandbox instance launched")
        print(f"🆔 Instance ID: {result['instance_id']}")
        print(f"📱 Preview URL: {result['preview_url']}")
        print(f"🔒 Secure URL: {result['secure_preview_url'][:50]}...")
        print(f"📊 Logs URL: {result['logs_url']}")
        print(f"🚪 Port: {result['port']}")
        print(f"⏰ Expires: {result['expires_at']}")
        
        return result


async def check_instance_status(instance_id: str):
    """Step 4: Check instance status"""
    print("\n" + "="*60)
    print("STEP 4: CHECK INSTANCE STATUS")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/sandbox/{instance_id}/status",
            timeout=30.0
        )
        
        if response.status_code != 200:
            print(f"❌ Status check failed: {response.text}")
            return
        
        status = response.json()
        
        print(f"\n✅ Instance Status")
        print(f"🆔 Instance ID: {status['instance_id']}")
        print(f"🔴 Status: {status['status']}")
        print(f"❤️  Health: {status['health']}")
        print(f"📱 Preview URL: {status['preview_url']}")
        
        if "resources" in status:
            resources = status["resources"]
            print(f"\n📊 Resource Usage:")
            print(f"  • CPU: {resources['cpu_percent']}%")
            print(f"  • Memory: {resources['memory_usage']} ({resources['memory_percent']}%)")


async def get_instance_logs(instance_id: str):
    """Step 5: Get instance logs"""
    print("\n" + "="*60)
    print("STEP 5: RETRIEVE INSTANCE LOGS")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/sandbox/{instance_id}/logs?tail=20",
            timeout=30.0
        )
        
        if response.status_code != 200:
            print(f"❌ Log retrieval failed: {response.text}")
            return
        
        result = response.json()
        
        print(f"\n📜 Last 20 log lines:")
        print("-" * 60)
        print(result["logs"])
        print("-" * 60)


async def list_all_instances():
    """List all active instances"""
    print("\n" + "="*60)
    print("LIST ALL ACTIVE INSTANCES")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/sandbox/instances",
            timeout=30.0
        )
        
        if response.status_code == 503:
            print("⚠️  Sandbox orchestrator not available")
            return
        
        if response.status_code != 200:
            print(f"❌ Failed to list instances: {response.text}")
            return
        
        result = response.json()
        
        print(f"\n📦 Active Instances: {result['count']}")
        for instance in result["instances"]:
            print(f"\n  • {instance['instance_id']}")
            print(f"    Status: {instance['status']}")
            print(f"    Preview: {instance['preview_url']}")
            print(f"    Expires: {instance['expires_at']}")


async def stop_instance(instance_id: str):
    """Step 6: Stop instance"""
    print("\n" + "="*60)
    print("STEP 6: STOP SANDBOX INSTANCE")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/app/stop",
            json={
                "instance_id": instance_id,
                "force": True
            },
            timeout=30.0
        )
        
        if response.status_code != 200:
            print(f"❌ Stop failed: {response.text}")
            return
        
        result = response.json()
        
        print(f"\n✅ Instance stopped")
        print(f"🆔 Instance ID: {result['instance_id']}")
        print(f"🔴 Status: {result['status']}")
        print(f"🔒 Revoked Sessions: {result.get('revoked_sessions', 0)}")


async def download_app(app_path: str):
    """Step 7: Download application"""
    print("\n" + "="*60)
    print("STEP 7: DOWNLOAD APPLICATION")
    print("="*60)
    
    app_name = Path(app_path).name
    output_file = f"{app_name}.zip"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/app/download",
            params={"app_path": app_path},
            timeout=60.0
        )
        
        if response.status_code != 200:
            print(f"❌ Download failed: {response.text}")
            return
        
        # Save zip file
        with open(output_file, "wb") as f:
            f.write(response.content)
        
        print(f"\n✅ Application downloaded")
        print(f"📦 File: {output_file}")
        print(f"💾 Size: {len(response.content) / 1024:.2f} KB")


async def check_sandbox_health():
    """Check sandbox health"""
    print("\n" + "="*60)
    print("SANDBOX HEALTH CHECK")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/sandbox/health",
            timeout=30.0
        )
        
        if response.status_code != 200:
            print(f"❌ Health check failed: {response.text}")
            return False
        
        health = response.json()
        
        print(f"\n📊 Sandbox Health")
        print(f"🔴 Status: {health['status']}")
        
        if health['status'] == 'healthy':
            print(f"🐳 Docker: {health['docker']}")
            print(f"🌐 Network: {health['network']}")
            print(f"📦 Active Instances: {health['active_instances']}/{health['max_instances']}")
            return True
        elif health['status'] == 'unavailable':
            print(f"⚠️  {health['message']}")
            return False
        else:
            print(f"❌ Error: {health.get('error', 'Unknown')}")
            return False


async def main():
    """Main demo function"""
    print("\n" + "="*60)
    print("PHASE 1: SANDBOX ORCHESTRATION DEMO")
    print("="*60)
    
    # Get app path from command line or use default
    if len(sys.argv) > 1:
        app_path = sys.argv[1]
    else:
        # Try to find a generated app
        generated_dir = Path("generated")
        if generated_dir.exists():
            apps = [d for d in generated_dir.iterdir() if d.is_dir() and d.name != ".git"]
            if apps:
                app_path = str(apps[0])
            else:
                print("\n❌ No generated apps found. Please provide an app path:")
                print("   python examples/phase1_demo.py /path/to/app")
                return
        else:
            print("\n❌ Please provide an app path:")
            print("   python examples/phase1_demo.py /path/to/app")
            return
    
    print(f"\n🎯 Target Application: {app_path}")
    
    # Check if coordinator is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health", timeout=5.0)
            if response.status_code != 200:
                print(f"\n❌ Coordinator not healthy. Please start it first:")
                print("   python coordinator/main.py")
                return
    except Exception as e:
        print(f"\n❌ Cannot connect to coordinator at {BASE_URL}")
        print("   Please start it first: python coordinator/main.py")
        return
    
    # Check sandbox health
    sandbox_available = await check_sandbox_health()
    
    # Step 1: Detect repository
    detection = await detect_repository(app_path)
    if not detection:
        return
    
    # Step 2: Create preview session
    preview = await create_preview_session(app_path)
    
    # Only proceed with launch if Docker is available
    if not sandbox_available:
        print("\n⚠️  Docker not available. Skipping instance launch steps.")
        print("   Install Docker to enable full sandbox orchestration.")
        
        # Step 7: Download (doesn't require Docker)
        await download_app(app_path)
        
        print("\n" + "="*60)
        print("DEMO COMPLETE (Limited - No Docker)")
        print("="*60)
        return
    
    # Step 3: Launch instance
    instance = await launch_sandbox_instance(app_path)
    if not instance:
        return
    
    instance_id = instance["instance_id"]
    
    # Wait a bit for container to start
    print("\n⏳ Waiting 5 seconds for container to initialize...")
    await asyncio.sleep(5)
    
    # Step 4: Check status
    await check_instance_status(instance_id)
    
    # Step 5: Get logs
    await get_instance_logs(instance_id)
    
    # List all instances
    await list_all_instances()
    
    # Step 6: Stop instance
    print("\n⏳ Keeping instance running for 10 seconds...")
    print("   (You can test the preview URL now)")
    await asyncio.sleep(10)
    
    await stop_instance(instance_id)
    
    # Step 7: Download
    await download_app(app_path)
    
    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60)
    print("\n✅ All Phase 1 features demonstrated successfully!")
    print("\n📚 For more information, see docs/phase1_sandbox_orchestration.md")


if __name__ == "__main__":
    asyncio.run(main())
