"""
Enhanced API with Graceful Degradation
Implements tiered functionality and load shedding
"""

import json
import time
import random
import threading
from datetime import datetime, timedelta
from collections import deque

class EcommerceAPI:
    def __init__(self):
        # Tiers of functionality
        self.tiers = {
            'tier1': {  # Critical - Product viewing
                'enabled': True,
                'priority': 1,
                'fallback_enabled': False,
                'cache': {},
                'cache_ttl': 300  # 5 minutes
            },
            'tier2': {  # Important - Reviews
                'enabled': True,
                'priority': 2,
                'fallback_enabled': True,
                'cache': {},
                'cache_ttl': 3600  # 1 hour
            },
            'tier3': {  # Nice-to-have - Recommendations
                'enabled': True,
                'priority': 3,
                'fallback_enabled': True,
                'feature_flag': True,
                'maintenance_mode': False
            }
        }
        
        # Load metrics
        self.load_metrics = {
            'current_cpu': 0.0,
            'request_queue': deque(maxlen=100),
            'active_requests': 0,
            'shedding_level': 0,  # 0 = full service, 3 = critical only
            'total_requests': 0,
            'shed_requests': 0
        }
        
        # Start load monitor
        self.monitoring_thread = threading.Thread(target=self._monitor_load, daemon=True)
        self.monitoring_thread.start()
        
        print("EcommerceAPI initialized with graceful degradation")
    
    def lambda_handler(self, event, context):
        """Main handler for API Gateway requests"""
        path = event.get('path', '')
        
        # Track metrics
        self.load_metrics['active_requests'] += 1
        self.load_metrics['total_requests'] += 1
        start_time = time.time()
        
        try:
            # Check if we should shed this request
            if self._should_shed_request(path):
                self.load_metrics['shed_requests'] += 1
                return self._shed_response(path)
            
            # Route to appropriate handler
            if path == '/product' or path.startswith('/product/'):
                return self._handle_product_request(event)
            elif path == '/reviews' or path.startswith('/reviews/'):
                return self._handle_reviews_request(event)
            elif path == '/recommendations':
                return self._handle_recommendations_request(event)
            elif path == '/metrics':
                return self._handle_metrics_request()
            else:
                return self._not_found()
                
        finally:
            self.load_metrics['active_requests'] -= 1
            request_time = time.time() - start_time
            self.load_metrics['request_queue'].append(request_time)
    
    def _should_shed_request(self, path):
        """Determine if request should be shed based on load"""
        load_level = self.load_metrics['shedding_level']
        
        # Map paths to tiers
        if '/product' in path:
            request_tier = 1  # Critical - never shed
            return False
        elif '/reviews' in path:
            request_tier = 2  # Important - shed at level 2+
            return load_level >= 2
        elif '/recommendations' in path:
            request_tier = 3  # Nice-to-have - shed at level 1+
            return load_level >= 1
        else:
            return False
    
    def _shed_response(self, path):
        """Return appropriate shed response"""
        return {
            'statusCode': 503,
            'headers': {
                'Content-Type': 'application/json',
                'X-Shedded': 'true'
            },
            'body': json.dumps({
                'status': 'unavailable',
                'message': 'Service temporarily unavailable due to high load',
                'retry_after': 30,
                'shedding_level': self.load_metrics['shedding_level']
            })
        }
    
    def _monitor_load(self):
        """Monitor system metrics and adjust shedding level"""
        while True:
            # Simulate monitoring
            active = self.load_metrics['active_requests']
            
            # Calculate average response time
            if len(self.load_metrics['request_queue']) > 0:
                avg_response = sum(self.load_metrics['request_queue']) / len(self.load_metrics['request_queue'])
            else:
                avg_response = 0
            
            # Simulate CPU based on active requests and queue
            simulated_cpu = min(100, (active * 15) + (len(self.load_metrics['request_queue']) * 5))
            
            # Determine shedding level
            old_level = self.load_metrics['shedding_level']
            
            if simulated_cpu > 80 or avg_response > 3.0:
                # High load - shed tier 3 only
                new_level = 1
                self.tiers['tier3']['enabled'] = False
            elif simulated_cpu > 60 or avg_response > 2.0:
                # Medium load - prepare to shed
                new_level = 1
                self.tiers['tier3']['enabled'] = False
            else:
                # Normal load - full service
                new_level = 0
                self.tiers['tier3']['enabled'] = True
            
            # Update shedding level
            self.load_metrics['shedding_level'] = new_level
            
            if new_level != old_level:
                print(f"Load shedding changed: Level {old_level} -> {new_level} (CPU: {simulated_cpu:.1f}%, Response: {avg_response:.2f}s)")
            
            time.sleep(5)
    
    def _handle_product_request(self, event):
        """Tier 1: Critical - Product viewing with cache"""
        # Extract product ID from path
        path = event.get('path', '')
        if path == '/product':
            product_id = event.get('queryStringParameters', {}).get('id', 'default')
        else:
            product_id = path.replace('/product/', '')
        
        # Simulate database load (critical function has high success rate)
        if random.random() < 0.02:  # 2% failure rate
            print(f"Product service failed for {product_id}")
            
            # Check cache
            if product_id in self.tiers['tier1']['cache']:
                cached = self.tiers['tier1']['cache'][product_id]
                age = (datetime.now() - cached['timestamp']).seconds
                
                if age < self.tiers['tier1']['cache_ttl']:
                    return {
                        'statusCode': 200,
                        'headers': {
                            'Content-Type': 'application/json',
                            'X-Cache': 'HIT',
                            'X-Cache-Age': str(age)
                        },
                        'body': json.dumps(cached['data'])
                    }
            
            return {
                'statusCode': 503,
                'body': json.dumps({'error': 'Product service unavailable'})
            }
        
        # Success - create product data
        product = {
            'id': product_id,
            'name': f'Product {product_id}',
            'price': round(random.uniform(10, 100), 2),
            'description': f'This is a detailed description for product {product_id}',
            'in_stock': random.choice([True, True, True, False]),  # 75% in stock
            'category': random.choice(['Electronics', 'Clothing', 'Books', 'Home'])
        }
        
        # Update cache
        self.tiers['tier1']['cache'][product_id] = {
            'data': product,
            'timestamp': datetime.now()
        }
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(product)
        }
    
    def _handle_reviews_request(self, event):
        """Tier 2: Important - Reviews with fallback to cache"""
        # Check if tier is disabled due to load
        if not self.tiers['tier2']['enabled']:
            return self._reviews_fallback()
        
        # Extract product ID
        path = event.get('path', '')
        if path == '/reviews':
            product_id = event.get('queryStringParameters', {}).get('product_id', 'default')
        else:
            product_id = path.replace('/reviews/', '')
        
        # Simulate review service (higher failure rate)
        if random.random() < 0.3:  # 30% failure rate
            print(f"Review service failed for {product_id}")
            return self._reviews_fallback(product_id)
        
        # Generate random reviews
        num_reviews = random.randint(1, 5)
        reviews = []
        for i in range(num_reviews):
            reviews.append({
                'id': i+1,
                'user': f'user{random.randint(100, 999)}',
                'rating': random.randint(3, 5),
                'comment': random.choice([
                    'Great product!', 'Good value', 'Works as expected',
                    'Satisfied with purchase', 'Would buy again'
                ]),
                'date': (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat()
            })
        
        # Update cache
        self.tiers['tier2']['cache'][product_id] = {
            'data': reviews,
            'timestamp': datetime.now()
        }
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'product_id': product_id,
                'reviews': reviews,
                'average_rating': round(sum(r['rating'] for r in reviews) / len(reviews), 1)
            })
        }
    
    def _reviews_fallback(self, product_id=None):
        """Fallback for reviews - return cached or placeholder"""
        self.tiers['tier2']['fallback_enabled'] = True
        
        # Check cache
        if product_id and product_id in self.tiers['tier2']['cache']:
            cached = self.tiers['tier2']['cache'][product_id]
            age = (datetime.now() - cached['timestamp']).seconds
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'X-Cache': 'HIT',
                    'X-Fallback': 'true',
                    'X-Cache-Age': str(age)
                },
                'body': json.dumps({
                    'product_id': product_id,
                    'reviews': cached['data'],
                    'notice': 'Showing cached reviews',
                    'average_rating': round(sum(r['rating'] for r in cached['data']) / len(cached['data']), 1)
                })
            }
        
        # Return placeholder
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'X-Fallback': 'true'
            },
            'body': json.dumps({
                'product_id': product_id or 'unknown',
                'reviews': [
                    {'user': 'placeholder', 'rating': 4, 'comment': 'Reviews temporarily unavailable'}
                ],
                'average_rating': 4.0,
                'notice': 'Live reviews unavailable - showing placeholder'
            })
        }
    
    def _handle_recommendations_request(self, event):
        """Tier 3: Nice-to-have - Recommendations with graceful disable"""
        # Check maintenance mode
        if self.tiers['tier3']['maintenance_mode']:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'recommendations': [],
                    'notice': 'Recommendations in maintenance mode'
                })
            }
        
        # Check feature flag
        if not self.tiers['tier3']['feature_flag']:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'recommendations': [],
                    'notice': 'Recommendations feature disabled'
                })
            }
        
        # Check if tier is enabled due to load
        if not self.tiers['tier3']['enabled']:
            return {
                'statusCode': 503,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Recommendations temporarily unavailable due to high load',
                    'notice': 'Disabled during peak traffic'
                })
            }
        
        # Simulate expensive recommendation algorithm
        time.sleep(0.3)  # Simulate processing time
        
        if random.random() < 0.2:  # 20% failure rate
            return {
                'statusCode': 503,
                'body': json.dumps({'error': 'Recommendation engine error'})
            }
        
        # Generate recommendations
        recommendations = []
        for i in range(3):
            recommendations.append({
                'product_id': random.randint(1000, 9999),
                'name': f'Recommended Product {i+1}',
                'price': round(random.uniform(20, 150), 2),
                'reason': random.choice(['Based on your browsing', 'Popular in your area', 'Similar to your purchases'])
            })
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'recommendations': recommendations,
                'personalized': True
            })
        }
    
    def _handle_metrics_request(self):
        """Return current system metrics"""
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'shedding_level': self.load_metrics['shedding_level'],
                'active_requests': self.load_metrics['active_requests'],
                'queue_size': len(self.load_metrics['request_queue']),
                'total_requests': self.load_metrics['total_requests'],
                'shed_requests': self.load_metrics['shed_requests'],
                'tiers': {
                    'tier1': {'enabled': self.tiers['tier1']['enabled']},
                    'tier2': {'enabled': self.tiers['tier2']['enabled']},
                    'tier3': {'enabled': self.tiers['tier3']['enabled']}
                }
            })
        }
    
    def _not_found(self):
        """404 handler"""
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Endpoint not found'})
        }

# Lambda handler function
ecommerce_api = EcommerceAPI()

def lambda_handler(event, context):
    """AWS Lambda entry point"""
    return ecommerce_api.lambda_handler(event, context)