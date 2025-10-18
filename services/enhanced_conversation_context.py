"""
Enhanced Conversation Context - Phase 3A.3
Improved agent-to-agent communication and context sharing
"""
import json
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class ConversationMessage:
    """Single conversation message"""
    
    def __init__(
        self,
        message_id: str,
        agent_name: str,
        content: str,
        message_type: str,  # request, response, clarification, decision
        context: Optional[Dict] = None,
        references: Optional[List[str]] = None
    ):
        self.message_id = message_id
        self.agent_name = agent_name
        self.content = content
        self.message_type = message_type
        self.context = context or {}
        self.references = references or []
        self.timestamp = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> Dict:
        return {
            "message_id": self.message_id,
            "agent_name": self.agent_name,
            "content": self.content,
            "message_type": self.message_type,
            "context": self.context,
            "references": self.references,
            "timestamp": self.timestamp
        }


class ConversationThread:
    """Conversation thread between agents"""
    
    def __init__(self, thread_id: str, topic: str):
        self.thread_id = thread_id
        self.topic = topic
        self.messages: List[ConversationMessage] = []
        self.participants: List[str] = []
        self.status = "active"  # active, resolved, archived
        self.created_at = datetime.utcnow().isoformat() + "Z"
        self.updated_at = self.created_at
    
    def add_message(self, message: ConversationMessage):
        """Add message to thread"""
        self.messages.append(message)
        if message.agent_name not in self.participants:
            self.participants.append(message.agent_name)
        self.updated_at = datetime.utcnow().isoformat() + "Z"
    
    def get_context_summary(self) -> Dict:
        """Get summary of thread context"""
        return {
            "thread_id": self.thread_id,
            "topic": self.topic,
            "message_count": len(self.messages),
            "participants": self.participants,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def to_dict(self) -> Dict:
        return {
            **self.get_context_summary(),
            "messages": [m.to_dict() for m in self.messages]
        }


class EnhancedConversationContext:
    """
    Enhanced conversation context system with:
    - Full conversation history preservation
    - Context-aware message threading
    - Cross-agent context injection
    """
    
    def __init__(self, storage_path: Path):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Conversation data
        self.threads: Dict[str, ConversationThread] = {}
        self.build_threads: Dict[str, List[str]] = defaultdict(list)  # build_id -> thread_ids
        
        # Load existing threads
        self._load_threads()
    
    def _load_threads(self):
        """Load existing conversation threads"""
        threads_file = self.storage_path / "threads.json"
        if threads_file.exists():
            with open(threads_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for thread_data in data.get("threads", []):
                    thread = ConversationThread(
                        thread_id=thread_data["thread_id"],
                        topic=thread_data["topic"]
                    )
                    thread.status = thread_data["status"]
                    thread.created_at = thread_data["created_at"]
                    thread.updated_at = thread_data["updated_at"]
                    thread.participants = thread_data["participants"]
                    
                    for msg_data in thread_data["messages"]:
                        message = ConversationMessage(
                            message_id=msg_data["message_id"],
                            agent_name=msg_data["agent_name"],
                            content=msg_data["content"],
                            message_type=msg_data["message_type"],
                            context=msg_data.get("context", {}),
                            references=msg_data.get("references", [])
                        )
                        message.timestamp = msg_data["timestamp"]
                        thread.messages.append(message)
                    
                    self.threads[thread.thread_id] = thread
                
                self.build_threads = defaultdict(list, data.get("build_threads", {}))
    
    def _save_threads(self):
        """Save conversation threads"""
        threads_file = self.storage_path / "threads.json"
        with open(threads_file, 'w', encoding='utf-8') as f:
            json.dump({
                "threads": [t.to_dict() for t in self.threads.values()],
                "build_threads": dict(self.build_threads)
            }, f, indent=2)
    
    def create_thread(self, topic: str, build_id: Optional[str] = None) -> str:
        """Create new conversation thread"""
        thread_id = f"thread_{len(self.threads)}_{datetime.utcnow().timestamp()}"
        thread = ConversationThread(thread_id, topic)
        self.threads[thread_id] = thread
        
        if build_id:
            self.build_threads[build_id].append(thread_id)
        
        self._save_threads()
        return thread_id
    
    def add_message(
        self,
        thread_id: str,
        agent_name: str,
        content: str,
        message_type: str = "response",
        context: Optional[Dict] = None,
        references: Optional[List[str]] = None
    ):
        """Add message to thread"""
        if thread_id not in self.threads:
            raise ValueError(f"Thread not found: {thread_id}")
        
        message_id = f"msg_{thread_id}_{len(self.threads[thread_id].messages)}"
        message = ConversationMessage(
            message_id, agent_name, content, message_type, context, references
        )
        
        self.threads[thread_id].add_message(message)
        self._save_threads()
    
    def get_thread(self, thread_id: str) -> Optional[ConversationThread]:
        """Get conversation thread"""
        return self.threads.get(thread_id)
    
    def get_build_threads(self, build_id: str) -> List[ConversationThread]:
        """Get all threads for a build"""
        thread_ids = self.build_threads.get(build_id, [])
        return [self.threads[tid] for tid in thread_ids if tid in self.threads]
    
    def get_agent_context(self, agent_name: str, build_id: Optional[str] = None, limit: int = 10) -> Dict:
        """Get conversation context for an agent"""
        relevant_threads = []
        
        if build_id:
            # Get threads for this build
            relevant_threads = self.get_build_threads(build_id)
        else:
            # Get all threads involving this agent
            for thread in self.threads.values():
                if agent_name in thread.participants:
                    relevant_threads.append(thread)
        
        # Sort by most recent
        relevant_threads.sort(key=lambda t: t.updated_at, reverse=True)
        relevant_threads = relevant_threads[:limit]
        
        # Extract context
        recent_messages = []
        topics = []
        
        for thread in relevant_threads:
            topics.append(thread.topic)
            # Get last few messages from each thread
            for message in thread.messages[-3:]:
                recent_messages.append({
                    "agent": message.agent_name,
                    "content": message.content,
                    "type": message.message_type,
                    "timestamp": message.timestamp
                })
        
        return {
            "agent_name": agent_name,
            "build_id": build_id,
            "recent_threads": len(relevant_threads),
            "topics": list(set(topics)),
            "recent_messages": recent_messages[-10:],  # Last 10 messages
            "context_timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    def inject_context_into_prompt(self, base_prompt: str, agent_name: str, build_id: Optional[str] = None) -> str:
        """Inject relevant context into agent prompt"""
        context = self.get_agent_context(agent_name, build_id)
        
        if not context["recent_messages"]:
            return base_prompt
        
        context_section = "\n## Previous Conversation Context\n\n"
        context_section += "Recent discussions:\n"
        
        for msg in context["recent_messages"]:
            context_section += f"- {msg['agent']} ({msg['type']}): {msg['content'][:100]}...\n"
        
        enhanced_prompt = f"{base_prompt}\n\n{context_section}"
        return enhanced_prompt
    
    def close_thread(self, thread_id: str):
        """Mark thread as resolved"""
        if thread_id in self.threads:
            self.threads[thread_id].status = "resolved"
            self._save_threads()
    
    def get_statistics(self) -> Dict:
        """Get conversation statistics"""
        total_threads = len(self.threads)
        total_messages = sum(len(t.messages) for t in self.threads.values())
        active_threads = sum(1 for t in self.threads.values() if t.status == "active")
        
        # Agent participation
        agent_participation = defaultdict(int)
        for thread in self.threads.values():
            for agent in thread.participants:
                agent_participation[agent] += 1
        
        return {
            "total_threads": total_threads,
            "total_messages": total_messages,
            "active_threads": active_threads,
            "resolved_threads": total_threads - active_threads,
            "agent_participation": dict(agent_participation),
            "builds_with_threads": len(self.build_threads)
        }


# Global instance
_conversation_context = None

def get_conversation_context(storage_path: Optional[Path] = None) -> EnhancedConversationContext:
    """Get or create global conversation context"""
    global _conversation_context
    if _conversation_context is None:
        if storage_path is None:
            storage_path = Path(".sb_artifacts/conversation_context")
        _conversation_context = EnhancedConversationContext(storage_path)
    return _conversation_context
