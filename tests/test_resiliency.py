"""
Comprehensive test script for resiliency patterns
"""

import sys
import os
import time
import json
from datetime import datetime

# Add client to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'client'))

from client import ResilientClient

def run_circuit_breaker_test(client, num_calls=20):
    """Run comprehensive circuit breaker test"""
    print("\n" + "="*50)
    print("CIRCUIT BREAKER TEST")
    print("="*50)
    
    results = []
    
    for i in range(num_calls):
        result = client.call_unreliable()
        results.append({
            'attempt': i + 1,
            'success': result['success'],
            'time': result['elapsed'],
            'circuit_state': result['circuit_state']
        })
        
        status = "✓" if result['success'] else "✗"
        print(f"Attempt {i+1:2d}: {status} - {result['elapsed']:.2f}s - State: {result['circuit_state']}")
        time.sleep(0.5)
    
    return results

def run_retry_test(client, num_calls=5):
    """Run comprehensive retry test"""
    print("\n" + "="*50)
    print("RETRY PATTERN TEST")
    print("="*50)
    
    results = []
    
    for i in range(num_calls):
        result = client.call_slow()
        results.append({
            'attempt': i + 1,
            'success': result['success'],
            'total_time': result['elapsed'],
            'api_delay': result['data'].get('delay', 0) if result['success'] else None
        })
        
        status = "✓" if result['success'] else "✗"
        if result['success']:
            print(f"Request {i+1}: {status} - Total: {result['elapsed']:.2f}s (API delay: {result['data'].get('delay', 0)}s)")
        else:
            print(f"Request {i+1}: {status} - Failed after {result['elapsed']:.2f}s")
    
    return results

def analyze_results(circuit_results, retry_results):
    """Analyze and print test results"""
    print("\n" + "="*50)
    print("TEST RESULTS ANALYSIS")
    print("="*50)
    
    # Circuit Breaker Analysis
    print("\n1. CIRCUIT BREAKER ANALYSIS")
    print("-" * 30)
    
    total_calls = len(circuit_results)
    successful = sum(1 for r in circuit_results if r['success'])
    
    # Calculate when circuit was open
    open_states = [r for r in circuit_results if r['circuit_state'] == 'OPEN']
    
    print(f"Total calls: {total_calls}")
    print(f"Successful: {successful} ({successful/total_calls*100:.1f}%)")
    print(f"Times circuit was OPEN: {len(open_states)}")
    
    if open_states:
        avg_open_time = sum(r['time'] for r in open_states) / len(open_states)
        print(f"Average response time when OPEN: {avg_open_time:.3f}s (fast fail)")
    
    # Retry Analysis
    print("\n2. RETRY PATTERN ANALYSIS")
    print("-" * 30)
    
    total_retry_calls = len(retry_results)
    retry_successful = sum(1 for r in retry_results if r['success'])
    
    print(f"Total requests: {total_retry_calls}")
    print(f"Successful: {retry_successful}")
    
    if retry_successful > 0:
        avg_success_time = sum(r['total_time'] for r in retry_results if r['success']) / retry_successful
        print(f"Average successful request time: {avg_success_time:.2f}s")

def save_results(circuit_results, retry_results):
    """Save test results to JSON file"""
    filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'circuit_breaker_results': circuit_results,
        'retry_results': retry_results
    }
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {filename}")

def main():
    """Main test function"""
    api_url = "https://kisxnq5vw0.execute-api.us-east-1.amazonaws.com/dev"
    client = ResilientClient(api_url)
    
    print(f"\nStarting resiliency pattern tests...")
    print(f"API URL: {api_url}")
    
    try:
        circuit_results = run_circuit_breaker_test(client, num_calls=20)
        retry_results = run_retry_test(client, num_calls=5)
        analyze_results(circuit_results, retry_results)
        save_results(circuit_results, retry_results)
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nError during testing: {str(e)}")

if __name__ == "__main__":
    main()