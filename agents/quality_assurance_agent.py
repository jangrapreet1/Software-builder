"""
Quality Assurance Agent - Comprehensive quality checks
Phase 3B.2 from analysis
"""
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import re

from agents.base_agent import BaseAgent, ExecutionContext, ExecutionResult, AgentStatus, AgentCapability


class QualityAssuranceAgent(BaseAgent):
    """
    QA agent that performs:
    - Security vulnerability scanning
    - Performance profiling
    - Accessibility audits
    - SEO scoring
    """
    
    def get_capabilities(self) -> List[AgentCapability]:
        return [AgentCapability.CODE_ANALYSIS, AgentCapability.TESTING]
    
    def validate_input(self, request_data: Dict) -> Tuple[bool, Optional[str]]:
        if "project_path" not in request_data:
            return False, "project_path is required"
        return True, None
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """Execute QA checks"""
        project_path = Path(context.request_data["project_path"])
        
        if not project_path.exists():
            return ExecutionResult(
                status=AgentStatus.FAILED,
                output=None,
                errors=[f"Project path does not exist: {project_path}"]
            )
        
        results = {
            "security": await self._security_scan(project_path),
            "performance": await self._performance_check(project_path),
            "accessibility": await self._accessibility_audit(project_path),
            "seo": await self._seo_scoring(project_path)
        }
        
        # Calculate overall score
        scores = [r["score"] for r in results.values() if "score" in r]
        overall_score = sum(scores) / len(scores) if scores else 0
        
        # Determine status
        critical_issues = sum(len(r.get("critical", [])) for r in results.values())
        
        return ExecutionResult(
            status=AgentStatus.COMPLETED if critical_issues == 0 else AgentStatus.FAILED,
            output={
                **results,
                "overall_score": overall_score,
                "grade": self._get_grade(overall_score),
                "critical_issues": critical_issues
            },
            warnings=[f"{critical_issues} critical issues found"] if critical_issues > 0 else []
        )
    
    async def _security_scan(self, project_path: Path) -> Dict:
        """Security vulnerability scanning (OWASP checks)"""
        issues = []
        
        # Check for common security issues
        all_files = list(project_path.rglob("*.py")) + list(project_path.rglob("*.js")) + list(project_path.rglob("*.ts"))
        
        for file_path in all_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # OWASP A01: Broken Access Control
                if re.search(r'@app\.get|@app\.post', content) and 'Depends' not in content:
                    issues.append({
                        "severity": "high",
                        "category": "A01:Broken-Access-Control",
                        "file": str(file_path),
                        "message": "Endpoint without authentication dependency",
                        "recommendation": "Add authentication dependencies to protected routes"
                    })
                
                # OWASP A02: Cryptographic Failures
                if re.search(r'md5|sha1[^256]', content, re.I):
                    issues.append({
                        "severity": "high",
                        "category": "A02:Cryptographic-Failures",
                        "file": str(file_path),
                        "message": "Weak cryptographic algorithm detected",
                        "recommendation": "Use SHA-256 or stronger algorithms"
                    })
                
                # OWASP A03: Injection
                if re.search(r'\.execute\([^?]*\+|\.execute\([^?]*%', content):
                    issues.append({
                        "severity": "critical",
                        "category": "A03:Injection",
                        "file": str(file_path),
                        "message": "Potential SQL injection vulnerability",
                        "recommendation": "Use parameterized queries"
                    })
                
                if re.search(r'eval\(|exec\(', content):
                    issues.append({
                        "severity": "critical",
                        "category": "A03:Injection",
                        "file": str(file_path),
                        "message": "Use of eval/exec is dangerous",
                        "recommendation": "Remove eval/exec or use safer alternatives"
                    })
                
                # OWASP A04: Insecure Design
                if re.search(r'password.*=.*["\']', content, re.I) and 'test' not in file_path.name.lower():
                    issues.append({
                        "severity": "critical",
                        "category": "A04:Insecure-Design",
                        "file": str(file_path),
                        "message": "Hardcoded credentials",
                        "recommendation": "Use environment variables for secrets"
                    })
                
                # OWASP A05: Security Misconfiguration
                if 'DEBUG = True' in content or 'debug: true' in content.lower():
                    issues.append({
                        "severity": "medium",
                        "category": "A05:Security-Misconfiguration",
                        "file": str(file_path),
                        "message": "Debug mode enabled",
                        "recommendation": "Disable debug mode in production"
                    })
                
                # OWASP A06: Vulnerable Components
                # Would check package versions against CVE database in production
                
                # OWASP A07: Identification and Authentication Failures
                if re.search(r'password.*length.*<.*8', content):
                    issues.append({
                        "severity": "medium",
                        "category": "A07:Auth-Failures",
                        "file": str(file_path),
                        "message": "Weak password requirements",
                        "recommendation": "Enforce minimum 8-character passwords"
                    })
                
                # OWASP A08: Software and Data Integrity Failures
                # Check for missing integrity checks
                
                # OWASP A09: Security Logging Failures
                if re.search(r'except.*:.*pass', content):
                    issues.append({
                        "severity": "low",
                        "category": "A09:Logging-Failures",
                        "file": str(file_path),
                        "message": "Silent exception handling",
                        "recommendation": "Log exceptions for security monitoring"
                    })
                
                # OWASP A10: Server-Side Request Forgery
                if re.search(r'requests\.get\(.*input|requests\.get\(.*request\.', content):
                    issues.append({
                        "severity": "high",
                        "category": "A10:SSRF",
                        "file": str(file_path),
                        "message": "Potential SSRF vulnerability",
                        "recommendation": "Validate and whitelist URLs before making requests"
                    })
            
            except Exception:
                pass
        
        critical = [i for i in issues if i["severity"] == "critical"]
        high = [i for i in issues if i["severity"] == "high"]
        medium = [i for i in issues if i["severity"] == "medium"]
        low = [i for i in issues if i["severity"] == "low"]
        
        score = 100 - (len(critical) * 25 + len(high) * 15 + len(medium) * 5 + len(low))
        score = max(0, score)
        
        return {
            "score": score,
            "issues": issues,
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
            "summary": f"Found {len(issues)} security issues"
        }
    
    async def _performance_check(self, project_path: Path) -> Dict:
        """Performance profiling and anti-pattern detection"""
        issues = []
        
        all_files = list(project_path.rglob("*.py")) + list(project_path.rglob("*.js")) + list(project_path.rglob("*.ts"))
        
        for file_path in all_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # N+1 query problem
                if re.search(r'for.*in.*:.*\.query\(|for.*in.*:.*\.get\(', content):
                    issues.append({
                        "severity": "medium",
                        "category": "n+1-queries",
                        "file": str(file_path),
                        "message": "Potential N+1 query problem",
                        "recommendation": "Use eager loading or batch queries"
                    })
                
                # Synchronous I/O in async context
                if 'async def' in content and re.search(r'\.read\(|\.write\(|requests\.(get|post)', content):
                    issues.append({
                        "severity": "medium",
                        "category": "blocking-io",
                        "file": str(file_path),
                        "message": "Blocking I/O in async function",
                        "recommendation": "Use async I/O operations"
                    })
                
                # Large data loading without pagination
                if re.search(r'\.all\(\)|\*.*FROM', content) and 'limit' not in content.lower():
                    issues.append({
                        "severity": "low",
                        "category": "memory-usage",
                        "file": str(file_path),
                        "message": "Loading all records without pagination",
                        "recommendation": "Implement pagination"
                    })
                
                # Inefficient loops
                if content.count('for') > 3 and content.count('for') == content.count('in'):
                    issues.append({
                        "severity": "info",
                        "category": "algorithm-efficiency",
                        "file": str(file_path),
                        "message": "Multiple nested loops detected",
                        "recommendation": "Consider optimizing algorithm complexity"
                    })
            
            except Exception:
                pass
        
        score = 100 - (len([i for i in issues if i["severity"] == "medium"]) * 10 + len([i for i in issues if i["severity"] == "low"]) * 5)
        score = max(0, score)
        
        return {
            "score": score,
            "issues": issues,
            "summary": f"Found {len(issues)} performance issues"
        }
    
    async def _accessibility_audit(self, project_path: Path) -> Dict:
        """Accessibility audit (WCAG compliance)"""
        issues = []
        
        # Check HTML/JSX files
        html_files = list(project_path.rglob("*.html")) + list(project_path.rglob("*.jsx")) + list(project_path.rglob("*.tsx"))
        
        for file_path in html_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # Missing alt text on images
                if '<img' in content and not re.search(r'<img[^>]*alt=', content):
                    issues.append({
                        "severity": "medium",
                        "category": "WCAG-1.1.1",
                        "file": str(file_path),
                        "message": "Images missing alt text",
                        "recommendation": "Add descriptive alt attributes to all images"
                    })
                
                # Missing form labels
                if '<input' in content and not re.search(r'<label|aria-label', content):
                    issues.append({
                        "severity": "medium",
                        "category": "WCAG-3.3.2",
                        "file": str(file_path),
                        "message": "Form inputs missing labels",
                        "recommendation": "Add labels or aria-label to form inputs"
                    })
                
                # Missing page title
                if '<html' in content and '<title>' not in content:
                    issues.append({
                        "severity": "low",
                        "category": "WCAG-2.4.2",
                        "file": str(file_path),
                        "message": "Missing page title",
                        "recommendation": "Add descriptive title tag"
                    })
                
                # Missing language attribute
                if '<html' in content and not re.search(r'<html[^>]*lang=', content):
                    issues.append({
                        "severity": "low",
                        "category": "WCAG-3.1.1",
                        "file": str(file_path),
                        "message": "Missing language attribute",
                        "recommendation": "Add lang attribute to html tag"
                    })
                
                # Button without accessible name
                if '<button>' in content or '<button ' in content:
                    if not re.search(r'<button[^>]*aria-label=|<button>[^<]', content):
                        issues.append({
                            "severity": "medium",
                            "category": "WCAG-4.1.2",
                            "file": str(file_path),
                            "message": "Buttons without accessible names",
                            "recommendation": "Add text content or aria-label to buttons"
                        })
            
            except Exception:
                pass
        
        score = 100 - (len([i for i in issues if i["severity"] == "medium"]) * 10 + len([i for i in issues if i["severity"] == "low"]) * 3)
        score = max(0, score)
        
        return {
            "score": score,
            "issues": issues,
            "summary": f"Found {len(issues)} accessibility issues",
            "wcag_level": "A" if score >= 90 else "Partial"
        }
    
    async def _seo_scoring(self, project_path: Path) -> Dict:
        """SEO scoring"""
        issues = []
        score = 100
        
        html_files = list(project_path.rglob("*.html")) + list(project_path.rglob("*.jsx")) + list(project_path.rglob("*.tsx"))
        
        for file_path in html_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # Missing meta description
                if '<html' in content and 'meta name="description"' not in content:
                    issues.append({
                        "severity": "medium",
                        "file": str(file_path),
                        "message": "Missing meta description",
                        "recommendation": "Add meta description for better SEO"
                    })
                    score -= 10
                
                # Missing Open Graph tags
                if '<html' in content and 'og:title' not in content:
                    issues.append({
                        "severity": "low",
                        "file": str(file_path),
                        "message": "Missing Open Graph tags",
                        "recommendation": "Add og:title, og:description for social sharing"
                    })
                    score -= 5
                
                # Multiple H1 tags
                h1_count = content.count('<h1')
                if h1_count > 1:
                    issues.append({
                        "severity": "low",
                        "file": str(file_path),
                        "message": f"Multiple H1 tags ({h1_count})",
                        "recommendation": "Use only one H1 tag per page"
                    })
                    score -= 5
            
            except Exception:
                pass
        
        return {
            "score": max(0, score),
            "issues": issues,
            "summary": f"SEO score: {score}/100"
        }
    
    def _get_grade(self, score: float) -> str:
        """Convert score to grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
