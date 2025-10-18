"""
MCP Manager - Manages connections to MCP servers (e.g., Playwright)
"""
import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


class MCPManagerError(Exception):
    """Raised when an MCP server interaction fails"""


class MCPManager:
    """Loads MCP server configurations and executes MCP-backed operations"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = Path(config_path) if config_path else Path("config/mcp_servers.json")
        self._config = self._load_config()

    def _load_config(self) -> Dict:
        """Load MCP configuration from JSON file"""
        if not self.config_path.exists():
            raise MCPManagerError(f"MCP configuration not found at {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as config_file:
                config = json.load(config_file)
        except json.JSONDecodeError as error:
            raise MCPManagerError(f"Invalid MCP configuration file: {error}") from error

        if not isinstance(config, dict):
            raise MCPManagerError("MCP configuration must be a JSON object")

        return config

    def _get_server(self, name: str) -> Dict:
        """Retrieve configuration for a specific MCP server"""
        try:
            return self._config[name]
        except KeyError as error:
            raise MCPManagerError(f"MCP server '{name}' is not configured") from error

    def run_playwright_tests(self, app_path: str | Path, specific_tests: Optional[List[str]] = None) -> Dict:
        """Run Playwright tests using the configured MCP Playwright server"""
        server_config = self._get_server("playwright")
        app_path = Path(app_path).resolve()

        if not app_path.exists():
            raise MCPManagerError(f"Application path does not exist: {app_path}")

        command_parts: List[str] = [server_config["command"], *server_config.get("args", [])]

        # Mount the application directory into the container and set working directory
        command_parts.extend([
            "-v",
            f"{app_path}:/workspace",
            "-w",
            "/workspace",
        ])

        # Playwright execution command
        playwright_command = [
            "npx",
            "playwright",
            "test",
            "--reporter=list",
        ]

        if specific_tests:
            playwright_command.extend(specific_tests)

        full_command = [*command_parts, *playwright_command]

        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as error:
            raise MCPManagerError(
                "Docker is not available on this system or not accessible from the container"
            ) from error
        except subprocess.SubprocessError as error:
            raise MCPManagerError(str(error)) from error

        summary = self._parse_playwright_summary(result.stdout, result.stderr)

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "summary": summary,
        }

    @staticmethod
    def _parse_playwright_summary(stdout: str, stderr: str) -> Dict:
        """Parse Playwright output to extract summary information"""
        summary = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_skipped": 0,
            "failures": [],
        }

        combined_output = f"{stdout}\n{stderr}".lower()

        passed_matches = re.findall(r"(\d+)\s+passed", combined_output)
        failed_matches = re.findall(r"(\d+)\s+failed", combined_output)
        skipped_matches = re.findall(r"(\d+)\s+skipped", combined_output)

        summary["tests_passed"] = sum(int(match) for match in passed_matches)
        summary["tests_failed"] = sum(int(match) for match in failed_matches)
        summary["tests_skipped"] = sum(int(match) for match in skipped_matches)
        summary["tests_run"] = (
            summary["tests_passed"] + summary["tests_failed"] + summary["tests_skipped"]
        )

        failure_details = re.findall(r"✖\s+(.*?)\s+-\s+(.*)", stdout)
        summary["failures"] = [
            {"test": test.strip(), "message": message.strip()} for test, message in failure_details
        ]

        return summary


_mcp_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """Get shared MCP manager instance"""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager
