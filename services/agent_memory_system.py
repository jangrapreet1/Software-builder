"""
Agent Memory & Learning System
Enables agents to learn from past builds and improve over time
"""
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
import pickle


class MemoryType:
    """Types of memory storage"""
    SHORT_TERM = "short_term"  # Current build context
    LONG_TERM = "long_term"    # Cross-build knowledge
    EPISODIC = "episodic"      # Specific build experiences
    SEMANTIC = "semantic"       # General knowledge about patterns


class Memory:
    """Individual memory entry"""
    
    def __init__(
        self,
        memory_id: str,
        memory_type: str,
        content: Dict,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ):
        self.memory_id = memory_id
        self.memory_type = memory_type
        self.content = content
        self.metadata = metadata or {}
        self.tags = tags or []
        self.created_at = datetime.utcnow().isoformat() + "Z"
        self.accessed_count = 0
        self.last_accessed = None
        self.relevance_score = 1.0
    
    def to_dict(self) -> Dict:
        return {
            "memory_id": self.memory_id,
            "memory_type": self.memory_type,
            "content": self.content,
            "metadata": self.metadata,
            "tags": self.tags,
            "created_at": self.created_at,
            "accessed_count": self.accessed_count,
            "last_accessed": self.last_accessed,
            "relevance_score": self.relevance_score
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'Memory':
        memory = Memory(
            memory_id=data["memory_id"],
            memory_type=data["memory_type"],
            content=data["content"],
            metadata=data.get("metadata", {}),
            tags=data.get("tags", [])
        )
        memory.created_at = data.get("created_at", memory.created_at)
        memory.accessed_count = data.get("accessed_count", 0)
        memory.last_accessed = data.get("last_accessed")
        memory.relevance_score = data.get("relevance_score", 1.0)
        return memory
    
    def access(self):
        """Mark memory as accessed"""
        self.accessed_count += 1
        self.last_accessed = datetime.utcnow().isoformat() + "Z"


class BuildKnowledgeBase:
    """
    Stores successful patterns, failure patterns, and solutions
    """
    
    def __init__(self, storage_path: Path):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.success_patterns_file = self.storage_path / "success_patterns.json"
        self.failure_patterns_file = self.storage_path / "failure_patterns.json"
        self.solutions_file = self.storage_path / "solutions.json"
        
        self.success_patterns = self._load_patterns(self.success_patterns_file)
        self.failure_patterns = self._load_patterns(self.failure_patterns_file)
        self.solutions = self._load_patterns(self.solutions_file)
    
    def _load_patterns(self, file_path: Path) -> Dict:
        """Load patterns from file"""
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_patterns(self, patterns: Dict, file_path: Path):
        """Save patterns to file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(patterns, f, indent=2)
    
    def add_success_pattern(
        self,
        pattern_type: str,
        pattern: Dict,
        context: Optional[Dict] = None
    ):
        """Add a successful pattern"""
        pattern_id = self._generate_pattern_id(pattern_type, pattern)
        
        if pattern_id not in self.success_patterns:
            self.success_patterns[pattern_id] = {
                "type": pattern_type,
                "pattern": pattern,
                "context": context or {},
                "occurrences": 1,
                "success_rate": 1.0,
                "first_seen": datetime.utcnow().isoformat() + "Z",
                "last_seen": datetime.utcnow().isoformat() + "Z"
            }
        else:
            # Update existing pattern
            self.success_patterns[pattern_id]["occurrences"] += 1
            self.success_patterns[pattern_id]["last_seen"] = datetime.utcnow().isoformat() + "Z"
        
        self._save_patterns(self.success_patterns, self.success_patterns_file)
    
    def add_failure_pattern(
        self,
        pattern_type: str,
        pattern: Dict,
        error_message: str,
        context: Optional[Dict] = None,
        resolution: Optional[str] = None
    ):
        """Add a failure pattern"""
        pattern_id = self._generate_pattern_id(pattern_type, pattern)
        
        if pattern_id not in self.failure_patterns:
            self.failure_patterns[pattern_id] = {
                "type": pattern_type,
                "pattern": pattern,
                "error_message": error_message,
                "context": context or {},
                "resolution": resolution,
                "occurrences": 1,
                "first_seen": datetime.utcnow().isoformat() + "Z",
                "last_seen": datetime.utcnow().isoformat() + "Z"
            }
        else:
            self.failure_patterns[pattern_id]["occurrences"] += 1
            self.failure_patterns[pattern_id]["last_seen"] = datetime.utcnow().isoformat() + "Z"
            if resolution:
                self.failure_patterns[pattern_id]["resolution"] = resolution
        
        self._save_patterns(self.failure_patterns, self.failure_patterns_file)
    
    def add_solution(
        self,
        problem_type: str,
        problem: str,
        solution: str,
        success: bool,
        metadata: Optional[Dict] = None
    ):
        """Add a solution to the knowledge base"""
        solution_id = self._generate_pattern_id(problem_type, {"problem": problem})
        
        if solution_id not in self.solutions:
            self.solutions[solution_id] = {
                "problem_type": problem_type,
                "problem": problem,
                "solutions": [],
                "first_seen": datetime.utcnow().isoformat() + "Z"
            }
        
        self.solutions[solution_id]["solutions"].append({
            "solution": solution,
            "success": success,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
        self._save_patterns(self.solutions, self.solutions_file)
    
    def _generate_pattern_id(self, pattern_type: str, pattern: Dict) -> str:
        """Generate unique pattern ID"""
        pattern_str = f"{pattern_type}:{json.dumps(pattern, sort_keys=True)}"
        return hashlib.sha256(pattern_str.encode()).hexdigest()[:16]
    
    def search_similar_patterns(
        self,
        pattern_type: str,
        pattern: Dict,
        pattern_source: str = "success"
    ) -> List[Dict]:
        """Search for similar patterns"""
        source = self.success_patterns if pattern_source == "success" else self.failure_patterns
        
        similar = []
        for pattern_id, stored_pattern in source.items():
            if stored_pattern["type"] == pattern_type:
                # Simple similarity check (can be enhanced with semantic similarity)
                similarity = self._calculate_similarity(pattern, stored_pattern["pattern"])
                if similarity > 0.5:  # Threshold
                    similar.append({
                        **stored_pattern,
                        "pattern_id": pattern_id,
                        "similarity": similarity
                    })
        
        return sorted(similar, key=lambda x: x["similarity"], reverse=True)
    
    def _calculate_similarity(self, pattern1: Dict, pattern2: Dict) -> float:
        """Calculate pattern similarity (simple version)"""
        # Convert to sets of keys
        keys1 = set(json.dumps(pattern1, sort_keys=True))
        keys2 = set(json.dumps(pattern2, sort_keys=True))
        
        if not keys1 or not keys2:
            return 0.0
        
        intersection = len(keys1.intersection(keys2))
        union = len(keys1.union(keys2))
        
        return intersection / union if union > 0 else 0.0
    
    def get_best_solutions(self, problem_type: str, problem: str, limit: int = 5) -> List[Dict]:
        """Get best solutions for a problem"""
        all_solutions = []
        
        for solution_id, solution_data in self.solutions.items():
            if solution_data["problem_type"] == problem_type:
                # Calculate success rate
                successful = sum(1 for s in solution_data["solutions"] if s["success"])
                total = len(solution_data["solutions"])
                success_rate = successful / total if total > 0 else 0
                
                if success_rate > 0:
                    all_solutions.append({
                        **solution_data,
                        "success_rate": success_rate,
                        "total_attempts": total
                    })
        
        return sorted(all_solutions, key=lambda x: x["success_rate"], reverse=True)[:limit]


class AgentMemorySystem:
    """
    Complete agent memory system with short-term, long-term, episodic, and semantic memory
    """
    
    def __init__(self, storage_path: Path):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Memory stores
        self.short_term_memory: Dict[str, List[Memory]] = defaultdict(list)  # By build_id
        self.long_term_memory: List[Memory] = []
        self.episodic_memory: List[Memory] = []
        self.semantic_memory: List[Memory] = []
        
        # Knowledge base
        self.knowledge_base = BuildKnowledgeBase(self.storage_path / "knowledge_base")
        
        # Load persisted memories
        self._load_memories()
    
    def _load_memories(self):
        """Load persisted memories"""
        long_term_file = self.storage_path / "long_term_memory.json"
        episodic_file = self.storage_path / "episodic_memory.json"
        semantic_file = self.storage_path / "semantic_memory.json"
        
        if long_term_file.exists():
            with open(long_term_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.long_term_memory = [Memory.from_dict(m) for m in data]
        
        if episodic_file.exists():
            with open(episodic_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.episodic_memory = [Memory.from_dict(m) for m in data]
        
        if semantic_file.exists():
            with open(semantic_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.semantic_memory = [Memory.from_dict(m) for m in data]
    
    def _save_memories(self):
        """Save memories to disk"""
        long_term_file = self.storage_path / "long_term_memory.json"
        episodic_file = self.storage_path / "episodic_memory.json"
        semantic_file = self.storage_path / "semantic_memory.json"
        
        with open(long_term_file, 'w', encoding='utf-8') as f:
            json.dump([m.to_dict() for m in self.long_term_memory], f, indent=2)
        
        with open(episodic_file, 'w', encoding='utf-8') as f:
            json.dump([m.to_dict() for m in self.episodic_memory], f, indent=2)
        
        with open(semantic_file, 'w', encoding='utf-8') as f:
            json.dump([m.to_dict() for m in self.semantic_memory], f, indent=2)
    
    def add_short_term_memory(self, build_id: str, content: Dict, tags: Optional[List[str]] = None):
        """Add to short-term memory (current build)"""
        memory_id = f"stm_{build_id}_{len(self.short_term_memory[build_id])}"
        memory = Memory(memory_id, MemoryType.SHORT_TERM, content, tags=tags)
        self.short_term_memory[build_id].append(memory)
    
    def add_long_term_memory(self, content: Dict, metadata: Optional[Dict] = None, tags: Optional[List[str]] = None):
        """Add to long-term memory (cross-build knowledge)"""
        memory_id = f"ltm_{len(self.long_term_memory)}"
        memory = Memory(memory_id, MemoryType.LONG_TERM, content, metadata, tags)
        self.long_term_memory.append(memory)
        self._save_memories()
    
    def add_episodic_memory(self, content: Dict, metadata: Optional[Dict] = None, tags: Optional[List[str]] = None):
        """Add episodic memory (specific build experience)"""
        memory_id = f"epi_{len(self.episodic_memory)}"
        memory = Memory(memory_id, MemoryType.EPISODIC, content, metadata, tags)
        self.episodic_memory.append(memory)
        self._save_memories()
    
    def add_semantic_memory(self, content: Dict, metadata: Optional[Dict] = None, tags: Optional[List[str]] = None):
        """Add semantic memory (general patterns/knowledge)"""
        memory_id = f"sem_{len(self.semantic_memory)}"
        memory = Memory(memory_id, MemoryType.SEMANTIC, content, metadata, tags)
        self.semantic_memory.append(memory)
        self._save_memories()
    
    def recall_short_term(self, build_id: str, limit: int = 10) -> List[Memory]:
        """Recall recent short-term memories"""
        memories = self.short_term_memory.get(build_id, [])
        return memories[-limit:]
    
    def recall_by_tags(self, tags: List[str], memory_type: Optional[str] = None, limit: int = 10) -> List[Memory]:
        """Recall memories by tags"""
        all_memories = []
        
        if not memory_type or memory_type == MemoryType.LONG_TERM:
            all_memories.extend(self.long_term_memory)
        if not memory_type or memory_type == MemoryType.EPISODIC:
            all_memories.extend(self.episodic_memory)
        if not memory_type or memory_type == MemoryType.SEMANTIC:
            all_memories.extend(self.semantic_memory)
        
        # Filter by tags
        matching = []
        for memory in all_memories:
            if any(tag in memory.tags for tag in tags):
                memory.access()
                matching.append(memory)
        
        # Sort by relevance and access count
        matching.sort(key=lambda m: (m.relevance_score, m.accessed_count), reverse=True)
        
        return matching[:limit]
    
    def recall_similar(self, content: Dict, memory_type: Optional[str] = None, limit: int = 5) -> List[Memory]:
        """Recall similar memories based on content"""
        all_memories = []
        
        if not memory_type or memory_type == MemoryType.LONG_TERM:
            all_memories.extend(self.long_term_memory)
        if not memory_type or memory_type == MemoryType.EPISODIC:
            all_memories.extend(self.episodic_memory)
        if not memory_type or memory_type == MemoryType.SEMANTIC:
            all_memories.extend(self.semantic_memory)
        
        # Calculate similarity for each memory
        scored_memories = []
        for memory in all_memories:
            similarity = self._calculate_content_similarity(content, memory.content)
            if similarity > 0.3:  # Threshold
                scored_memories.append((memory, similarity))
        
        # Sort by similarity
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        
        # Access and return
        result = []
        for memory, similarity in scored_memories[:limit]:
            memory.access()
            result.append(memory)
        
        return result
    
    def _calculate_content_similarity(self, content1: Dict, content2: Dict) -> float:
        """Calculate content similarity"""
        # Simple JSON-based similarity
        str1 = json.dumps(content1, sort_keys=True)
        str2 = json.dumps(content2, sort_keys=True)
        
        set1 = set(str1.split())
        set2 = set(str2.split())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def consolidate_short_to_long_term(self, build_id: str, success: bool):
        """Move successful short-term memories to long-term"""
        if build_id not in self.short_term_memory:
            return
        
        for memory in self.short_term_memory[build_id]:
            # Convert to long-term memory
            self.add_long_term_memory(
                content=memory.content,
                metadata={
                    **memory.metadata,
                    "build_id": build_id,
                    "success": success,
                    "original_memory_id": memory.memory_id
                },
                tags=memory.tags
            )
        
        # Clear short-term memory for this build
        del self.short_term_memory[build_id]
    
    def get_statistics(self) -> Dict:
        """Get memory system statistics"""
        total_short_term = sum(len(memories) for memories in self.short_term_memory.values())
        
        return {
            "short_term_memories": total_short_term,
            "long_term_memories": len(self.long_term_memory),
            "episodic_memories": len(self.episodic_memory),
            "semantic_memories": len(self.semantic_memory),
            "total_memories": total_short_term + len(self.long_term_memory) + 
                            len(self.episodic_memory) + len(self.semantic_memory),
            "success_patterns": len(self.knowledge_base.success_patterns),
            "failure_patterns": len(self.knowledge_base.failure_patterns),
            "solutions": len(self.knowledge_base.solutions)
        }


# Global instance
_memory_system = None

def get_memory_system(storage_path: Optional[Path] = None) -> AgentMemorySystem:
    """Get or create global memory system instance"""
    global _memory_system
    if _memory_system is None:
        if storage_path is None:
            storage_path = Path(".sb_artifacts/agent_memory")
        _memory_system = AgentMemorySystem(storage_path)
    return _memory_system
