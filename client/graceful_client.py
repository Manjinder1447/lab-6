"""
Test client for Graceful Degradation
Tests tiered functionality and load shedding
"""

import requests
import time
import threading
import logging
import random
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GracefulDegradationTest:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.results = {
            'tier1_success': [],
            'tier2_success': [],
            'tier3_success': [],
            'response_times': [],
            'shed_events': []
        }
    
    def test_tier1_product(self, product_id="123"):
        """Test critical tier - should always work"""
        url = f"{self.base_url}/product/{product_id}"
        try:
            start = time.time()
            response = requests.get(url, timeout=5)
            elapsed = time.time() - start
            
            result = {
                'success': response.status_code == 200,
                'status': response.status_code,
                'time': elapsed,
                'cached': response.headers.get('X-Cache', 'MISS')
            }
            self.results['tier1_success'].append(result['success'])
            self.results['response_times'].append(elapsed)
            return result
        except Exception as e:
            result = {'success': False, 'error': str(e)}
            self.results['tier1_success'].append(False)
            return result
    
    def test_tier2_reviews(self, product_id="123"):
        """Test important tier - may fall back to cache"""
        url = f"{self.base_url}/reviews/{product_id}"
        try:
            start = time.time()
            response = requests.get(url, timeout=5)
            elapsed = time.time() - start
            
            is_fallback = response.headers.get('X-Fallback', 'false') == 'true'
            is_cached = response.headers.get('X-Cache', 'MISS') == 'HIT'
            
            result = {
                'success': response.status_code == 200,
                'status': response.status_code,
                'time': elapsed,
                'fallback': is_fallback,
                'cached': is_cached
            }
            self.results['tier2_success'].append(result['success'])
            self.results['response_times'].append(elapsed)
            return result
        except Exception as e:
            result = {'success': False, 'error': str(e)}
            self.results['tier2_success'].append(False)
            return result
    
    def test_tier3_recommendations(self):
        """Test nice-to-have tier - may be disabled under load"""
        url = f"{self.base_url}/recommendations"
        try:
            start = time.time()
            response = requests.get(url, timeout=5)
            elapsed = time.time() - start
            
            # Check if request was shed
            is_shed = response.status_code == 503 or response.headers.get('X-Shedded') == 'true'
            if is_shed:
                self.results['shed_events'].append(True)
            
            result = {
                'success': response.status_code == 200,
                'status': response.status_code,
                'time': elapsed,
                'shed': is_shed
            }
            self.results['tier3_success'].append(result['success'] if not is_shed else False)
            self.results['response_times'].append(elapsed)
            return result
        except Exception as e:
            result = {'success': False, 'error': str(e)}
            self.results['tier3_success'].append(False)
            return result
    
    def check_metrics(self):
        """Check current system metrics"""
        url = f"{self.base_url}/metrics"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    def simulate_load(self, concurrency=5, duration=10):
        """Simulate load to trigger load shedding"""
        print(f"\n🚀 Simulating load with {concurrency} concurrent users for {duration} seconds...")
        
        def worker():
            end_time = time.time() + duration
            while time.time() < end_time:
                # Randomly choose which tier to test
                choice = random.random()
                if choice < 0.5:  # 50% product views (critical)
                    self.test_tier1_product(str(random.randint(1, 100)))
                elif choice < 0.8:  # 30% reviews (important)
                    self.test_tier2_reviews(str(random.randint(1, 100)))
                else:  # 20% recommendations (nice-to-have)
                    self.test_tier3_recommendations()
                time.sleep(random.uniform(0.1, 0.5))
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(worker) for _ in range(concurrency)]
            for f in futures:
                f.result()
    
    def run_test_scenarios(self):
        """Run various test scenarios"""
        print("\n" + "="*60)
        print("GRACEFUL DEGRADATION TEST")
        print("="*60)
        print(f"API URL: {self.base_url}")
        
        # Scenario 1: Normal load
        print("\n📊 Scenario 1: Normal Load (Baseline)")
        print("-" * 40)
        for i in range(5):
            self.test_tier1_product("123")
            self.test_tier2_reviews("123")
            self.test_tier3_recommendations()
            time.sleep(0.5)
        
        metrics = self.check_metrics()
        if metrics:
            print(f"   Shedding Level: {metrics.get('shedding_level', 0)}")
        
        # Scenario 2: High load - should trigger shedding
        print("\n📊 Scenario 2: High Load (Should trigger shedding)")
        print("-" * 40)
        self.simulate_load(concurrency=10, duration=15)
        
        metrics = self.check_metrics()
        if metrics:
            print(f"   Shedding Level: {metrics.get('shedding_level', 0)}")
            print(f"   Requests Shed: {metrics.get('shed_requests', 0)}")
        
        # Scenario 3: Recovery period
        print("\n📊 Scenario 3: Recovery Period")
        print("-" * 40)
        print("   Waiting for system to recover...")
        time.sleep(10)
        
        # Test after recovery
        for i in range(3):
            self.test_tier1_product("123")
            self.test_tier2_reviews("123")
            self.test_tier3_recommendations()
            time.sleep(1)
        
        metrics = self.check_metrics()
        if metrics:
            print(f"   Shedding Level: {metrics.get('shedding_level', 0)}")
    
    def print_results(self):
        """Print test results"""
        print("\n" + "="*60)
        print("TEST RESULTS SUMMARY")
        print("="*60)
        
        # Calculate success rates
        tier1_success = sum(self.results['tier1_success']) / len(self.results['tier1_success']) * 100 if self.results['tier1_success'] else 0
        tier2_success = sum(self.results['tier2_success']) / len(self.results['tier2_success']) * 100 if self.results['tier2_success'] else 0
        tier3_success = sum(self.results['tier3_success']) / len(self.results['tier3_success']) * 100 if self.results['tier3_success'] else 0
        
        print(f"\n📈 Success Rates:")
        print(f"   Tier 1 (Critical): {tier1_success:.1f}%")
        print(f"   Tier 2 (Important): {tier2_success:.1f}%")
        print(f"   Tier 3 (Nice-to-have): {tier3_success:.1f}%")
        
        if self.results['response_times']:
            avg_time = sum(self.results['response_times']) / len(self.results['response_times'])
            print(f"\n⏱️  Average Response Time: {avg_time:.2f}s")
        
        if self.results['shed_events']:
            print(f"\n🛡️  Load Shedding Events: {len(self.results['shed_events'])}")
        
        print("\n" + "="*60)

def main():
    # Use your API URL
    api_url = "https://jqmtiyoarc.execute-api.us-east-1.amazonaws.com/dev"
    
    test = GracefulDegradationTest(api_url)
    test.run_test_scenarios()
    test.print_results()

if __name__ == "__main__":
    main()