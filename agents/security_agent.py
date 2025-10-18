"""
SecurityAgent - Specialized agent for security auditing and hardening
"""
import ast
import re
import json
from typing import Any, List, Dict
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

from config.settings import Settings


class SecurityAgent:
    """
    Specialized agent for security vulnerability detection and auto-fixing
    """
    
    def __init__(self, llm: ChatGoogleGenerativeAI, settings: Settings):
        self.llm = llm
        self.settings = settings
        
        # Security patterns to check
        self.dangerous_patterns = {
            "sql_injection": [r"execute\([^)]*%[^)]*\)", r"cursor\.execute\([^)]*\+[^)]*\)"],
            "xss": [r"innerHTML\s*=\s*[^;]*\+", r"dangerouslySetInnerHTML"],
            "secrets": [r"password\s*=\s*['\"][^'\"]+['\"]", r"api_key\s*=\s*['\"][^'\"]+['\"]"],
            "unsafe_eval": [r"\beval\(", r"\bexec\("],
            "insecure_random": [r"random\.random\(\)", r"Math\.random\(\)"],
        }
    
    async def audit_code(self, backend_code: dict, frontend_code: dict) -> dict:
        """
        Comprehensive security audit of generated code
        """
        issues = []
        
        # Audit backend
        for file_name, content in backend_code.items():
            file_issues = await self._audit_python_file(file_name, content)
            issues.extend(file_issues)
        
        # Audit frontend
        for file_name, content in frontend_code.items():
            if isinstance(content, str):
                file_issues = await self._audit_javascript_file(file_name, content)
                issues.extend(file_issues)
            elif isinstance(content, dict):
                # Handle nested structure (pages, components)
                for nested_name, nested_content in content.items():
                    file_issues = await self._audit_javascript_file(
                        f"{file_name}/{nested_name}", nested_content
                    )
                    issues.extend(file_issues)
        
        # Calculate severity score
        severity_score = self._calculate_severity_score(issues)
        
        return {
            "issues": issues,
            "total_issues": len(issues),
            "critical_count": len([i for i in issues if i["severity"] == "critical"]),
            "high_count": len([i for i in issues if i["severity"] == "high"]),
            "medium_count": len([i for i in issues if i["severity"] == "medium"]),
            "low_count": len([i for i in issues if i["severity"] == "low"]),
            "severity_score": severity_score,
            "status": "failed" if severity_score > 70 else "passed"
        }
    
    async def _audit_python_file(self, file_name: str, content: str) -> List[Dict]:
        """Audit Python file for security issues"""
        issues = []
        
        # Check for SQL injection patterns
        for pattern in self.dangerous_patterns["sql_injection"]:
            matches = re.finditer(pattern, content)
            for match in matches:
                issues.append({
                    "file": file_name,
                    "line": content[:match.start()].count('\n') + 1,
                    "category": "sql_injection",
                    "severity": "critical",
                    "message": "Potential SQL injection vulnerability detected",
                    "code_snippet": match.group(0),
                    "recommendation": "Use parameterized queries with SQLAlchemy ORM"
                })
        
        # Check for unsafe eval/exec
        for pattern in self.dangerous_patterns["unsafe_eval"]:
            matches = re.finditer(pattern, content)
            for match in matches:
                issues.append({
                    "file": file_name,
                    "line": content[:match.start()].count('\n') + 1,
                    "category": "code_injection",
                    "severity": "critical",
                    "message": "Unsafe eval() or exec() usage detected",
                    "code_snippet": match.group(0),
                    "recommendation": "Avoid eval/exec, use safe alternatives"
                })
        
        # Check for hardcoded secrets
        for pattern in self.dangerous_patterns["secrets"]:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                if "change" not in match.group(0).lower() and "example" not in match.group(0).lower():
                    issues.append({
                        "file": file_name,
                        "line": content[:match.start()].count('\n') + 1,
                        "category": "secrets_exposure",
                        "severity": "high",
                        "message": "Potential hardcoded secret detected",
                        "code_snippet": match.group(0),
                        "recommendation": "Use environment variables for secrets"
                    })
        
        # Check for weak cryptography
        if "md5" in content.lower() or "sha1" in content.lower():
            issues.append({
                "file": file_name,
                "line": -1,
                "category": "weak_crypto",
                "severity": "medium",
                "message": "Weak cryptographic algorithm (MD5/SHA1) detected",
                "recommendation": "Use SHA256 or stronger algorithms"
            })
        
        # Check for missing authentication
        if file_name == "routes.py" and "Depends(get_current_user)" not in content:
            if "router.get" in content or "router.post" in content:
                issues.append({
                    "file": file_name,
                    "line": -1,
                    "category": "missing_auth",
                    "severity": "high",
                    "message": "Routes may be missing authentication checks",
                    "recommendation": "Add Depends(get_current_user) to protected routes"
                })
        
        return issues
    
    async def _audit_javascript_file(self, file_name: str, content: str) -> List[Dict]:
        """Audit JavaScript/TypeScript file for security issues"""
        issues = []
        
        # Check for XSS vulnerabilities
        for pattern in self.dangerous_patterns["xss"]:
            matches = re.finditer(pattern, content)
            for match in matches:
                issues.append({
                    "file": file_name,
                    "line": content[:match.start()].count('\n') + 1,
                    "category": "xss",
                    "severity": "high",
                    "message": "Potential XSS vulnerability detected",
                    "code_snippet": match.group(0),
                    "recommendation": "Sanitize user input and use safe rendering methods"
                })
        
        # Check for insecure randomness
        for pattern in self.dangerous_patterns["insecure_random"]:
            matches = re.finditer(pattern, content)
            for match in matches:
                issues.append({
                    "file": file_name,
                    "line": content[:match.start()].count('\n') + 1,
                    "category": "weak_random",
                    "severity": "medium",
                    "message": "Insecure random number generation",
                    "code_snippet": match.group(0),
                    "recommendation": "Use crypto.getRandomValues() for security-sensitive operations"
                })
        
        # Check for localStorage with sensitive data
        if "localStorage.setItem" in content and ("token" in content.lower() or "password" in content.lower()):
            issues.append({
                "file": file_name,
                "line": -1,
                "category": "insecure_storage",
                "severity": "medium",
                "message": "Sensitive data stored in localStorage",
                "recommendation": "Consider using httpOnly cookies or sessionStorage"
            })
        
        return issues
    
    async def apply_security_fixes(self, code: dict, issues: List[Dict]) -> dict:
        """
        Automatically fix common security issues
        """
        fixed_code = code.copy()
        
        for issue in issues:
            if issue["severity"] in ["critical", "high"]:
                file_name = issue["file"]
                
                if file_name in fixed_code:
                    content = fixed_code[file_name]
                    
                    # Apply fixes based on category
                    if issue["category"] == "sql_injection":
                        content = self._fix_sql_injection(content)
                    elif issue["category"] == "code_injection":
                        content = self._fix_code_injection(content)
                    elif issue["category"] == "xss":
                        content = self._fix_xss(content)
                    
                    fixed_code[file_name] = content
        
        return fixed_code
    
    def _fix_sql_injection(self, content: str) -> str:
        """Fix SQL injection by converting to parameterized queries"""
        # Replace string concatenation with parameterized queries
        content = re.sub(
            r'execute\(f"([^"]+)"\)',
            r'execute(text("\1"), params)',
            content
        )
        return content
    
    def _fix_code_injection(self, content: str) -> str:
        """Remove eval/exec usage"""
        # Comment out eval/exec with warning
        content = re.sub(
            r'(\s*)(eval|exec)\(',
            r'\1# SECURITY: Removed unsafe \2(',
            content
        )
        return content
    
    def _fix_xss(self, content: str) -> str:
        """Fix XSS by using safe rendering"""
        # Replace innerHTML with textContent
        content = re.sub(
            r'\.innerHTML\s*=',
            '.textContent =',
            content
        )
        return content
    
    def _calculate_severity_score(self, issues: List[Dict]) -> int:
        """Calculate overall severity score (0-100, higher is worse)"""
        if not issues:
            return 0
        
        score = 0
        weights = {
            "critical": 30,
            "high": 20,
            "medium": 10,
            "low": 5
        }
        
        for issue in issues:
            score += weights.get(issue["severity"], 0)
        
        return min(100, score)
    
    async def generate_security_report(self, audit_results: dict, project_name: str) -> str:
        """Generate detailed security report"""
        report = f"""# Security Audit Report: {project_name}

## Summary

- **Total Issues**: {audit_results['total_issues']}
- **Critical**: {audit_results['critical_count']}
- **High**: {audit_results['high_count']}
- **Medium**: {audit_results['medium_count']}
- **Low**: {audit_results['low_count']}
- **Severity Score**: {audit_results['severity_score']}/100
- **Status**: {audit_results['status'].upper()}

## Issues by Category

"""
        
        # Group issues by category
        by_category = {}
        for issue in audit_results['issues']:
            cat = issue['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(issue)
        
        for category, issues in by_category.items():
            report += f"\n### {category.replace('_', ' ').title()}\n\n"
            for issue in issues:
                report += f"""
**File**: `{issue['file']}`  
**Line**: {issue['line']}  
**Severity**: {issue['severity'].upper()}  
**Message**: {issue['message']}  
**Recommendation**: {issue['recommendation']}

"""
        
        report += """
## Remediation Steps

1. Address all critical and high severity issues immediately
2. Review and fix medium severity issues
3. Plan to address low severity issues in next iteration
4. Re-run security audit after fixes
5. Implement automated security scanning in CI/CD

## Best Practices

- Use parameterized queries for all database operations
- Sanitize and validate all user inputs
- Store secrets in environment variables
- Use secure random number generators
- Implement proper authentication and authorization
- Keep dependencies up to date
- Enable security headers (CORS, CSP, etc.)
"""
        
        return report
