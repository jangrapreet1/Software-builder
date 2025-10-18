"""
Base Agent Interface - Formal contracts for all agents
Provides standardized execution model, telemetry, and error handling
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
from datetime import datetime
from enum import Enum
import traceback
import time


class AgentStatus(Enum):
    """Agent execution status"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentCapability(Enum):
    """Agent capabilities"""
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    PROBLEM_RESOLUTION = "problem_resolution"
    TESTING = "testing"
    INTEGRATION = "integration"
    COORDINATION = "coordination"


class ExecutionContext:
    """Context passed to agent during execution"""
    
    def __init__(
        self,
        build_id: str,
        request_data: Dict,
        shared_state: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ):
        self.build_id = build_id
        self.request_data = request_data
        self.shared_state = shared_state or {}
        self.metadata = metadata or {}
        self.start_time = datetime.utcnow()
        self.telemetry: List[Dict] = []
    
    def add_telemetry(self, event: str, data: Optional[Dict] = None):
        """Add telemetry event"""
        self.telemetry.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event,
            "data": data or {}
        })
    
    def get_duration(self) -> float:
        """Get execution duration in seconds"""
        return (datetime.utcnow() - self.start_time).total_seconds()


class ExecutionResult:
    """Standardized agent execution result"""
    
    def __init__(
        self,
        status: AgentStatus,
        output: Any,
        metadata: Optional[Dict] = None,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        telemetry: Optional[List[Dict]] = None
    ):
        self.status = status
        self.output = output
        self.metadata = metadata or {}
        self.errors = errors or []
        self.warnings = warnings or []
        self.telemetry = telemetry or []
        self.timestamp = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "status": self.status.value,
            "output": self.output,
            "metadata": self.metadata,
            "errors": self.errors,
            "warnings": self.warnings,
            "telemetry": self.telemetry,
            "timestamp": self.timestamp
        }
    
    def is_success(self) -> bool:
        """Check if execution was successful"""
        return self.status == AgentStatus.COMPLETED and not self.errors


class BaseAgent(ABC):
    """
    Base class for all agents with standardized interface
    
    All agents must implement:
    - execute(): Main execution logic
    - get_capabilities(): Agent capabilities
    - validate_input(): Input validation
    """
    
    def __init__(self, llm, settings):
        self.llm = llm
        self.settings = settings
        self.agent_name = self.__class__.__name__
        self.execution_history: List[ExecutionResult] = []
        self._current_status = AgentStatus.IDLE
    
    @abstractmethod
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """
        Execute agent task
        
        Args:
            context: Execution context with input data and shared state
        
        Returns:
            ExecutionResult with status, output, and metadata
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[AgentCapability]:
        """Return list of agent capabilities"""
        pass
    
    @abstractmethod
    def validate_input(self, request_data: Dict) -> tuple[bool, Optional[str]]:
        """
        Validate input data
        
        Returns:
            (is_valid, error_message)
        """
        pass
    
    async def execute_safe(self, context: ExecutionContext) -> ExecutionResult:
        """
        Execute with error handling and telemetry
        
        Wraps execute() with:
        - Status tracking
        - Error handling
        - Telemetry collection
        - History recording
        """
        self._current_status = AgentStatus.RUNNING
        context.add_telemetry("agent_started", {"agent": self.agent_name})
        
        start_time = time.time()
        result = None
        
        try:
            # Validate input
            is_valid, error_msg = self.validate_input(context.request_data)
            if not is_valid:
                result = ExecutionResult(
                    status=AgentStatus.FAILED,
                    output=None,
                    errors=[f"Input validation failed: {error_msg}"],
                    telemetry=context.telemetry
                )
                self._current_status = AgentStatus.FAILED
                return result
            
            # Execute main logic
            result = await self.execute(context)
            
            # Add execution metadata
            result.metadata.update({
                "agent": self.agent_name,
                "execution_time": time.time() - start_time,
                "build_id": context.build_id
            })
            
            # Merge telemetry
            result.telemetry.extend(context.telemetry)
            
            self._current_status = result.status
            
        except Exception as e:
            # Handle unexpected errors
            error_trace = traceback.format_exc()
            context.add_telemetry("agent_error", {
                "error": str(e),
                "traceback": error_trace
            })
            
            result = ExecutionResult(
                status=AgentStatus.FAILED,
                output=None,
                errors=[f"Agent execution failed: {str(e)}"],
                metadata={
                    "agent": self.agent_name,
                    "execution_time": time.time() - start_time,
                    "error_trace": error_trace
                },
                telemetry=context.telemetry
            )
            
            self._current_status = AgentStatus.FAILED
        
        finally:
            # Record in history
            if result:
                self.execution_history.append(result)
                context.add_telemetry("agent_completed", {
                    "agent": self.agent_name,
                    "status": result.status.value
                })
        
        return result
    
    def get_status(self) -> AgentStatus:
        """Get current agent status"""
        return self._current_status
    
    def get_execution_history(self, limit: int = 10) -> List[Dict]:
        """Get execution history"""
        return [result.to_dict() for result in self.execution_history[-limit:]]
    
    def get_metrics(self) -> Dict:
        """Get agent performance metrics"""
        if not self.execution_history:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "average_duration": 0.0,
                "error_count": 0
            }
        
        total = len(self.execution_history)
        successful = sum(1 for r in self.execution_history if r.is_success())
        total_duration = sum(
            r.metadata.get("execution_time", 0) 
            for r in self.execution_history
        )
        error_count = sum(len(r.errors) for r in self.execution_history)
        
        return {
            "total_executions": total,
            "success_rate": (successful / total) * 100 if total > 0 else 0.0,
            "average_duration": total_duration / total if total > 0 else 0.0,
            "error_count": error_count,
            "last_execution": self.execution_history[-1].timestamp if self.execution_history else None
        }
    
    def reset_state(self):
        """Reset agent to initial state"""
        self._current_status = AgentStatus.IDLE
    
    def _log(self, level: str, message: str, context: Optional[ExecutionContext] = None):
        """Internal logging helper"""
        log_entry = {
            "level": level,
            "agent": self.agent_name,
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if context:
            context.add_telemetry("log", log_entry)
        
        print(f"[{level.upper()}] {self.agent_name}: {message}")
