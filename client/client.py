"""
Resilient Client Application
Demonstrates Circuit Breaker and Retry patterns
"""

import requests
import time
import logging
from circuit_breaker import CircuitBreaker
from retry import RetryWithBackoff

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ResilientClient:
    """
    Client that demonstrates resiliency patterns
    """
    
    def __init__(self, base_url, timeout=10):
        """
        Initialize the resilient client
        
        Args:
            base_url: Base URL of the API (your API Gateway URL)
            timeout: Default timeout for requests
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
        # Initialize patterns
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            timeout=30,
            name="unreliable-endpoint"
        )
        
        self.retry_handler = RetryWithBackoff(
            max_retries=3,
            base_delay=0.1,
            max_delay=2.0,
            jitter=True
        )
        
        logger.info(f"ResilientClient initialized with base URL: {base_url}")
    
    def call_healthy(self):
        """
        Call the healthy endpoint (no resiliency patterns)
        """
        url = f"{self.base_url}/healthy"
        logger.info(f"Calling healthy endpoint: {url}")
        
        start_time = time.time()
        
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            elapsed = time.time() - start_time
            data = response.json()
            
            logger.info(f"Healthy endpoint success - Time: {elapsed:.2f}s")
            return {
                'success': True,
                'data': data,
                'elapsed': elapsed,
                'status_code': response.status_code
            }
            
        except requests.exceptions.RequestException as e:
            elapsed = time.time() - start_time
            logger.error(f"Healthy endpoint failed - Time: {elapsed:.2f}s - Error: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'elapsed': elapsed,
                'status_code': getattr(e.response, 'status_code', None)
            }
    
    def call_unreliable(self):
        """
        Call the unreliable endpoint with circuit breaker
        """
        url = f"{self.base_url}/unreliable"
        logger.info(f"Calling unreliable endpoint with circuit breaker")
        
        def _make_request():
            """Inner function that makes the actual request"""
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            return response.json()
        
        start_time = time.time()
        
        try:
            # Call through circuit breaker
            result = self.circuit_breaker.call(_make_request)
            elapsed = time.time() - start_time
            
            logger.info(f"Unreliable endpoint success via circuit breaker - Time: {elapsed:.2f}s")
            
            return {
                'success': True,
                'data': result,
                'elapsed': elapsed,
                'circuit_state': self.circuit_breaker.get_state()
            }
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Unreliable endpoint failed via circuit breaker - Time: {elapsed:.2f}s - Error: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'elapsed': elapsed,
                'circuit_state': self.circuit_breaker.get_state()
            }
    
    def call_slow(self):
        """
        Call the slow endpoint with retry pattern
        """
        url = f"{self.base_url}/slow"
        logger.info(f"Calling slow endpoint with retry pattern")
        
        def _make_request():
            """Inner function that makes the actual request"""
            response = requests.get(url, timeout=12)  # Longer timeout for slow endpoint
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            return response.json()
        
        start_time = time.time()
        
        try:
            # Call through retry handler
            result = self.retry_handler.execute(_make_request)
            elapsed = time.time() - start_time
            
            logger.info(f"Slow endpoint success via retry - Time: {elapsed:.2f}s")
            
            return {
                'success': True,
                'data': result,
                'elapsed': elapsed,
                'retry_metrics': self.retry_handler.get_metrics()
            }
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Slow endpoint failed via retry - Time: {elapsed:.2f}s - Error: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'elapsed': elapsed,
                'retry_metrics': self.retry_handler.get_metrics()
            }
    
    def get_stats(self):
        """Get client statistics"""
        return {
            'circuit_breaker': self.circuit_breaker.get_metrics(),
            'retry_handler': self.retry_handler.get_metrics()
        }

def main():
    """Main function to demonstrate the client"""
    # IMPORTANT: Replace with YOUR API URL from the deployment
    api_url = "https://kisxnq5vw0.execute-api.us-east-1.amazonaws.com/dev"
    
    # Create client
    client = ResilientClient(api_url)
    
    print("\n" + "="*60)
    print("RESILIENCY PATTERNS DEMONSTRATION")
    print("="*60)
    print(f"API URL: {api_url}")
    
    # Test 1: Healthy endpoint (baseline)
    print("\n1. Testing Healthy Endpoint (Baseline)")
    print("-" * 40)
    for i in range(3):
        result = client.call_healthy()
        status = "✓" if result['success'] else "✗"
        print(f"   Attempt {i+1}: {status} - {result['elapsed']:.2f}s")
    
    # Test 2: Circuit Breaker with Unreliable Endpoint
    print("\n2. Testing Circuit Breaker with Unreliable Endpoint")
    print("-" * 40)
    print("   (Making 15 calls - circuit should open after 3 failures)")
    
    for i in range(15):
        result = client.call_unreliable()
        status = "✓" if result['success'] else "✗"
        print(f"   Attempt {i+1:2d}: {status} - {result['elapsed']:.2f}s - Circuit: {result['circuit_state']}")
        time.sleep(1)  # Wait 1 second between calls
    
    # Test 3: Retry with Slow Endpoint
    print("\n3. Testing Retry Pattern with Slow Endpoint")
    print("-" * 40)
    print("   (Making 3 calls - each may trigger retries)")
    
    for i in range(3):
        result = client.call_slow()
        status = "✓" if result['success'] else "✗"
        print(f"   Request {i+1}: {status} - Total time: {result['elapsed']:.2f}s")
        if result['success']:
            print(f"      API delay: {result['data'].get('delay', 'unknown')}s")
    
    # Show final statistics
    print("\n4. Final Statistics")
    print("-" * 40)
    stats = client.get_stats()
    
    print("\n   Circuit Breaker:")
    print(f"      State: {stats['circuit_breaker']['state']}")
    print(f"      Success Rate: {stats['circuit_breaker']['success_rate']}%")
    print(f"      Requests: {stats['circuit_breaker']['total_requests']} total, "
          f"{stats['circuit_breaker']['rejected_requests']} rejected")
    
    print("\n   Retry Handler:")
    print(f"      Total Attempts: {stats['retry_handler']['total_attempts']}")
    print(f"      Retry Rate: {stats['retry_handler']['retry_rate']}%")

if __name__ == "__main__":
    main()