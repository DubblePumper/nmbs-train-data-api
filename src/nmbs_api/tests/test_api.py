"""
API endpoint for running tests
"""
import threading
import time
import json
import logging
from datetime import datetime
from flask import Blueprint, jsonify, current_app
from ..utils.logging.logging_utils import get_logger
from .test_runner import run_all_tests

# Create a blueprint for the test API
test_api = Blueprint('test_api', __name__)
logger = get_logger('nmbs_api.tests.api')

# Global variable to store test results
_test_results = None
_test_status = "not_run"
_test_thread = None

def _run_tests_in_thread():
    """Run the tests in a background thread"""
    global _test_results, _test_status
    
    try:
        logger.info("Starting delayed test execution in background thread")
        _test_status = "running"
        
        # Give the server time to fully start up
        time.sleep(3)
        
        # Run the tests
        _test_results = run_all_tests()
        _test_status = "completed"
        
        logger.info(f"Background test execution completed: {_test_results['success']}/{_test_results['total']} tests passed")
    except Exception as e:
        logger.error(f"Error running tests in background thread: {str(e)}")
        _test_status = "error"
        _test_results = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'error': str(e)
        }

def start_delayed_tests(delay=5):
    """Start running tests in a background thread after a delay"""
    global _test_thread
    
    # Only start if no test is currently running
    if _test_thread is None or not _test_thread.is_alive():
        # Start with a longer delay to ensure API is ready
        def delayed_start():
            logger.info(f"Waiting {delay} seconds before starting tests...")
            time.sleep(delay)
            _run_tests_in_thread()
            
        _test_thread = threading.Thread(target=delayed_start, daemon=True)
        _test_thread.start()
        return True
    else:
        return False

@test_api.route('/run', methods=['POST'])
def run_tests():
    """API endpoint to trigger test runs"""
    global _test_status, _test_results
    
    if _test_status == "running":
        return jsonify({
            'status': 'running',
            'message': 'Tests are already running'
        }), 200
    
    # Start the tests in a background thread
    if start_delayed_tests():
        return jsonify({
            'status': 'started',
            'message': 'Tests started in background'
        }), 200
    else:
        return jsonify({
            'status': 'error',
            'message': 'Failed to start tests'
        }), 500

@test_api.route('/status', methods=['GET'])
def get_test_status():
    """API endpoint to check test status"""
    global _test_status, _test_results
    
    return jsonify({
        'status': _test_status,
        'results': _test_results
    }), 200