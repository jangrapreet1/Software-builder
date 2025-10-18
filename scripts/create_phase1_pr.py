"""
Git automation script for creating Phase 1 feature branch and PR
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run_command(cmd, cwd=None):
    """Run shell command and return output"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Error: {e.stderr}")
        return None


def main():
    """Create feature branch, commit changes, and open PR"""
    repo_root = Path(__file__).resolve().parent.parent
    
    print("=" * 60)
    print("Phase 1: Creating feature branch and PR")
    print("=" * 60)
    
    # Check if git is available
    if not run_command("git --version"):
        print("Error: Git not found. Please install Git.")
        sys.exit(1)
    
    # Check current branch
    current_branch = run_command("git branch --show-current", cwd=repo_root)
    print(f"\nCurrent branch: {current_branch}")
    
    # Create feature branch
    branch_name = "feature/live-preview"
    print(f"\nCreating branch: {branch_name}")
    
    # Check if branch already exists
    existing_branches = run_command("git branch --list", cwd=repo_root)
    if branch_name in existing_branches:
        print(f"Branch {branch_name} already exists. Switching to it...")
        run_command(f"git checkout {branch_name}", cwd=repo_root)
    else:
        run_command(f"git checkout -b {branch_name}", cwd=repo_root)
    
    # Add files
    print("\nAdding files...")
    files_to_add = [
        "coordinator/ui/src/",
        "coordinator/services/build_registry.py",
        "coordinator/services/run_audit_logger.py",
        "coordinator/services/repository_detector.py",
        "coordinator/main.py",
        ".sb_artifacts/",
        "PHASE1_LIVE_PREVIEW_GUIDE.md",
        "workflows/app_builder_fixed.py",
    ]
    
    for file_path in files_to_add:
        full_path = repo_root / file_path
        if full_path.exists():
            run_command(f'git add "{file_path}"', cwd=repo_root)
            print(f"  ✓ Added {file_path}")
        else:
            print(f"  ⚠ Skipped {file_path} (not found)")
    
    # Check if there are changes to commit
    status = run_command("git status --porcelain", cwd=repo_root)
    if not status:
        print("\nNo changes to commit.")
        return
    
    # Commit changes
    commit_message = """feat: Phase 1 live preview with permission-first flow

- Add repository detection with persisted reports
- Implement permission-first sandbox launch workflow
- Add run audit logging with structured JSON artifacts
- Enhance build registry with persistence across restarts
- Add React UI components with permission modal
- Implement complete REST API contract
- Add comprehensive implementation guide

Phase 1 Deliverables:
- Detection report persistence to .sb_artifacts/
- Permission grant endpoint with audit logging
- Sandbox orchestration with resource limits
- Build metadata persistence
- Frontend permission modal showing exact commands
- Audit log retrieval endpoints
- Complete documentation in PHASE1_LIVE_PREVIEW_GUIDE.md
"""
    
    print("\nCommitting changes...")
    run_command(f'git commit -m "{commit_message}"', cwd=repo_root)
    print("  ✓ Changes committed")
    
    # Push to remote
    print("\nPushing to remote...")
    push_result = run_command(f"git push origin {branch_name}", cwd=repo_root)
    if push_result is not None:
        print("  ✓ Pushed to remote")
    else:
        print("  ⚠ Push failed. You may need to push manually.")
    
    # Create PR (using GitHub CLI if available)
    print("\nAttempting to create PR...")
    gh_version = run_command("gh --version")
    
    if gh_version:
        pr_title = "feat: Phase 1 Live Preview - Sandbox Orchestration"
        pr_body = """## Phase 1 Deliverables

This PR implements the Phase 1 live preview sandbox orchestration system with permission-first workflow.

### ✅ Implemented Features

1. **Detection Report Persistence**
   - Auto-detect languages, frameworks, build/run commands
   - Persist reports to `.sb_artifacts/detection_report_<timestamp>.json`
   - API endpoint to retrieve latest detection

2. **Permission-First Flow**
   - `POST /api/session/permissions` to record user approvals
   - `POST /api/app/launch` checks permission before execution
   - Returns HTTP 403 with required commands if permission missing
   - Frontend modal shows exact commands before approval

3. **Sandbox Orchestration**
   - Docker-based isolated containers
   - CPU/memory/timeout limits enforced
   - Health checks and session management
   - Automatic cleanup of expired instances

4. **Audit Logging**
   - Structured JSON logs for all operations
   - Run-specific audit trails in `.sb_artifacts/audit_run_*.json`
   - API endpoints: `/api/audit/{run_id}`, `/api/audit/runs/list`
   - Event tracking with timestamps, commands, exit codes

5. **Build Persistence**
   - Build metadata persisted to `.sb_artifacts/builds/`
   - Auto-bootstrap from `generated/` on startup
   - Survives backend restarts

6. **Frontend Components**
   - `LivePreview.tsx` - Embedded preview iframe
   - `ControlsPanel.tsx` - Launch/stop controls with permission modal
   - `StatusIndicator.tsx` - Instance status display
   - `LogsPanel.tsx` - Real-time container logs

7. **Complete API Contract**
   - `POST /api/repo/detect` - Detect and persist configuration
   - `GET /api/repo/detect/latest` - Get latest detection report
   - `POST /api/session/permissions` - Grant permissions
   - `POST /api/app/launch` - Launch sandbox (permission-gated)
   - `POST /api/app/stop` - Stop instance
   - `GET /api/app/download` - Download source (respects .gitignore)
   - `GET /api/audit/{run_id}` - Get run audit log
   - `GET /api/audit/runs/list` - List recent runs

8. **Documentation**
   - Complete implementation guide in `PHASE1_LIVE_PREVIEW_GUIDE.md`
   - API usage examples
   - Security features explained
   - Troubleshooting guide

### 📁 Artifacts

- Detection reports: `.sb_artifacts/detection_report_*.json`
- Audit logs: `.sb_artifacts/audit_run_*.json`
- Build metadata: `.sb_artifacts/builds/*.json`

### 🔒 Security

- Explicit user approval required before command execution
- Commands displayed in modal before approval
- Sandboxed execution with resource limits
- Secrets masked in logs
- Time-limited permissions
- Audit trail for all operations

### 🧪 Testing

See `PHASE1_LIVE_PREVIEW_GUIDE.md` for validation workflow and manual testing instructions.

### 📝 Notes

- Docker Desktop must be running for sandbox orchestration
- Backend runs on port 5000, frontend on port 5173
- All artifacts stored in `.sb_artifacts/` directory
"""
        
        pr_command = f'gh pr create --title "{pr_title}" --body "{pr_body}" --base main'
        pr_result = run_command(pr_command, cwd=repo_root)
        
        if pr_result:
            print(f"  ✓ PR created: {pr_result}")
            return pr_result
        else:
            print("  ⚠ PR creation failed. Create manually on GitHub.")
    else:
        print("  ⚠ GitHub CLI not found. Create PR manually:")
        print(f"     Branch: {branch_name}")
        print(f"     Title: feat: Phase 1 Live Preview - Sandbox Orchestration")
    
    print("\n" + "=" * 60)
    print("Branch and commits ready!")
    print("=" * 60)
    print(f"\nBranch: {branch_name}")
    print(f"Files added: {len(files_to_add)}")
    print("\nNext steps:")
    print("1. Review changes: git diff main")
    print("2. Create PR on GitHub if not auto-created")
    print("3. Review PHASE1_LIVE_PREVIEW_GUIDE.md for usage")


if __name__ == "__main__":
    main()
