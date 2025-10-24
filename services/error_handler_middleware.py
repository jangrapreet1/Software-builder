"""
Enhanced Error Handling Middleware
Provides comprehensive error tracking, logging, and recovery mechanisms
"""
import traceback
from typing import Callable, Optional
from datetime import datetime
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from services.metrics_collector import get_metrics_collector
from services.audit_logger import audit_logger, AuditEventType


class ErrorCategory:
    """Error categories for classification"""
    VALIDATION = "validation_error"
    AUTHENTICATION = "authentication_error"
    AUTHORIZATION = "authorization_error"
    NOT_FOUND = "not_found_error"
    RATE_LIMIT = "rate_limit_error"
    EXTERNAL_SERVICE = "external_service_error"
    DATABASE = "database_error"
    FILE_SYSTEM = "file_system_error"
    NETWORK = "network_error"
    TIMEOUT = "timeout_error"
    INTERNAL = "internal_error"
    UNKNOWN = "unknown_error"


class ErrorContext:
    """Context information for errors"""
    
    def __init__(
        self,
        category: str,
        message: str,
        request_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        stack_trace: Optional[str] = None,
        metadata: Optional[dict] = None
    ):
        self.category = category
        self.message = message
        self.request_id = request_id
        self.endpoint = endpoint
        self.method = method
        self.status_code = status_code
        self.user_id = user_id
        self.session_id = session_id
        self.stack_trace = stack_trace
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "category": self.category,
            "message": self.message,
            "request_id": self.request_id,
            "endpoint": self.endpoint,
            "method": self.method,
            "status_code": self.status_code,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "stack_trace": self.stack_trace,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() + "Z"
        }


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Enhanced error handling middleware
    
    Features:
    - Automatic error categorization
    - Metrics collection for error rates
    - Audit logging of errors
    - Structured error responses
    - Stack trace capture (dev mode)
    - Request context preservation
    """
    
    def __init__(
        self,
        app: ASGIApp,
        debug: bool = False,
        metrics_enabled: bool = True,
        audit_enabled: bool = True
    ):
        super().__init__(app)
        self.debug = debug
        self.metrics_enabled = metrics_enabled
        self.audit_enabled = audit_enabled
        self.metrics_collector = get_metrics_collector() if metrics_enabled else None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with enhanced error handling
        """
        request_id = self._generate_request_id()
        request.state.request_id = request_id
        
        try:
            # Track request
            if self.metrics_enabled:
                self.metrics_collector.increment_counter(
                    "http.requests.total",
                    labels={"method": request.method, "endpoint": request.url.path}
                )
            
            # Process request
            response = await call_next(request)
            
            # If the downstream produced an error response (e.g., HTTPException handled by FastAPI),
            # convert it into our structured error format
            if response.status_code >= 400:
                class _HTTPStatusError(Exception):
                    def __init__(self, status_code: int, message: str = ""):
                        super().__init__(message or f"HTTP {status_code}")
                        self.status_code = status_code

                return await self._handle_error(
                    request,
                    _HTTPStatusError(response.status_code),
                    request_id,
                )

            # Track response
            if self.metrics_enabled:
                self.metrics_collector.increment_counter(
                    "http.responses.total",
                    labels={
                        "method": request.method,
                        "endpoint": request.url.path,
                        "status_code": str(response.status_code)
                    }
                )
            
            return response
            
        except Exception as exc:
            # Handle error
            return await self._handle_error(request, exc, request_id)
    
    async def _handle_error(
        self,
        request: Request,
        exc: Exception,
        request_id: str
    ) -> JSONResponse:
        """
        Handle and categorize errors
        """
        # Categorize error
        category = self._categorize_error(exc)
        status_code = self._get_status_code(exc, category)
        
        # Get user context if available
        user_id = getattr(request.state, "user_id", None)
        session_id = getattr(request.state, "session_id", None)
        
        # Capture stack trace in debug mode
        stack_trace = None
        if self.debug:
            stack_trace = traceback.format_exc()
        
        # Create error context
        error_context = ErrorContext(
            category=category,
            message=str(exc),
            request_id=request_id,
            endpoint=request.url.path,
            method=request.method,
            status_code=status_code,
            user_id=user_id,
            session_id=session_id,
            stack_trace=stack_trace,
            metadata={
                "query_params": dict(request.query_params),
                "headers": dict(request.headers)
            }
        )
        
        # Log error
        self._log_error(error_context)
        
        # Track metrics
        if self.metrics_enabled:
            self.metrics_collector.increment_counter(
                "http.errors.total",
                labels={
                    "category": category,
                    "status_code": str(status_code),
                    "endpoint": request.url.path
                }
            )
        
        # Audit log using a supported event type (no generic ERROR in enum)
        if self.audit_enabled:
            try:
                event_type = getattr(AuditEventType, "SECURITY_VIOLATION", None)
                if event_type is not None:
                    audit_logger.log_event(
                        event_type=event_type,
                        details={
                            "category": category,
                            "message": str(exc),
                            "endpoint": request.url.path,
                            "status_code": status_code,
                        },
                        user=user_id or "anonymous",
                        success=False,
                    )
            except Exception:
                # Never let audit failures impact error responses
                pass
        
        # Build response
        error_response = {
            "error": {
                "category": category,
                "message": self._sanitize_error_message(str(exc), category),
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        # Include stack trace in debug mode
        if self.debug and stack_trace:
            error_response["error"]["stack_trace"] = stack_trace
        
        return JSONResponse(
            status_code=status_code,
            content=error_response
        )
    
    def _categorize_error(self, exc: Exception) -> str:
        """Categorize error by type"""
        exc_type = type(exc).__name__
        exc_msg = str(exc).lower()
        
        # Validation errors
        if "validation" in exc_msg or "invalid" in exc_msg:
            return ErrorCategory.VALIDATION
        
        # Authentication errors
        if "auth" in exc_msg or "unauthorized" in exc_msg:
            return ErrorCategory.AUTHENTICATION
        
        # Authorization errors
        if "permission" in exc_msg or "forbidden" in exc_msg:
            return ErrorCategory.AUTHORIZATION
        
        # Not found errors
        if "not found" in exc_msg or exc_type == "NotFoundError":
            return ErrorCategory.NOT_FOUND
        
        # Rate limit errors
        if "rate limit" in exc_msg or "too many" in exc_msg:
            return ErrorCategory.RATE_LIMIT
        
        # External service errors
        if "api" in exc_msg or "service" in exc_msg or "connection" in exc_msg:
            return ErrorCategory.EXTERNAL_SERVICE
        
        # Database errors
        if "database" in exc_msg or "sql" in exc_msg:
            return ErrorCategory.DATABASE
        
        # File system errors
        if "file" in exc_msg or "directory" in exc_msg or "path" in exc_msg:
            return ErrorCategory.FILE_SYSTEM
        
        # Network errors
        if "network" in exc_msg or "socket" in exc_msg:
            return ErrorCategory.NETWORK
        
        # Timeout errors
        if "timeout" in exc_msg or "timed out" in exc_msg:
            return ErrorCategory.TIMEOUT
        
        return ErrorCategory.INTERNAL
    
    def _get_status_code(self, exc: Exception, category: str) -> int:
        """Get appropriate HTTP status code"""
        # Check if exception has status_code attribute
        if hasattr(exc, "status_code"):
            return exc.status_code
        
        # Map categories to status codes
        category_status_map = {
            ErrorCategory.VALIDATION: status.HTTP_400_BAD_REQUEST,
            ErrorCategory.AUTHENTICATION: status.HTTP_401_UNAUTHORIZED,
            ErrorCategory.AUTHORIZATION: status.HTTP_403_FORBIDDEN,
            ErrorCategory.NOT_FOUND: status.HTTP_404_NOT_FOUND,
            ErrorCategory.RATE_LIMIT: status.HTTP_429_TOO_MANY_REQUESTS,
            ErrorCategory.EXTERNAL_SERVICE: status.HTTP_502_BAD_GATEWAY,
            ErrorCategory.DATABASE: status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCategory.FILE_SYSTEM: status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCategory.NETWORK: status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCategory.TIMEOUT: status.HTTP_504_GATEWAY_TIMEOUT,
            ErrorCategory.INTERNAL: status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCategory.UNKNOWN: status.HTTP_500_INTERNAL_SERVER_ERROR,
        }
        
        return category_status_map.get(category, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _sanitize_error_message(self, message: str, category: str) -> str:
        """
        Sanitize error message for production
        Removes sensitive information
        """
        if not self.debug:
            # Generic messages for security
            if category == ErrorCategory.INTERNAL:
                return "An internal error occurred. Please contact support."
            elif category == ErrorCategory.DATABASE:
                return "A database error occurred. Please try again later."
            elif category == ErrorCategory.EXTERNAL_SERVICE:
                return "An external service is unavailable. Please try again later."
        
        return message
    
    def _log_error(self, error_context: ErrorContext):
        """Log error with full context"""
        log_entry = f"[ERROR] {error_context.category} - {error_context.message}"
        log_entry += f"\n  Request ID: {error_context.request_id}"
        log_entry += f"\n  Endpoint: {error_context.method} {error_context.endpoint}"
        log_entry += f"\n  Status Code: {error_context.status_code}"
        
        if error_context.user_id:
            log_entry += f"\n  User ID: {error_context.user_id}"
        
        if error_context.session_id:
            log_entry += f"\n  Session ID: {error_context.session_id}"
        
        if error_context.stack_trace and self.debug:
            log_entry += f"\n  Stack Trace:\n{error_context.stack_trace}"
        
        print(log_entry)
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        import uuid
        return str(uuid.uuid4())


def add_error_handling(app, debug: bool = False):
    """
    Add error handling middleware to FastAPI app
    
    Usage:
        from services.error_handler_middleware import add_error_handling
        
        app = FastAPI()
        add_error_handling(app, debug=True)
    """
    app.add_middleware(
        ErrorHandlerMiddleware,
        debug=debug,
        metrics_enabled=True,
        audit_enabled=True
    )
