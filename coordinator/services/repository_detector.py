"""
Repository detection service - auto-detect languages, frameworks, and build commands
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RepositoryDetector:
    """Detects repository configuration, frameworks, and commands"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.detection_cache = {}
        
    def detect_all(self, persist: bool = True) -> Dict:
        """Perform complete repository detection"""
        result = {
            "detection_timestamp": datetime.utcnow().isoformat() + "Z",
            "repository_root": str(self.repo_path.absolute()),
            "languages": self._detect_languages(),
            "frameworks": self._detect_frameworks(),
            "package_managers": self._detect_package_managers(),
            "build_commands": self._detect_build_commands(),
            "run_commands": self._detect_run_commands(),
            "test_commands": self._detect_test_commands(),
            "docker_config": self._detect_docker_config(),
            "environment_variables": self._detect_env_vars(),
        }
        
        # Persist detection report to artifacts directory
        if persist:
            artifact_path = self._persist_detection_report(result)
            result["artifactPath"] = str(artifact_path)
        
        return result
    
    def _persist_detection_report(self, report: Dict) -> Path:
        """Persist detection report to .sb_artifacts directory"""
        # Create artifacts directory
        artifact_dir = self.repo_path / ".sb_artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        filename = f"detection_report_{timestamp}.json"
        artifact_path = artifact_dir / filename
        
        # Write report
        try:
            with open(artifact_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Detection report saved to {artifact_path}")
        except Exception as e:
            logger.error(f"Failed to persist detection report: {e}")
            raise
        
        return artifact_path
    
    def get_latest_detection_report(self) -> Optional[Dict]:
        """Get the most recent detection report"""
        artifact_dir = self.repo_path / ".sb_artifacts"
        if not artifact_dir.exists():
            return None
        
        # Find all detection reports
        reports = sorted(artifact_dir.glob("detection_report_*.json"), reverse=True)
        if not reports:
            return None
        
        # Read the latest one
        try:
            with open(reports[0], 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read detection report: {e}")
            return None
    
    def _detect_languages(self) -> Dict[str, List[Dict]]:
        """Detect programming languages"""
        confident = []
        candidate = []
        
        # Python detection
        if self._file_exists("requirements.txt") or self._file_exists("pyproject.toml") or self._file_exists("setup.py"):
            python_version = self._detect_python_version()
            confident.append({
                "language": "Python",
                "version": python_version or "3.11+",
                "evidence": self._collect_evidence(["requirements.txt", "*.py", "pyproject.toml", "setup.py"])
            })
        
        # Node.js/JavaScript/TypeScript detection
        if self._file_exists("package.json"):
            node_version = self._detect_node_version()
            confident.append({
                "language": "JavaScript/TypeScript",
                "version": node_version or "18+",
                "evidence": self._collect_evidence(["package.json", "package-lock.json", "tsconfig.json"])
            })
        elif self._has_files_with_extension([".js", ".ts", ".tsx", ".jsx"]):
            candidate.append({
                "language": "JavaScript/TypeScript",
                "version": "Unknown",
                "evidence": "Found .js/.ts/.tsx/.jsx files",
                "note": "No package.json found"
            })
        
        # Go detection
        if self._file_exists("go.mod"):
            confident.append({
                "language": "Go",
                "version": "1.18+",
                "evidence": self._collect_evidence(["go.mod", "go.sum"])
            })
        
        # Java detection
        if self._file_exists("pom.xml") or self._file_exists("build.gradle"):
            confident.append({
                "language": "Java",
                "version": "11+",
                "evidence": self._collect_evidence(["pom.xml", "build.gradle", "settings.gradle"])
            })
        
        # Rust detection
        if self._file_exists("Cargo.toml"):
            confident.append({
                "language": "Rust",
                "version": "Latest stable",
                "evidence": self._collect_evidence(["Cargo.toml", "Cargo.lock"])
            })
        
        return {"confident": confident, "candidate": candidate}
    
    def _detect_frameworks(self) -> Dict[str, List[str]]:
        """Detect web frameworks and libraries"""
        confident = []
        candidate = []
        
        # Python frameworks
        requirements = self._read_requirements()
        if requirements:
            if any("fastapi" in req.lower() for req in requirements):
                confident.append("FastAPI")
            if any("django" in req.lower() for req in requirements):
                confident.append("Django")
            if any("flask" in req.lower() for req in requirements):
                confident.append("Flask")
            if any("langchain" in req.lower() for req in requirements):
                confident.append("LangChain")
            if any("langgraph" in req.lower() for req in requirements):
                confident.append("LangGraph")
            if any("autogen" in req.lower() for req in requirements):
                confident.append("AutoGen")
        
        # JavaScript frameworks
        package_json = self._read_package_json()
        if package_json:
            deps = {**package_json.get("dependencies", {}), **package_json.get("devDependencies", {})}
            if "react" in deps:
                confident.append("React")
            if "vue" in deps:
                confident.append("Vue.js")
            if "next" in deps:
                confident.append("Next.js")
            if "vite" in deps:
                confident.append("Vite")
            if "express" in deps:
                confident.append("Express.js")
        
        # Docker
        if self._file_exists("Dockerfile") or self._file_exists("docker-compose.yml"):
            confident.append("Docker")
        
        return {"confident": confident, "candidate": candidate}
    
    def _detect_package_managers(self) -> List[Dict]:
        """Detect package managers"""
        managers = []
        
        if self._file_exists("requirements.txt") or self._file_exists("pyproject.toml"):
            managers.append({
                "name": "pip",
                "install_command": "pip install -r requirements.txt" if self._file_exists("requirements.txt") else "pip install -e .",
                "files": self._collect_evidence(["requirements.txt", "pyproject.toml"])
            })
        
        if self._file_exists("poetry.lock"):
            managers.append({
                "name": "poetry",
                "install_command": "poetry install",
                "files": ["poetry.lock", "pyproject.toml"]
            })
        
        if self._file_exists("package.json"):
            lock_file = "package-lock.json" if self._file_exists("package-lock.json") else None
            yarn_lock = "yarn.lock" if self._file_exists("yarn.lock") else None
            pnpm_lock = "pnpm-lock.yaml" if self._file_exists("pnpm-lock.yaml") else None
            
            if pnpm_lock:
                managers.append({"name": "pnpm", "install_command": "pnpm install", "files": ["package.json", pnpm_lock]})
            elif yarn_lock:
                managers.append({"name": "yarn", "install_command": "yarn install", "files": ["package.json", yarn_lock]})
            else:
                managers.append({"name": "npm", "install_command": "npm ci" if lock_file else "npm install", "files": ["package.json"]})
        
        if self._file_exists("go.mod"):
            managers.append({"name": "go mod", "install_command": "go mod download", "files": ["go.mod"]})
        
        if self._file_exists("Cargo.toml"):
            managers.append({"name": "cargo", "install_command": "cargo fetch", "files": ["Cargo.toml"]})
        
        return managers
    
    def _detect_build_commands(self) -> Dict[str, List[str]]:
        """Detect build commands"""
        confident = []
        candidate = []
        
        # Python
        if self._file_exists("requirements.txt"):
            confident.append("pip install -r requirements.txt")
        
        # Docker
        if self._file_exists("Dockerfile"):
            confident.append("docker build -t app .")
        if self._file_exists("docker-compose.yml"):
            confident.append("docker-compose build")
        
        # Node.js
        package_json = self._read_package_json()
        if package_json and "scripts" in package_json:
            scripts = package_json["scripts"]
            if "build" in scripts:
                confident.append("npm run build")
            if "compile" in scripts:
                candidate.append("npm run compile")
        
        # Makefile
        if self._file_exists("Makefile"):
            candidate.append("make build")
        
        # Go
        if self._file_exists("go.mod"):
            confident.append("go build")
        
        # Rust
        if self._file_exists("Cargo.toml"):
            confident.append("cargo build --release")
        
        return {"confident": confident, "candidate": candidate}
    
    def _detect_run_commands(self) -> Dict[str, List[str]]:
        """Detect run commands"""
        confident = []
        candidate = []
        
        # Docker
        if self._file_exists("docker-compose.yml"):
            confident.append("docker-compose up")
        
        # Python
        if self._file_exists("main.py"):
            confident.append("python main.py")
        if self._file_exists("app.py"):
            confident.append("python app.py")
        if self._file_exists("manage.py"):  # Django
            confident.append("python manage.py runserver")
        
        # Check for uvicorn/gunicorn in requirements
        requirements = self._read_requirements()
        if requirements:
            if any("uvicorn" in req.lower() for req in requirements):
                candidate.append("uvicorn main:app --reload")
            if any("gunicorn" in req.lower() for req in requirements):
                candidate.append("gunicorn main:app")
        
        # Node.js
        package_json = self._read_package_json()
        if package_json and "scripts" in package_json:
            scripts = package_json["scripts"]
            if "start" in scripts:
                confident.append("npm start")
            if "dev" in scripts:
                candidate.append("npm run dev")
        
        return {"confident": confident, "candidate": candidate}
    
    def _detect_test_commands(self) -> Dict[str, List[str]]:
        """Detect test commands"""
        confident = []
        candidate = []
        
        # Python
        if self._file_exists("pytest.ini") or self._has_directory("tests"):
            confident.append("pytest")
        if self._file_exists("tox.ini"):
            candidate.append("tox")
        
        # Node.js
        package_json = self._read_package_json()
        if package_json and "scripts" in package_json:
            scripts = package_json["scripts"]
            if "test" in scripts:
                confident.append("npm test")
            if "test:unit" in scripts:
                candidate.append("npm run test:unit")
            if "test:e2e" in scripts:
                candidate.append("npm run test:e2e")
        
        # Go
        if self._file_exists("go.mod"):
            confident.append("go test ./...")
        
        # Rust
        if self._file_exists("Cargo.toml"):
            confident.append("cargo test")
        
        return {"confident": confident, "candidate": candidate}
    
    def _detect_docker_config(self) -> Optional[Dict]:
        """Detect Docker configuration"""
        if not (self._file_exists("Dockerfile") or self._file_exists("docker-compose.yml")):
            return None
        
        config = {}
        
        if self._file_exists("Dockerfile"):
            config["dockerfile"] = "Dockerfile"
            # Try to detect exposed ports
            dockerfile_content = self._read_file("Dockerfile")
            if dockerfile_content:
                ports = self._extract_exposed_ports(dockerfile_content)
                if ports:
                    config["exposed_ports"] = ports
        
        if self._file_exists("docker-compose.yml"):
            config["compose_file"] = "docker-compose.yml"
            compose_content = self._read_file("docker-compose.yml")
            if compose_content:
                services = self._extract_compose_services(compose_content)
                if services:
                    config["services"] = services
        
        return config if config else None
    
    def _detect_env_vars(self) -> Dict[str, List[str]]:
        """Detect environment variables"""
        required = []
        optional = []
        source = None
        
        if self._file_exists(".env.example"):
            source = ".env.example"
            env_content = self._read_file(".env.example")
            if env_content:
                for line in env_content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        var_name = line.split("=")[0].strip()
                        if var_name:
                            # Simple heuristic: API keys and secrets are required
                            if any(keyword in var_name.upper() for keyword in ["API_KEY", "SECRET", "PASSWORD"]):
                                required.append(var_name)
                            else:
                                optional.append(var_name)
        
        return {"required": required, "optional": optional, "source": source}
    
    # Helper methods
    
    def _file_exists(self, filename: str) -> bool:
        """Check if file exists in repo"""
        return (self.repo_path / filename).exists()
    
    def _has_directory(self, dirname: str) -> bool:
        """Check if directory exists in repo"""
        return (self.repo_path / dirname).is_dir()
    
    def _has_files_with_extension(self, extensions: List[str]) -> bool:
        """Check if any files with given extensions exist"""
        for ext in extensions:
            if list(self.repo_path.rglob(f"*{ext}")):
                return True
        return False
    
    def _read_file(self, filename: str) -> Optional[str]:
        """Read file content"""
        try:
            filepath = self.repo_path / filename
            if filepath.exists():
                return filepath.read_text(encoding="utf-8")
        except Exception:
            pass
        return None
    
    def _read_requirements(self) -> Optional[List[str]]:
        """Read requirements.txt"""
        content = self._read_file("requirements.txt")
        if content:
            return [line.strip() for line in content.split("\n") if line.strip() and not line.startswith("#")]
        return None
    
    def _read_package_json(self) -> Optional[Dict]:
        """Read package.json"""
        content = self._read_file("package.json")
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass
        return None
    
    def _collect_evidence(self, patterns: List[str]) -> List[str]:
        """Collect existing files matching patterns"""
        evidence = []
        for pattern in patterns:
            if "*" in pattern:
                # Glob pattern
                matches = list(self.repo_path.glob(pattern))
                if matches:
                    evidence.append(pattern)
            else:
                # Exact filename
                if self._file_exists(pattern):
                    evidence.append(pattern)
        return evidence
    
    def _detect_python_version(self) -> Optional[str]:
        """Detect Python version from runtime.txt or Dockerfile"""
        # Check runtime.txt (common in Heroku)
        runtime = self._read_file("runtime.txt")
        if runtime and "python" in runtime.lower():
            return runtime.strip().replace("python-", "")
        
        # Check Dockerfile
        dockerfile = self._read_file("Dockerfile")
        if dockerfile:
            for line in dockerfile.split("\n"):
                if "FROM python:" in line:
                    version = line.split("python:")[1].split("-")[0].split()[0]
                    return version + "+"
        
        return None
    
    def _detect_node_version(self) -> Optional[str]:
        """Detect Node.js version"""
        # Check .nvmrc
        nvmrc = self._read_file(".nvmrc")
        if nvmrc:
            return nvmrc.strip()
        
        # Check package.json engines
        package_json = self._read_package_json()
        if package_json and "engines" in package_json:
            node_version = package_json["engines"].get("node")
            if node_version:
                return node_version
        
        return None
    
    def _extract_exposed_ports(self, dockerfile_content: str) -> List[int]:
        """Extract EXPOSE directives from Dockerfile"""
        ports = []
        for line in dockerfile_content.split("\n"):
            if line.strip().upper().startswith("EXPOSE"):
                port_str = line.split("EXPOSE")[1].strip()
                try:
                    port = int(port_str.split("/")[0])  # Handle port/protocol
                    ports.append(port)
                except ValueError:
                    pass
        return ports
    
    def _extract_compose_services(self, compose_content: str) -> List[str]:
        """Extract service names from docker-compose.yml"""
        # Simple extraction - look for service definitions
        services = []
        in_services = False
        for line in compose_content.split("\n"):
            if "services:" in line:
                in_services = True
                continue
            if in_services:
                if line.strip() and not line.startswith(" ") and ":" in line:
                    break  # End of services section
                if line.strip() and line.startswith("  ") and ":" in line and not line.strip().startswith("#"):
                    service_name = line.strip().rstrip(":")
                    if service_name and not service_name.startswith("-"):
                        services.append(service_name)
        return services
