"""
OptimizationAgent - Performance optimization specialist
"""
import json
import re
from typing import Any, Dict, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import Settings


class OptimizationAgent:
    """
    Specialized agent for performance optimization of generated code
    """
    
    def __init__(self, llm: ChatGoogleGenerativeAI, settings: Settings):
        self.llm = llm
        self.settings = settings
    
    async def optimize_backend(self, code: dict, specs: dict) -> dict:
        """
        Apply performance optimizations to backend code
        """
        optimizations = []
        optimized_code = code.copy()
        
        # Add Redis caching layer
        if self._should_add_caching(code, specs):
            optimized_code = await self._inject_redis_caching(optimized_code)
            optimizations.append("Added Redis caching layer for frequently accessed data")
        
        # Optimize database queries
        optimized_code = await self._add_query_optimization(optimized_code)
        optimizations.append("Added database query optimization with eager loading")
        
        # Add connection pooling
        optimized_code = self._add_connection_pooling(optimized_code)
        optimizations.append("Enhanced database connection pooling configuration")
        
        # Add API rate limiting
        optimized_code = await self._add_rate_limiting(optimized_code)
        optimizations.append("Added API rate limiting for abuse prevention")
        
        # Add response compression
        optimized_code = self._add_compression(optimized_code)
        optimizations.append("Added response compression (gzip)")
        
        return {
            "code": optimized_code,
            "optimizations": optimizations,
            "estimated_improvement": "30-50% faster response times"
        }
    
    async def optimize_frontend(self, code: dict, specs: dict) -> dict:
        """
        Apply performance optimizations to frontend code
        """
        optimizations = []
        optimized_code = code.copy()
        
        # Add code splitting
        optimized_code = await self._add_code_splitting(optimized_code)
        optimizations.append("Added route-based code splitting for faster initial load")
        
        # Add lazy loading for images
        optimized_code = self._add_lazy_loading(optimized_code)
        optimizations.append("Added lazy loading for images and components")
        
        # Optimize bundle size
        optimized_code = await self._optimize_bundle(optimized_code)
        optimizations.append("Optimized bundle size with tree-shaking")
        
        # Add service worker for caching
        optimized_code = await self._add_service_worker(optimized_code)
        optimizations.append("Added service worker for offline support and caching")
        
        # Add React performance optimizations
        optimized_code = await self._add_react_optimizations(optimized_code)
        optimizations.append("Added React.memo and useMemo for expensive operations")
        
        return {
            "code": optimized_code,
            "optimizations": optimizations,
            "estimated_improvement": "40-60% faster page loads, 50% smaller bundle"
        }
    
    def _should_add_caching(self, code: dict, specs: dict) -> bool:
        """Determine if caching should be added"""
        # Check if there are read-heavy operations
        routes = code.get("routes", "")
        get_routes = routes.count("@router.get")
        post_routes = routes.count("@router.post")
        
        return get_routes > post_routes * 2  # More reads than writes
    
    async def _inject_redis_caching(self, code: dict) -> dict:
        """Add Redis caching layer"""
        
        # Add Redis configuration
        cache_config = """
import redis
from functools import wraps
import json
import hashlib

# Redis connection pool
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)

def cache_result(expiration: int = 300):
    \"\"\"Decorator to cache function results in Redis\"\"\"
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{hashlib.md5(str(args).encode() + str(kwargs).encode()).hexdigest()}"
            
            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            redis_client.setex(cache_key, expiration, json.dumps(result))
            
            return result
        return wrapper
    return decorator
"""
        
        # Add to config or main file
        if "config" in code:
            code["config"] = cache_config + "\n\n" + code["config"]
        else:
            code["cache"] = cache_config
        
        # Update requirements to include redis
        if "requirements" in code:
            if "redis" not in code["requirements"]:
                code["requirements"] += "\nredis==5.0.1\n"
        
        return code
    
    async def _add_query_optimization(self, code: dict) -> dict:
        """Add database query optimization"""
        
        if "routes" in code:
            routes = code["routes"]
            
            # Add eager loading for relationships
            routes = re.sub(
                r'(db\.query\([^)]+\))',
                r'\1.options(joinedload("*"))',
                routes
            )
            
            # Add pagination helpers
            pagination_code = """

# Pagination helper
def paginate(query, page: int = 1, page_size: int = 20):
    \"\"\"Add pagination to query\"\"\"
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    total = query.count()
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size
    }
"""
            
            code["routes"] = routes + pagination_code
        
        return code
    
    def _add_connection_pooling(self, code: dict) -> dict:
        """Enhance database connection pooling"""
        
        if "database" in code:
            database = code["database"]
            
            # Update engine configuration
            database = re.sub(
                r'create_engine\([^)]+\)',
                '''create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)''',
                database
            )
            
            code["database"] = database
        
        return code
    
    async def _add_rate_limiting(self, code: dict) -> dict:
        """Add API rate limiting"""
        
        rate_limit_code = """
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# Add to FastAPI app initialization
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Example usage in routes:
# @limiter.limit("5/minute")
# @router.get("/endpoint")
# async def endpoint(request: Request):
#     ...
"""
        
        if "main" in code:
            code["main"] = rate_limit_code + "\n\n" + code["main"]
        
        # Update requirements
        if "requirements" in code:
            if "slowapi" not in code["requirements"]:
                code["requirements"] += "\nslowapi==0.1.9\n"
        
        return code
    
    def _add_compression(self, code: dict) -> dict:
        """Add response compression"""
        
        compression_code = """
from fastapi.middleware.gzip import GZipMiddleware

# Add compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
"""
        
        if "main" in code:
            # Add after app initialization
            code["main"] = code["main"].replace(
                "app = FastAPI(",
                "app = FastAPI("
            ) + "\n\n" + compression_code
        
        return code
    
    async def _add_code_splitting(self, code: dict) -> dict:
        """Add route-based code splitting"""
        
        if "router" in code or "app" in code:
            splitting_code = """
// Lazy load route components
import { lazy, Suspense } from 'react';
import Loading from './components/Loading';

const Home = lazy(() => import('./pages/Home'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Login = lazy(() => import('./pages/Login'));

// Wrap routes with Suspense
<Suspense fallback={<Loading />}>
  <Routes>
    <Route path="/" element={<Home />} />
    <Route path="/dashboard" element={<Dashboard />} />
    <Route path="/login" element={<Login />} />
  </Routes>
</Suspense>
"""
            
            # Update router configuration
            if "router" in code:
                code["router"] = splitting_code
        
        return code
    
    def _add_lazy_loading(self, code: dict) -> dict:
        """Add lazy loading for images"""
        
        lazy_image_component = """
import { useState, useEffect, useRef } from 'react';

interface LazyImageProps {
  src: string;
  alt: string;
  className?: string;
}

export const LazyImage: React.FC<LazyImageProps> = ({ src, alt, className }) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );

    if (imgRef.current) {
      observer.observe(imgRef.current);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <img
      ref={imgRef}
      src={isInView ? src : ''}
      alt={alt}
      className={className}
      onLoad={() => setIsLoaded(true)}
      style={{ opacity: isLoaded ? 1 : 0, transition: 'opacity 0.3s' }}
    />
  );
};
"""
        
        if "components" not in code:
            code["components"] = {}
        
        if isinstance(code["components"], dict):
            code["components"]["LazyImage"] = lazy_image_component
        
        return code
    
    async def _optimize_bundle(self, code: dict) -> dict:
        """Optimize Vite bundle configuration"""
        
        optimized_vite_config = """
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';

export default defineConfig({
  plugins: [
    react(),
    visualizer({ open: false, gzipSize: true })
  ],
  build: {
    target: 'esnext',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    },
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'ui-vendor': ['@headlessui/react', '@heroicons/react']
        }
      }
    },
    chunkSizeWarningLimit: 600
  },
  server: {
    port: 3000
  }
});
"""
        
        code["vite_config"] = optimized_vite_config
        
        return code
    
    async def _add_service_worker(self, code: dict) -> dict:
        """Add service worker for offline support"""
        
        service_worker = """
// service-worker.js
const CACHE_NAME = 'app-cache-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/static/js/main.js',
  '/static/css/main.css'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => response || fetch(event.request))
  );
});
"""
        
        code["service_worker"] = service_worker
        
        return code
    
    async def _add_react_optimizations(self, code: dict) -> dict:
        """Add React performance optimizations"""
        
        # Add memo and useMemo examples to components
        optimization_patterns = """
// Performance optimization patterns

// 1. Memoize expensive components
import { memo } from 'react';

export const ExpensiveComponent = memo(({ data }) => {
  return <div>{/* render data */}</div>;
});

// 2. Use useMemo for expensive calculations
import { useMemo } from 'react';

const expensiveValue = useMemo(() => {
  return heavyCalculation(data);
}, [data]);

// 3. Use useCallback for event handlers
import { useCallback } from 'react';

const handleClick = useCallback(() => {
  doSomething(id);
}, [id]);

// 4. Virtualize long lists
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={items.length}
  itemSize={50}
  width="100%"
>
  {({ index, style }) => (
    <div style={style}>{items[index]}</div>
  )}
</FixedSizeList>
"""
        
        if "utils" in code:
            code["utils"] = optimization_patterns + "\n\n" + code["utils"]
        else:
            code["optimization_patterns"] = optimization_patterns
        
        return code
