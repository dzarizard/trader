"""
Health monitoring and error handling for CFD Trader Assistant.
"""
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json
import requests
from functools import wraps

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"     # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class HealthCheck:
    """Individual health check definition."""
    
    def __init__(self, name: str, check_func: Callable, timeout: float = 5.0, critical: bool = True):
        self.name = name
        self.check_func = check_func
        self.timeout = timeout
        self.critical = critical
        self.last_check = None
        self.last_result = None
        self.last_error = None
        self.consecutive_failures = 0
        self.max_failures = 3
    
    def run_check(self) -> Dict[str, Any]:
        """Run the health check."""
        start_time = time.time()
        
        try:
            result = self.check_func()
            duration = time.time() - start_time
            
            self.last_check = datetime.now()
            self.last_result = result
            self.last_error = None
            self.consecutive_failures = 0
            
            return {
                'name': self.name,
                'status': HealthStatus.HEALTHY,
                'result': result,
                'duration_ms': duration * 1000,
                'critical': self.critical,
                'timestamp': self.last_check.isoformat()
            }
            
        except Exception as e:
            duration = time.time() - start_time
            self.consecutive_failures += 1
            
            self.last_check = datetime.now()
            self.last_result = None
            self.last_error = str(e)
            
            status = HealthStatus.UNHEALTHY if self.critical else HealthStatus.DEGRADED
            
            return {
                'name': self.name,
                'status': status,
                'error': str(e),
                'duration_ms': duration * 1000,
                'critical': self.critical,
                'consecutive_failures': self.consecutive_failures,
                'timestamp': self.last_check.isoformat()
            }


class CircuitBreaker:
    """Circuit breaker for external service calls."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker."""
        if self.last_failure_time is None:
            return True
        
        return (datetime.now() - self.last_failure_time).total_seconds() >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class RetryHandler:
    """Retry handler with exponential backoff."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def retry(self, func: Callable, *args, **kwargs):
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    break
                
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
        
        raise last_exception


class HealthMonitor:
    """Main health monitoring system."""
    
    def __init__(self):
        self.health_checks: Dict[str, HealthCheck] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_handlers: Dict[str, RetryHandler] = {}
        self.overall_status = HealthStatus.UNKNOWN
        self.last_check_time = None
    
    def add_health_check(self, name: str, check_func: Callable, timeout: float = 5.0, critical: bool = True):
        """Add a health check."""
        self.health_checks[name] = HealthCheck(name, check_func, timeout, critical)
    
    def add_circuit_breaker(self, name: str, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        """Add a circuit breaker."""
        self.circuit_breakers[name] = CircuitBreaker(failure_threshold, recovery_timeout)
    
    def add_retry_handler(self, name: str, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        """Add a retry handler."""
        self.retry_handlers[name] = RetryHandler(max_retries, base_delay, max_delay)
    
    def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = []
        critical_failures = 0
        
        for check in self.health_checks.values():
            result = check.run_check()
            results.append(result)
            
            if result['status'] == HealthStatus.UNHEALTHY and result['critical']:
                critical_failures += 1
        
        # Determine overall status
        if critical_failures > 0:
            self.overall_status = HealthStatus.UNHEALTHY
        elif any(r['status'] == HealthStatus.DEGRADED for r in results):
            self.overall_status = HealthStatus.DEGRADED
        else:
            self.overall_status = HealthStatus.HEALTHY
        
        self.last_check_time = datetime.now()
        
        return {
            'overall_status': self.overall_status.value,
            'timestamp': self.last_check_time.isoformat(),
            'checks': results
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        return {
            'overall_status': self.overall_status.value,
            'last_check': self.last_check_time.isoformat() if self.last_check_time else None,
            'checks_count': len(self.health_checks),
            'circuit_breakers_count': len(self.circuit_breakers)
        }
    
    def call_with_circuit_breaker(self, name: str, func: Callable, *args, **kwargs):
        """Call function with circuit breaker protection."""
        if name not in self.circuit_breakers:
            raise ValueError(f"Circuit breaker '{name}' not found")
        
        return self.circuit_breakers[name].call(func, *args, **kwargs)
    
    def call_with_retry(self, name: str, func: Callable, *args, **kwargs):
        """Call function with retry logic."""
        if name not in self.retry_handlers:
            raise ValueError(f"Retry handler '{name}' not found")
        
        return self.retry_handlers[name].retry(func, *args, **kwargs)


# Global health monitor instance
health_monitor = HealthMonitor()


def with_retry(name: str = 'default'):
    """Decorator for retry functionality."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return health_monitor.call_with_retry(name, func, *args, **kwargs)
        return wrapper
    return decorator


def with_circuit_breaker(name: str = 'default'):
    """Decorator for circuit breaker functionality."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return health_monitor.call_with_circuit_breaker(name, func, *args, **kwargs)
        return wrapper
    return decorator


# Predefined health checks
def check_database_connection():
    """Check database connection health."""
    # This would check actual database connection
    # For now, return a mock success
    return {'status': 'connected', 'response_time_ms': 10}


def check_data_provider(provider_name: str):
    """Check data provider health."""
    def check():
        # This would check actual data provider
        # For now, return a mock success
        return {'provider': provider_name, 'status': 'available', 'last_update': datetime.now().isoformat()}
    
    return check


def check_telegram_connection():
    """Check Telegram bot connection."""
    def check():
        # This would check actual Telegram API
        # For now, return a mock success
        return {'bot_status': 'active', 'api_available': True}
    
    return check


def check_disk_space():
    """Check available disk space."""
    import shutil
    
    def check():
        total, used, free = shutil.disk_usage('/')
        free_gb = free // (1024**3)
        
        if free_gb < 1:
            raise Exception(f"Low disk space: {free_gb}GB available")
        
        return {'free_space_gb': free_gb, 'total_space_gb': total // (1024**3)}
    
    return check


def check_memory_usage():
    """Check memory usage."""
    import psutil
    
    def check():
        memory = psutil.virtual_memory()
        usage_percent = memory.percent
        
        if usage_percent > 90:
            raise Exception(f"High memory usage: {usage_percent}%")
        
        return {
            'usage_percent': usage_percent,
            'available_gb': memory.available // (1024**3),
            'total_gb': memory.total // (1024**3)
        }
    
    return check


def setup_default_health_checks():
    """Set up default health checks."""
    # Add health checks
    health_monitor.add_health_check('database', check_database_connection, critical=True)
    health_monitor.add_health_check('telegram', check_telegram_connection, critical=False)
    health_monitor.add_health_check('disk_space', check_disk_space, critical=True)
    health_monitor.add_health_check('memory', check_memory_usage, critical=True)
    
    # Add circuit breakers
    health_monitor.add_circuit_breaker('yahoo_finance', failure_threshold=3, recovery_timeout=300)
    health_monitor.add_circuit_breaker('telegram_api', failure_threshold=5, recovery_timeout=60)
    
    # Add retry handlers
    health_monitor.add_retry_handler('data_fetch', max_retries=3, base_delay=1.0, max_delay=30.0)
    health_monitor.add_retry_handler('telegram_send', max_retries=2, base_delay=0.5, max_delay=10.0)


def get_health_endpoint():
    """Get health endpoint for web framework."""
    def health_endpoint():
        try:
            health_status = health_monitor.run_health_checks()
            status_code = 200 if health_status['overall_status'] == 'healthy' else 503
            return health_status, status_code
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {'error': str(e), 'overall_status': 'unhealthy'}, 503
    
    return health_endpoint


# Initialize default health checks
setup_default_health_checks()