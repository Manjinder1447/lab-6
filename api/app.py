import json
import random
import time
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Main Lambda handler for the API
    """
    # Extract path from the event
    path = event.get('path', '')
    logger.info(f"Processing request for path: {path}")
    
    # Route to appropriate handler
    if path == '/healthy' or path == '/healthy/':
        return handle_healthy()
    elif path == '/unreliable' or path == '/unreliable/':
        return handle_unreliable()
    elif path == '/slow' or path == '/slow/':
        return handle_slow()
    else:
        return not_found()

def handle_healthy():
    """Always returns success"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'status': 'healthy',
            'message': 'Service is operating normally',
            'timestamp': time.time()
        })
    }

def handle_unreliable():
    """Fails 50% of the time"""
    # Generate random number between 0 and 1
    if random.random() < 0.5:
        logger.info("Unreliable endpoint - SUCCESS")
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'success',
                'message': 'Request succeeded',
                'timestamp': time.time()
            })
        }
    else:
        logger.warning("Unreliable endpoint - FAILURE")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'error',
                'message': 'Internal server error - simulated failure',
                'timestamp': time.time()
            })
        }

def handle_slow():
    """Responds with variable latency (1-10 seconds)"""
    # Random delay between 1 and 10 seconds
    delay = random.randint(1, 10)
    logger.info(f"Slow endpoint - delaying for {delay} seconds")
    
    # Simulate slow processing
    time.sleep(delay)
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'status': 'success',
            'message': f'Request completed after {delay} seconds',
            'delay': delay,
            'timestamp': time.time()
        })
    }

def not_found():
    """404 handler"""
    return {
        'statusCode': 404,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'error': 'Not found',
            'message': 'The requested endpoint does not exist'
        })
    }