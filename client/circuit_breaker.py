"""
Circuit Breaker Pattern Implementation
Tracks failures and opens the circuit after threshold is reached
"""

import time
import logging
from enum import Enum
from datetime import datetime, timedelta
from threading import Lock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Possible states of the circuit breaker"""
    CLOSED = "CLOSED"      # Normal operation - requests allowed
    OPEN = "OPEN"          # Failing fast - requests blocked
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered

class CircuitBreaker:
    """
    Circuit breaker implementation with configurable thresholds
    """
    
    def __init__(self, failure_threshold=3, timeout=30, name="default"):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting to close circuit
            name: Name of this circuit breaker (for logging)
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.name = name
        
        # Circuit state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        
        # Metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.rejected_requests = 0
        
        # Thread safety
        self.lock = Lock()
        
        logger.info(f"Circuit Breaker '{name}' initialized with threshold={failure_threshold}, timeout={timeout}")
    
    def call(self, func, *args, **kwargs):
        """
        Execute a function through the circuit breaker
        
        Args:
            func: The function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            The result of the function call
            
        Raises:
            Exception: If circuit is open or function fails
        """
        with self.lock:
            self.total_requests += 1
            
            # Check if circuit is open
            if self.state == CircuitState.OPEN:
                if self._timeout_expired():
                    logger.info(f"Circuit '{self.name}' timeout expired, transitioning to HALF-OPEN")
                    self.state = CircuitState.HALF_OPEN
                else:
                    self.rejected_requests += 1
                    logger.warning(f"Circuit '{self.name}' is OPEN, failing fast")
                    raise Exception(f"Circuit breaker '{self.name}' is OPEN - failing fast")
            
        try:
            # Execute the function
            result = func(*args, **kwargs)
            
            # Handle success
            with self.lock:
                self._handle_success()
            
            return result
            
        except Exception as e:
            # Handle failure
            with self.lock:
                self._handle_failure(e)
            
            # Re-raise the exception
            raise
    
    def _handle_success(self):
        """Handle successful execution"""
        self.successful_requests += 1
        
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit '{self.name}' test request succeeded, closing circuit")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.rejected_requests = 0
            
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = max(0, self.failure_count - 1)
    
    def _handle_failure(self, exception):
        """Handle failed execution"""
        self.failed_requests += 1
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        logger.warning(f"Circuit '{self.name}' failure #{self.failure_count}: {str(exception)}")
        
        if self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            logger.error(f"Circuit '{self.name}' failure threshold reached, OPENING circuit")
            self.state = CircuitState.OPEN
            
        elif self.state == CircuitState.HALF_OPEN:
            logger.error(f"Circuit '{self.name}' test request failed, re-opening circuit")
            self.state = CircuitState.OPEN
    
    def _timeout_expired(self):
        """Check if timeout period has expired"""
        if not self.last_failure_time:
            return True
        
        elapsed = (datetime.now() - self.last_failure_time).seconds
        return elapsed >= self.timeout
    
    def get_state(self):
        """Get current circuit state"""
        return self.state.value
    
    def get_metrics(self):
        """Get circuit breaker metrics"""
        with self.lock:
            success_rate = (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0
            
            return {
                'name': self.name,
                'state': self.state.value,
                'failure_count': self.failure_count,
                'failure_threshold': self.failure_threshold,
                'total_requests': self.total_requests,
                'successful_requests': self.successful_requests,
                'failed_requests': self.failed_requests,
                'rejected_requests': self.rejected_requests,
                'success_rate': round(success_rate, 2),
                'last_failure': self.last_failure_time.isoformat() if self.last_failure_time else None
            }
    
    def reset(self):
        """Manually reset the circuit breaker"""
        with self.lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
            logger.info(f"Circuit '{self.name}' manually reset")