"""
Retry with Exponential Backoff Pattern Implementation
Retries failed operations with increasing delays
"""

import time
import random
import logging

logger = logging.getLogger(__name__)

class RetryWithBackoff:
    """
    Retry with exponential backoff implementation
    """
    
    def __init__(self, max_retries=3, base_delay=0.1, max_delay=10.0, jitter=True):
        """
        Initialize retry handler
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            jitter: Whether to add random jitter to delays
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        
        # Metrics
        self.total_attempts = 0
        self.retry_count = 0
        self.successful_calls = 0
        self.failed_calls = 0
        
        logger.info(f"Retry handler initialized: max_retries={max_retries}, base_delay={base_delay}s")
    
    def execute(self, func, *args, **kwargs):
        """
        Execute a function with retry logic
        
        Args:
            func: The function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            The result of the function call
            
        Raises:
            Exception: The last exception from the function after max retries
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                self.total_attempts += 1
                
                if attempt > 0:
                    self.retry_count += 1
                    logger.info(f"Retry attempt {attempt}/{self.max_retries}")
                
                result = func(*args, **kwargs)
                self.successful_calls += 1
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    self.failed_calls += 1
                    logger.error(f"Max retries ({self.max_retries}) exceeded. Last error: {str(e)}")
                    raise
                
                delay = self._calculate_delay(attempt)
                logger.warning(f"Attempt {attempt + 1} failed. Retrying in {delay:.2f}s. Error: {str(e)}")
                time.sleep(delay)
    
    def _calculate_delay(self, attempt):
        """
        Calculate delay for exponential backoff
        
        Formula: base_delay * (2 ^ attempt)
        """
        delay = self.base_delay * (2 ** attempt)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            # Random between 50% and 150% of calculated delay
            jitter_factor = 0.5 + random.random()
            delay = delay * jitter_factor
        
        # Cap at max delay
        return min(delay, self.max_delay)
    
    def get_metrics(self):
        """Get retry handler metrics"""
        return {
            'max_retries': self.max_retries,
            'total_attempts': self.total_attempts,
            'retry_count': self.retry_count,
            'successful_calls': self.successful_calls,
            'failed_calls': self.failed_calls,
            'retry_rate': round((self.retry_count / self.total_attempts * 100) if self.total_attempts > 0 else 0, 2)
        }
    
    def reset_metrics(self):
        """Reset metrics counters"""
        self.total_attempts = 0
        self.retry_count = 0
        self.successful_calls = 0
        self.failed_calls = 0
        logger.info("Retry handler metrics reset")
