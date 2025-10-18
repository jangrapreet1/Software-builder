"""
Learning Engine - Enables agents to learn from patterns and improve
"""
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict
from pathlib import Path

from services.agent_memory_system import get_memory_system, MemoryType


class PatternExtractor:
    """Extract patterns from build data"""
    
    def extract_success_pattern(self, build_data: Dict) -> List[Dict]:
        """Extract successful patterns from build"""
        patterns = []
        
        # Architecture pattern
        if "technical_specs" in build_data:
            patterns.append({
                "type": "architecture",
                "pattern": {
                    "backend_framework": build_data.get("technical_specs", {}).get("backend_framework"),
                    "frontend_framework": build_data.get("technical_specs", {}).get("frontend_framework"),
                    "database": build_data.get("technical_specs", {}).get("database"),
                    "authentication": build_data.get("technical_specs", {}).get("authentication")
                },
                "context": {
                    "project_type": build_data.get("project_type"),
                    "complexity": build_data.get("complexity")
                }
            })
        
        # Code pattern
        if "backend_code" in build_data and build_data["backend_code"]:
            patterns.append({
                "type": "code_structure",
                "pattern": {
                    "file_count": len(build_data.get("backend_code", {})),
                    "has_models": "models.py" in build_data.get("backend_code", {}),
                    "has_routes": "routes.py" in build_data.get("backend_code", {}),
                    "has_auth": "auth.py" in build_data.get("backend_code", {})
                },
                "context": {
                    "build_id": build_data.get("build_id")
                }
            })
        
        # Entity pattern
        if "entities" in build_data:
            patterns.append({
                "type": "entity_design",
                "pattern": {
                    "entity_count": len(build_data.get("entities", [])),
                    "entity_types": [e.get("name") for e in build_data.get("entities", [])]
                },
                "context": {
                    "domain": build_data.get("domain", "general")
                }
            })
        
        return patterns
    
    def extract_failure_pattern(self, build_data: Dict, error: str) -> Dict:
        """Extract failure pattern from build"""
        return {
            "type": "build_failure",
            "pattern": {
                "stage": build_data.get("current_step"),
                "error_type": self._classify_error(error),
                "context": {
                    "framework": build_data.get("technical_specs", {}).get("backend_framework"),
                    "complexity": build_data.get("complexity")
                }
            },
            "error_message": error
        }
    
    def _classify_error(self, error: str) -> str:
        """Classify error type"""
        error_lower = error.lower()
        
        if "modulenotfound" in error_lower or "import" in error_lower:
            return "import_error"
        elif "syntax" in error_lower:
            return "syntax_error"
        elif "timeout" in error_lower:
            return "timeout_error"
        elif "authentication" in error_lower or "auth" in error_lower:
            return "auth_error"
        elif "database" in error_lower or "sql" in error_lower:
            return "database_error"
        else:
            return "unknown_error"


class RecommendationEngine:
    """Generate recommendations based on learned patterns"""
    
    def __init__(self):
        self.memory_system = get_memory_system()
    
    def get_recommendations_for_build(self, brief: str, requirements: List[str]) -> Dict:
        """Get recommendations for a new build based on past experience"""
        recommendations = {
            "architecture": None,
            "frameworks": {},
            "entities": [],
            "common_pitfalls": [],
            "best_practices": [],
            "confidence": 0.0
        }
        
        # Search for similar past builds
        search_content = {
            "brief": brief,
            "requirements": requirements
        }
        
        similar_memories = self.memory_system.recall_similar(
            content=search_content,
            memory_type=MemoryType.LONG_TERM,
            limit=5
        )
        
        if similar_memories:
            # Extract patterns from similar successful builds
            for memory in similar_memories:
                if memory.metadata.get("success"):
                    # Get architecture recommendations
                    if "architecture" in memory.content:
                        recommendations["architecture"] = memory.content["architecture"]
                    
                    # Get framework recommendations
                    if "frameworks" in memory.content:
                        recommendations["frameworks"] = memory.content["frameworks"]
            
            recommendations["confidence"] = len(similar_memories) / 5.0
        
        # Get best practices from semantic memory
        best_practices = self.memory_system.recall_by_tags(
            tags=["best_practice", "pattern"],
            memory_type=MemoryType.SEMANTIC,
            limit=10
        )
        
        recommendations["best_practices"] = [
            bp.content.get("practice", "") for bp in best_practices
        ]
        
        # Get common pitfalls
        failure_memories = self.memory_system.recall_by_tags(
            tags=["failure", "error"],
            memory_type=MemoryType.EPISODIC,
            limit=10
        )
        
        recommendations["common_pitfalls"] = [
            {
                "issue": fm.content.get("error_type", "unknown"),
                "solution": fm.content.get("resolution", "")
            }
            for fm in failure_memories
        ]
        
        return recommendations
    
    def get_framework_recommendation(self, project_type: str, requirements: List[str]) -> Dict:
        """Recommend best framework based on project type and requirements"""
        # Search knowledge base for similar projects
        kb = self.memory_system.knowledge_base
        
        # Count successful framework uses by project type
        framework_scores = defaultdict(lambda: {"success": 0, "total": 0})
        
        for pattern_id, pattern in kb.success_patterns.items():
            if pattern["type"] == "architecture":
                framework = pattern["pattern"].get("backend_framework")
                if framework:
                    framework_scores[framework]["success"] += pattern.get("occurrences", 1)
                    framework_scores[framework]["total"] += pattern.get("occurrences", 1)
        
        # Calculate success rates
        recommendations = []
        for framework, scores in framework_scores.items():
            success_rate = scores["success"] / scores["total"] if scores["total"] > 0 else 0
            recommendations.append({
                "framework": framework,
                "success_rate": success_rate,
                "usage_count": scores["total"]
            })
        
        recommendations.sort(key=lambda x: x["success_rate"], reverse=True)
        
        return {
            "recommended": recommendations[0] if recommendations else None,
            "alternatives": recommendations[1:4] if len(recommendations) > 1 else []
        }
    
    def suggest_entities(self, project_description: str) -> List[Dict]:
        """Suggest entities based on similar projects"""
        # Search for similar project descriptions
        search_content = {"description": project_description}
        
        similar = self.memory_system.recall_similar(
            content=search_content,
            memory_type=MemoryType.LONG_TERM,
            limit=3
        )
        
        entity_suggestions = []
        for memory in similar:
            if "entities" in memory.content:
                entity_suggestions.extend(memory.content["entities"])
        
        # Deduplicate and rank by frequency
        entity_counts = defaultdict(int)
        entity_details = {}
        
        for entity in entity_suggestions:
            name = entity.get("name", "")
            if name:
                entity_counts[name] += 1
                entity_details[name] = entity
        
        # Return top entities
        sorted_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {**entity_details[name], "confidence": count / len(similar)}
            for name, count in sorted_entities[:10]
        ]


class AdaptivePromptEngine:
    """Adapt prompts based on learning history"""
    
    def __init__(self):
        self.memory_system = get_memory_system()
    
    def enhance_prompt(self, base_prompt: str, context: Dict) -> str:
        """Enhance prompt with learned knowledge"""
        # Get relevant past experiences
        similar = self.memory_system.recall_similar(
            content=context,
            memory_type=MemoryType.EPISODIC,
            limit=3
        )
        
        # Extract lessons learned
        lessons = []
        for memory in similar:
            if "lessons_learned" in memory.content:
                lessons.extend(memory.content["lessons_learned"])
        
        if lessons:
            lessons_text = "\n".join([f"- {lesson}" for lesson in lessons[:5]])
            enhanced_prompt = f"""{base_prompt}

Based on past experience, keep in mind:
{lessons_text}
"""
            return enhanced_prompt
        
        return base_prompt
    
    def add_constraints_from_failures(self, base_constraints: List[str], context: Dict) -> List[str]:
        """Add constraints based on past failures"""
        # Get failure patterns
        failures = self.memory_system.recall_by_tags(
            tags=["failure", context.get("stage", "unknown")],
            memory_type=MemoryType.EPISODIC,
            limit=5
        )
        
        new_constraints = base_constraints.copy()
        
        for failure in failures:
            if "constraint" in failure.content:
                constraint = failure.content["constraint"]
                if constraint not in new_constraints:
                    new_constraints.append(constraint)
        
        return new_constraints


class LearningEngine:
    """Main learning engine coordinating all learning components"""
    
    def __init__(self):
        self.memory_system = get_memory_system()
        self.pattern_extractor = PatternExtractor()
        self.recommendation_engine = RecommendationEngine()
        self.prompt_engine = AdaptivePromptEngine()
    
    def learn_from_build(self, build_data: Dict, success: bool):
        """Learn from completed build"""
        build_id = build_data.get("build_id")
        
        if success:
            # Extract and store success patterns
            patterns = self.pattern_extractor.extract_success_pattern(build_data)
            
            for pattern in patterns:
                # Add to knowledge base
                self.memory_system.knowledge_base.add_success_pattern(
                    pattern_type=pattern["type"],
                    pattern=pattern["pattern"],
                    context=pattern.get("context")
                )
                
                # Add to semantic memory
                self.memory_system.add_semantic_memory(
                    content={
                        "pattern_type": pattern["type"],
                        "pattern": pattern["pattern"],
                        "success": True
                    },
                    metadata={"build_id": build_id},
                    tags=["success_pattern", pattern["type"]]
                )
            
            # Add episodic memory
            self.memory_system.add_episodic_memory(
                content={
                    "build_id": build_id,
                    "brief": build_data.get("brief"),
                    "result": "success",
                    "duration": build_data.get("duration"),
                    "architecture": build_data.get("technical_specs")
                },
                metadata={"success": True},
                tags=["successful_build", build_data.get("project_type", "unknown")]
            )
            
        else:
            # Extract and store failure patterns
            error = build_data.get("errors", ["Unknown error"])[0]
            failure_pattern = self.pattern_extractor.extract_failure_pattern(build_data, error)
            
            # Add to knowledge base
            self.memory_system.knowledge_base.add_failure_pattern(
                pattern_type=failure_pattern["type"],
                pattern=failure_pattern["pattern"],
                error_message=failure_pattern["error_message"],
                context=failure_pattern["pattern"].get("context")
            )
            
            # Add episodic memory
            self.memory_system.add_episodic_memory(
                content={
                    "build_id": build_id,
                    "brief": build_data.get("brief"),
                    "result": "failure",
                    "error": error,
                    "stage": build_data.get("current_step")
                },
                metadata={"success": False},
                tags=["failed_build", failure_pattern["pattern"]["error_type"]]
            )
        
        # Consolidate short-term memories
        self.memory_system.consolidate_short_to_long_term(build_id, success)
    
    def get_build_recommendations(self, brief: str, requirements: List[str]) -> Dict:
        """Get recommendations for a new build"""
        return self.recommendation_engine.get_recommendations_for_build(brief, requirements)
    
    def enhance_agent_prompt(self, base_prompt: str, context: Dict) -> str:
        """Enhance agent prompt with learned knowledge"""
        return self.prompt_engine.enhance_prompt(base_prompt, context)
    
    def get_statistics(self) -> Dict:
        """Get learning engine statistics"""
        mem_stats = self.memory_system.get_statistics()
        
        return {
            **mem_stats,
            "learning_enabled": True,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


# Global instance
_learning_engine = None

def get_learning_engine() -> LearningEngine:
    """Get or create global learning engine instance"""
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = LearningEngine()
    return _learning_engine
