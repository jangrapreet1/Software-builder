"""
Error Feedback System - Captures errors and feeds them back to planning
Enables adaptive workflow that learns from failures
"""
from typing import Dict, List, Optional, Set
from datetime import datetime
from pathlib import Path
import json
from collections import defaultdict


class ErrorPattern:
    """Represents a recurring error pattern"""
    
    def __init__(self, category: str, pattern: str, occurrences: int = 1):
        self.category = category
        self.pattern = pattern
        self.occurrences = occurrences
        self.first_seen = datetime.utcnow().isoformat() + "Z"
        self.last_seen = datetime.utcnow().isoformat() + "Z"
        self.affected_builds: Set[str] = set()
        self.suggested_fixes: List[str] = []
    
    def record_occurrence(self, build_id: str):
        """Record another occurrence of this pattern"""
        self.occurrences += 1
        self.last_seen = datetime.utcnow().isoformat() + "Z"
        self.affected_builds.add(build_id)
    
    def add_fix_suggestion(self, fix: str):
        """Add a suggested fix"""
        if fix not in self.suggested_fixes:
            self.suggested_fixes.append(fix)
    
    def to_dict(self) -> Dict:
        return {
            "category": self.category,
            "pattern": self.pattern,
            "occurrences": self.occurrences,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "affected_builds": list(self.affected_builds),
            "suggested_fixes": self.suggested_fixes
        }


class ErrorFeedbackSystem:
    """
    Collects errors from problem resolution and provides feedback to coordinator
    Enables adaptive planning based on historical failures
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path(".sb_artifacts/error_feedback")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Error tracking
        self.error_patterns: Dict[str, ErrorPattern] = {}
        self.build_errors: Dict[str, List[Dict]] = defaultdict(list)
        
        # Load existing patterns
        self._load_patterns()
    
    def record_error(
        self,
        build_id: str,
        error_category: str,
        error_message: str,
        context: Optional[Dict] = None,
        resolution_attempted: bool = False,
        resolution_successful: bool = False
    ):
        """Record an error occurrence"""
        error_entry = {
            "build_id": build_id,
            "category": error_category,
            "message": error_message,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "resolution_attempted": resolution_attempted,
            "resolution_successful": resolution_successful
        }
        
        # Add to build errors
        self.build_errors[build_id].append(error_entry)
        
        # Check if this matches an existing pattern
        pattern_key = f"{error_category}:{self._normalize_error(error_message)}"
        
        if pattern_key in self.error_patterns:
            self.error_patterns[pattern_key].record_occurrence(build_id)
        else:
            # Create new pattern
            self.error_patterns[pattern_key] = ErrorPattern(
                error_category,
                self._normalize_error(error_message)
            )
            self.error_patterns[pattern_key].record_occurrence(build_id)
        
        # Persist
        self._save_patterns()
    
    def record_resolution(
        self,
        build_id: str,
        error_category: str,
        error_message: str,
        fix_applied: str,
        successful: bool
    ):
        """Record a resolution attempt"""
        pattern_key = f"{error_category}:{self._normalize_error(error_message)}"
        
        if pattern_key in self.error_patterns:
            if successful:
                self.error_patterns[pattern_key].add_fix_suggestion(fix_applied)
        
        self._save_patterns()
    
    def get_feedback_for_planning(
        self,
        project_type: Optional[str] = None,
        technologies: Optional[List[str]] = None
    ) -> Dict:
        """
        Get feedback to inform planning phase
        
        Returns insights about common errors and preventive measures
        """
        # Get frequently occurring errors
        frequent_patterns = sorted(
            self.error_patterns.values(),
            key=lambda p: p.occurrences,
            reverse=True
        )[:10]
        
        # Build recommendations
        recommendations = []
        constraint_modifications = []
        
        for pattern in frequent_patterns:
            if pattern.occurrences >= 3:  # Recurring issue
                recommendations.append({
                    "category": pattern.category,
                    "issue": pattern.pattern,
                    "occurrences": pattern.occurrences,
                    "preventive_measures": pattern.suggested_fixes
                })
                
                # Generate constraint modifications
                if pattern.category == "module_dependency":
                    constraint_modifications.append({
                        "type": "dependency_constraint",
                        "description": f"Ensure proper handling of: {pattern.pattern}"
                    })
                elif pattern.category == "syntax":
                    constraint_modifications.append({
                        "type": "code_generation_constraint",
                        "description": f"Add extra validation for: {pattern.pattern}"
                    })
                elif pattern.category == "database":
                    constraint_modifications.append({
                        "type": "database_constraint",
                        "description": "Add robust error handling for database operations"
                    })
        
        return {
            "has_feedback": len(recommendations) > 0,
            "total_patterns": len(self.error_patterns),
            "frequent_issues": recommendations,
            "constraint_modifications": constraint_modifications,
            "summary": self._generate_feedback_summary(frequent_patterns)
        }
    
    def get_build_error_history(self, build_id: str) -> List[Dict]:
        """Get error history for a specific build"""
        return self.build_errors.get(build_id, [])
    
    def get_category_statistics(self) -> Dict:
        """Get statistics by error category"""
        stats = defaultdict(int)
        
        for pattern in self.error_patterns.values():
            stats[pattern.category] += pattern.occurrences
        
        return dict(stats)
    
    def get_resolution_success_rate(self) -> Dict:
        """Calculate resolution success rate by category"""
        category_stats = defaultdict(lambda: {"attempted": 0, "successful": 0})
        
        for build_errors in self.build_errors.values():
            for error in build_errors:
                if error["resolution_attempted"]:
                    category = error["category"]
                    category_stats[category]["attempted"] += 1
                    if error["resolution_successful"]:
                        category_stats[category]["successful"] += 1
        
        # Calculate rates
        rates = {}
        for category, stats in category_stats.items():
            if stats["attempted"] > 0:
                rates[category] = {
                    "attempted": stats["attempted"],
                    "successful": stats["successful"],
                    "success_rate": (stats["successful"] / stats["attempted"]) * 100
                }
        
        return rates
    
    def generate_preventive_spec_additions(self) -> List[Dict]:
        """Generate spec additions to prevent common errors"""
        additions = []
        
        # Analyze patterns and generate preventive specs
        category_counts = self.get_category_statistics()
        
        if category_counts.get("module_dependency", 0) > 5:
            additions.append({
                "spec_type": "dependency_management",
                "addition": {
                    "requirements": "Include version pinning for all dependencies",
                    "validation": "Run dependency check before build"
                }
            })
        
        if category_counts.get("syntax", 0) > 5:
            additions.append({
                "spec_type": "code_quality",
                "addition": {
                    "requirements": "Add syntax validation step",
                    "linting": "Enable strict linting rules"
                }
            })
        
        if category_counts.get("database", 0) > 3:
            additions.append({
                "spec_type": "database",
                "addition": {
                    "requirements": "Add connection pooling and retry logic",
                    "error_handling": "Wrap all database calls in try-except"
                }
            })
        
        if category_counts.get("api_network", 0) > 3:
            additions.append({
                "spec_type": "api_client",
                "addition": {
                    "requirements": "Add timeout and retry mechanisms",
                    "error_handling": "Handle network failures gracefully"
                }
            })
        
        return additions
    
    def clear_build_errors(self, build_id: str):
        """Clear errors for a specific build"""
        if build_id in self.build_errors:
            del self.build_errors[build_id]
    
    def export_analytics(self) -> Dict:
        """Export analytics for monitoring"""
        return {
            "total_error_patterns": len(self.error_patterns),
            "total_builds_tracked": len(self.build_errors),
            "category_distribution": self.get_category_statistics(),
            "resolution_success_rates": self.get_resolution_success_rate(),
            "top_patterns": [
                p.to_dict() for p in sorted(
                    self.error_patterns.values(),
                    key=lambda x: x.occurrences,
                    reverse=True
                )[:20]
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    # Backwards-compatibility analytics expected by tests
    def get_error_analytics(self) -> Dict:
        """Return concise analytics with totals and category breakdown expected by tests."""
        total_errors = sum(len(errs) for errs in self.build_errors.values())
        by_category = self.get_category_statistics()
        # Include a minimal, stable structure while also surfacing a richer snapshot
        return {
            "total_errors": total_errors,
            "by_category": by_category,
            "summary": {
                "total_error_patterns": len(self.error_patterns),
                "total_builds_tracked": len(self.build_errors),
            },
            "top_patterns": [
                p.to_dict() for p in sorted(
                    self.error_patterns.values(),
                    key=lambda x: x.occurrences,
                    reverse=True
                )[:10]
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    
    def _normalize_error(self, error_message: str) -> str:
        """Normalize error message to identify patterns"""
        # Remove specific values, paths, line numbers
        import re
        normalized = error_message.lower()
        normalized = re.sub(r'\d+', 'N', normalized)  # Replace numbers
        normalized = re.sub(r'/[^\s]+', 'PATH', normalized)  # Replace paths
        normalized = re.sub(r"'[^']+'", 'VALUE', normalized)  # Replace quoted values
        return normalized[:200]  # Limit length
    
    def _generate_feedback_summary(self, patterns: List[ErrorPattern]) -> str:
        """Generate human-readable summary"""
        if not patterns:
            return "No significant error patterns detected"
        
        summary_parts = []
        
        # Count by category
        category_counts = defaultdict(int)
        for pattern in patterns:
            category_counts[pattern.category] += 1
        
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            summary_parts.append(f"{count} {category} issue(s)")
        
        return "Common issues: " + ", ".join(summary_parts)
    
    def _load_patterns(self):
        """Load error patterns from disk"""
        patterns_file = self.storage_path / "error_patterns.json"
        
        if patterns_file.exists():
            try:
                with open(patterns_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for key, pattern_data in data.items():
                    pattern = ErrorPattern(
                        pattern_data["category"],
                        pattern_data["pattern"],
                        pattern_data["occurrences"]
                    )
                    pattern.first_seen = pattern_data["first_seen"]
                    pattern.last_seen = pattern_data["last_seen"]
                    pattern.affected_builds = set(pattern_data.get("affected_builds", []))
                    pattern.suggested_fixes = pattern_data.get("suggested_fixes", [])
                    self.error_patterns[key] = pattern
                    
            except Exception as e:
                print(f"Warning: Failed to load error patterns: {e}")
    
    def _save_patterns(self):
        """Save error patterns to disk"""
        patterns_file = self.storage_path / "error_patterns.json"
        
        try:
            data = {key: pattern.to_dict() for key, pattern in self.error_patterns.items()}
            
            with open(patterns_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Failed to save error patterns: {e}")
