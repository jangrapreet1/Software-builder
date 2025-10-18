"""Code Generation Cache - Redis-based caching for LLM outputs"""
import json
import hashlib
from typing import Optional
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class CodeGenerationCache:
    """Cache LLM outputs to reduce costs and latency"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.enabled = REDIS_AVAILABLE
        if self.enabled:
            try:
                self.redis = redis.from_url(redis_url, decode_responses=True)
                self.redis.ping()
            except:
                self.enabled = False
                self.redis = None
        else:
            self.redis = None
    
    async def get_cached_code(self, cache_key: str) -> Optional[dict]:
        """Retrieve cached code"""
        if not self.enabled:
            return None
        try:
            cached = self.redis.get(cache_key)
            return json.loads(cached) if cached else None
        except:
            return None
    
    async def cache_code(self, cache_key: str, code: dict, ttl: int = 86400):
        """Cache code for 24 hours"""
        if not self.enabled:
            return
        try:
            self.redis.setex(cache_key, ttl, json.dumps(code))
        except:
            pass
    
    def generate_cache_key(self, *args) -> str:
        """Generate deterministic cache key"""
        content = json.dumps(args, sort_keys=True)
        return f"codegen:{hashlib.sha256(content.encode()).hexdigest()}"
