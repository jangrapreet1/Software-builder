"""
Error Message Enhancer - Quick Win #3
Provides user-friendly error messages with suggested fixes
"""
import re
from typing import Dict, List, Optional, Tuple


class ErrorPattern:
    """Error pattern with solutions"""
    
    def __init__(
        self,
        pattern: str,
        error_type: str,
        user_message: str,
        suggestions: List[str],
        documentation_link: Optional[str] = None,
        code_example: Optional[str] = None
    ):
        self.pattern = pattern
        self.error_type = error_type
        self.user_message = user_message
        self.suggestions = suggestions
        self.documentation_link = documentation_link
        self.code_example = code_example


class ErrorMessageEnhancer:
    """
    Enhances error messages with:
    - User-friendly explanations
    - Suggested fixes with examples
    - Links to documentation
    - Common resolution steps
    """
    
    def __init__(self):
        self.patterns: List[ErrorPattern] = []
        self._register_patterns()
    
    def _register_patterns(self):
        """Register common error patterns"""
        
        # Python errors
        self.patterns.append(ErrorPattern(
            pattern=r"ModuleNotFoundError: No module named '([^']+)'",
            error_type="missing_dependency",
            user_message="A required Python package '{0}' is not installed.",
            suggestions=[
                "Install the package: pip install {0}",
                "Add '{0}' to requirements.txt",
                "If using virtual environment, ensure it's activated"
            ],
            documentation_link="https://pip.pypa.io/en/stable/",
            code_example="pip install {0}"
        ))
        
        self.patterns.append(ErrorPattern(
            pattern=r"SyntaxError: invalid syntax.*line (\d+)",
            error_type="syntax_error",
            user_message="There's a syntax error in your Python code at line {0}.",
            suggestions=[
                "Check for missing colons, parentheses, or brackets",
                "Verify proper indentation",
                "Look for unclosed strings or comments",
                "Run: python -m py_compile <filename> to locate the error"
            ],
            documentation_link="https://docs.python.org/3/tutorial/errors.html"
        ))
        
        self.patterns.append(ErrorPattern(
            pattern=r"ImportError: cannot import name '([^']+)' from '([^']+)'",
            error_type="import_error",
            user_message="Cannot import '{0}' from '{1}'. The module exists but doesn't contain this name.",
            suggestions=[
                "Check if '{0}' is spelled correctly",
                "Verify the package version is compatible",
                "Check the package documentation for correct import path",
                "Try: from {1} import * to see available names"
            ]
        ))
        
        # JavaScript/Node errors
        self.patterns.append(ErrorPattern(
            pattern=r"Cannot find module '([^']+)'",
            error_type="missing_npm_package",
            user_message="The npm package '{0}' is not installed.",
            suggestions=[
                "Install the package: npm install {0}",
                "Add to package.json dependencies",
                "Run: npm install to install all dependencies",
                "Clear cache: npm cache clean --force && npm install"
            ],
            code_example="npm install {0}"
        ))
        
        self.patterns.append(ErrorPattern(
            pattern=r"Unexpected token.*",
            error_type="js_syntax_error",
            user_message="JavaScript syntax error detected.",
            suggestions=[
                "Check for missing commas, brackets, or semicolons",
                "Verify proper JSX syntax if using React",
                "Check for missing closing tags",
                "Run: npm run lint to identify issues"
            ]
        ))
        
        # Database errors
        self.patterns.append(ErrorPattern(
            pattern=r"could not connect to server|Connection refused",
            error_type="database_connection",
            user_message="Cannot connect to the database server.",
            suggestions=[
                "Verify database server is running",
                "Check connection string in .env file",
                "Verify host, port, username, and password",
                "Check firewall settings",
                "For PostgreSQL: sudo systemctl status postgresql"
            ],
            documentation_link="https://www.postgresql.org/docs/current/tutorial-start.html"
        ))
        
        self.patterns.append(ErrorPattern(
            pattern=r"relation \"([^\"]+)\" does not exist",
            error_type="missing_table",
            user_message="Database table '{0}' doesn't exist.",
            suggestions=[
                "Run database migrations: alembic upgrade head",
                "Or for Django: python manage.py migrate",
                "Verify database schema is up to date",
                "Check if table name is correct (case-sensitive)"
            ],
            code_example="alembic upgrade head"
        ))
        
        # Docker errors
        self.patterns.append(ErrorPattern(
            pattern=r"Cannot connect to the Docker daemon",
            error_type="docker_not_running",
            user_message="Docker daemon is not running.",
            suggestions=[
                "Start Docker Desktop or Docker service",
                "Windows: Start Docker Desktop application",
                "Linux: sudo systemctl start docker",
                "Verify Docker installation: docker --version"
            ]
        ))
        
        self.patterns.append(ErrorPattern(
            pattern=r"port is already allocated|address already in use",
            error_type="port_in_use",
            user_message="The port is already being used by another application.",
            suggestions=[
                "Stop the application using that port",
                "Change the port in your configuration",
                "Find process using port: netstat -ano | findstr :<port>",
                "Kill process: taskkill /PID <pid> /F (Windows)"
            ]
        ))
        
        # Authentication errors
        self.patterns.append(ErrorPattern(
            pattern=r"401.*Unauthorized|Authentication failed",
            error_type="auth_error",
            user_message="Authentication failed. Invalid or missing credentials.",
            suggestions=[
                "Check if you're logged in",
                "Verify API key or token is correct",
                "Check if token has expired",
                "Ensure Authorization header is set correctly"
            ]
        ))
        
        # API/Network errors
        self.patterns.append(ErrorPattern(
            pattern=r"ECONNREFUSED|Connection refused",
            error_type="api_connection_error",
            user_message="Cannot connect to the API server.",
            suggestions=[
                "Verify the API server is running",
                "Check the API URL in configuration",
                "Verify network connectivity",
                "Check if firewall is blocking the connection"
            ]
        ))
        
        # Build errors
        self.patterns.append(ErrorPattern(
            pattern=r"npm ERR!|build failed",
            error_type="build_error",
            user_message="Build process failed.",
            suggestions=[
                "Delete node_modules and package-lock.json",
                "Run: npm install",
                "Clear npm cache: npm cache clean --force",
                "Try with different Node version: nvm use <version>"
            ]
        ))
        
        # Environment errors
        self.patterns.append(ErrorPattern(
            pattern=r"Environment variable.*not set|KeyError: '([^']+)'",
            error_type="missing_env_var",
            user_message="Required environment variable '{0}' is not set.",
            suggestions=[
                "Create .env file from .env.example",
                "Add {0}=<value> to your .env file",
                "On Windows: set {0}=<value>",
                "On Linux/Mac: export {0}=<value>",
                "Verify .env file is in the correct directory"
            ],
            code_example="echo '{0}=your_value' >> .env"
        ))
    
    def enhance_error(self, error_message: str) -> Dict:
        """Enhance error message with helpful information"""
        # Try to match error patterns
        for pattern in self.patterns:
            match = re.search(pattern.pattern, error_message, re.IGNORECASE)
            if match:
                # Extract captured groups
                groups = match.groups()
                
                # Format messages with captured values
                user_message = pattern.user_message.format(*groups) if groups else pattern.user_message
                suggestions = [s.format(*groups) if groups else s for s in pattern.suggestions]
                code_example = pattern.code_example.format(*groups) if pattern.code_example and groups else pattern.code_example
                
                return {
                    "original_error": error_message,
                    "error_type": pattern.error_type,
                    "user_friendly_message": user_message,
                    "suggestions": suggestions,
                    "code_example": code_example,
                    "documentation_link": pattern.documentation_link,
                    "severity": self._determine_severity(pattern.error_type)
                }
        
        # No pattern matched - return generic enhancement
        return {
            "original_error": error_message,
            "error_type": "unknown",
            "user_friendly_message": "An error occurred during the build process.",
            "suggestions": [
                "Review the error message above for details",
                "Check recent changes to your code",
                "Search for the error message online",
                "Check application logs for more context"
            ],
            "severity": "medium"
        }
    
    def _determine_severity(self, error_type: str) -> str:
        """Determine error severity"""
        critical = ["database_connection", "docker_not_running", "missing_env_var"]
        high = ["missing_dependency", "missing_npm_package", "auth_error"]
        medium = ["syntax_error", "import_error", "build_error"]
        
        if error_type in critical:
            return "critical"
        elif error_type in high:
            return "high"
        elif error_type in medium:
            return "medium"
        else:
            return "low"
    
    def format_for_display(self, enhanced_error: Dict) -> str:
        """Format enhanced error for console display"""
        output = []
        output.append("=" * 80)
        output.append("ERROR DETAILS")
        output.append("=" * 80)
        output.append("")
        output.append(f"❌ {enhanced_error['user_friendly_message']}")
        output.append("")
        
        if enhanced_error.get("suggestions"):
            output.append("💡 Suggested fixes:")
            for i, suggestion in enumerate(enhanced_error["suggestions"], 1):
                output.append(f"   {i}. {suggestion}")
            output.append("")
        
        if enhanced_error.get("code_example"):
            output.append("📝 Example command:")
            output.append(f"   {enhanced_error['code_example']}")
            output.append("")
        
        if enhanced_error.get("documentation_link"):
            output.append(f"📚 Documentation: {enhanced_error['documentation_link']}")
            output.append("")
        
        output.append("Original error:")
        output.append(f"   {enhanced_error['original_error']}")
        output.append("=" * 80)
        
        return "\n".join(output)


# Global instance
_error_enhancer = None

def get_error_enhancer() -> ErrorMessageEnhancer:
    """Get global error enhancer instance"""
    global _error_enhancer
    if _error_enhancer is None:
        _error_enhancer = ErrorMessageEnhancer()
    return _error_enhancer
