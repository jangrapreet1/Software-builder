"""
Example script demonstrating how to build an application programmatically
"""
import requests
import time
import json
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

API_URL = "http://localhost:5000"


def check_api_health():
    """Check if the API is running"""
    try:
        response = requests.get(f"{API_URL}/health")
        return response.status_code == 200
    except Exception:
        return False


def build_app(description, name=None, requirements=None):
    """Start building an application"""
    console.print(f"\n[bold cyan]Building application:[/bold cyan] {description}")
    
    payload = {
        "description": description,
        "name": name,
        "requirements": requirements or []
    }
    
    response = requests.post(f"{API_URL}/api/build", json=payload)
    
    if response.status_code != 200:
        console.print(f"[bold red]Error:[/bold red] {response.json().get('detail')}")
        return None
    
    result = response.json()
    console.print(f"[bold green]✓[/bold green] Build started with ID: {result['build_id']}")
    
    return result['build_id']


def watch_build(build_id):
    """Watch build progress"""
    console.print(f"\n[bold]Watching build progress...[/bold]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Building...", total=100)
        
        last_progress = 0
        
        while True:
            try:
                response = requests.get(f"{API_URL}/api/build/{build_id}/status")
                
                if response.status_code != 200:
                    console.print("[bold red]✗[/bold red] Failed to get build status")
                    break
                
                status = response.json()
                current_progress = status.get('progress', 0)
                current_step = status.get('current_step', 'Processing...')
                build_status = status.get('status', 'building')
                
                # Update progress
                progress.update(task, completed=current_progress, description=current_step)
                
                # Print new logs
                if last_progress != current_progress:
                    logs = status.get('logs', [])
                    if logs:
                        latest_log = logs[-1]
                        level = latest_log.get('level', 'info')
                        message = latest_log.get('message', '')
                        
                        if level == 'success':
                            console.print(f"[green]✓[/green] {message}")
                        elif level == 'error':
                            console.print(f"[red]✗[/red] {message}")
                        elif level == 'warning':
                            console.print(f"[yellow]⚠[/yellow] {message}")
                        else:
                            console.print(f"[blue]→[/blue] {message}")
                
                last_progress = current_progress
                
                # Check if build is complete
                if build_status in ['success', 'failed']:
                    break
                
                time.sleep(2)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Build monitoring stopped[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                time.sleep(2)
    
    return status


def main():
    """Main function"""
    console.print("\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]  Autonomous App Builder - Example Script[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════[/bold cyan]\n")
    
    # Check API health
    console.print("Checking API connection...")
    if not check_api_health():
        console.print("[bold red]✗[/bold red] API is not running")
        console.print("Please start the coordinator first:")
        console.print("  python coordinator/main.py")
        return
    
    console.print("[bold green]✓[/bold green] API is running\n")
    
    # Example 1: Simple task management app
    console.print("[bold]Example 1: Task Management App[/bold]")
    build_id = build_app(
        description="Build a task management app with user authentication and task sharing",
        name="task-manager",
        requirements=["user registration", "task CRUD", "task sharing"]
    )
    
    if build_id:
        final_status = watch_build(build_id)
        
        if final_status.get('status') == 'success':
            console.print("\n[bold green]✓ Build completed successfully![/bold green]")
            console.print(f"\n[bold]Your application is ready:[/bold]")
            console.print(f"  Frontend: http://localhost:3000")
            console.print(f"  Backend API: http://localhost:8000")
            console.print(f"  API Docs: http://localhost:8000/docs")
            console.print(f"  Source: {final_status.get('source_path', 'generated/')}")
        else:
            console.print("\n[bold red]✗ Build failed[/bold red]")
            errors = final_status.get('errors', [])
            if errors:
                console.print(f"Errors: {errors}")
    
    console.print("\n[bold]To run your application:[/bold]")
    console.print("  cd generated/task-manager")
    console.print("  docker-compose up\n")
    
    # List all builds
    console.print("\n[bold]All builds:[/bold]")
    response = requests.get(f"{API_URL}/api/builds")
    builds = response.json().get('builds', [])
    
    for build in builds:
        status_icon = "✓" if build['status'] == 'success' else "✗" if build['status'] == 'failed' else "→"
        status_color = "green" if build['status'] == 'success' else "red" if build['status'] == 'failed' else "yellow"
        console.print(f"  [{status_color}]{status_icon}[/{status_color}] {build['project_name']} - {build['status']} ({build['progress']}%)")


if __name__ == "__main__":
    main()
