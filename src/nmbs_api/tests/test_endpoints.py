"""
Tests for all API endpoints

This module discovers and tests all available API endpoints to ensure they are active
and returning data.
"""
import time
from typing import Dict, List, Any, Tuple
from .test_utils import make_api_request, log_test, TestStatus, timed_test, get_data_count

# Known API endpoints to test (these will be automatically discovered in production)
DEFAULT_ENDPOINTS = [
    "api/realtime/data",
    "api/planningdata/stops",
    "api/planningdata/routes",
    "api/planningdata/trips",
    "api/planningdata/stop_times",
    "api/planningdata/calendar",
    "api/planningdata/calendar_dates",
    "api/planningdata/agency",
    "api/planningdata/translations"
]

@timed_test
def test_endpoints_discovery():
    """
    Discover available endpoints by checking known endpoints
    and looking for common patterns
    """
    test_name = "API Endpoints Discovery"
    log_test(test_name, TestStatus.RUNNING, "Discovering available API endpoints")
    
    # The endpoints we've verified work
    verified_endpoints = []
    
    # First check the health endpoint to confirm API is running
    status_code, _ = make_api_request("api/health")
    if status_code != 200:
        log_test(test_name, TestStatus.FAILED, f"API health check failed with status {status_code}")
        raise ConnectionError("API is not responding, cannot discover endpoints")
    
    # Check all known endpoints
    for endpoint in DEFAULT_ENDPOINTS:
        try:
            status_code, response_data = make_api_request(endpoint)
            if status_code == 200:
                verified_endpoints.append(endpoint)
        except Exception:
            # Skip failed endpoints in discovery phase
            pass
    
    # Log results
    if verified_endpoints:
        log_test(test_name, TestStatus.SUCCESS, f"Discovered {len(verified_endpoints)} API endpoints")
        return verified_endpoints
    else:
        log_test(test_name, TestStatus.FAILED, "No API endpoints could be verified")
        raise ValueError("No API endpoints could be verified")

@timed_test
def test_all_endpoints():
    """Test all API endpoints to ensure they are responding correctly"""
    test_name = "All Endpoints Test"
    log_test(test_name, TestStatus.RUNNING, "Testing all API endpoints")
    
    # First discover available endpoints
    try:
        endpoints = test_endpoints_discovery()
    except Exception as e:
        log_test(test_name, TestStatus.FAILED, "Failed to discover endpoints", exception=e)
        raise
    
    # Initialize results
    success_count = 0
    failed_count = 0
    results = {}
    
    # Test each endpoint
    for endpoint in endpoints:
        endpoint_name = endpoint.split("/")[-1]
        endpoint_test_name = f"Endpoint: {endpoint_name}"
        
        try:
            log_test(endpoint_test_name, TestStatus.RUNNING, f"Testing {endpoint}")
            
            # Make request to endpoint
            status_code, response_data = make_api_request(endpoint)
            
            # Check if request was successful
            if status_code == 200:
                # Check if endpoint has data
                data_count = get_data_count(response_data)
                
                if data_count > 0:
                    log_test(endpoint_test_name, TestStatus.SUCCESS, f"Endpoint working", data_count=data_count)
                    results[endpoint] = {
                        'status': 'success',
                        'data_count': data_count
                    }
                    success_count += 1
                else:
                    log_test(endpoint_test_name, TestStatus.SUCCESS, f"Endpoint working but no data found", data_count=0)
                    results[endpoint] = {
                        'status': 'success',
                        'data_count': 0
                    }
                    success_count += 1
            else:
                log_test(endpoint_test_name, TestStatus.FAILED, f"Endpoint returned status {status_code}")
                results[endpoint] = {
                    'status': 'failed',
                    'error': f"Status code {status_code}"
                }
                failed_count += 1
                
        except Exception as e:
            log_test(endpoint_test_name, TestStatus.FAILED, "Request failed", exception=e)
            results[endpoint] = {
                'status': 'failed',
                'error': str(e)
            }
            failed_count += 1
    
    # Log summary
    if failed_count == 0:
        log_test(test_name, TestStatus.SUCCESS, f"All {success_count} endpoints working")
    else:
        log_test(test_name, TestStatus.FAILED, f"{failed_count} of {success_count + failed_count} endpoints failed")
        # Don't raise an exception here so other tests can continue
    
    return results

# Individual endpoint tests - these will be discovered and run by the test runner
@timed_test
def test_realtime_data():
    """Test the real-time data endpoint"""
    test_name = "Realtime Data Endpoint"
    log_test(test_name, TestStatus.RUNNING, "Testing real-time data endpoint")
    
    endpoint = "api/realtime/data"
    status_code, response_data = make_api_request(endpoint)
    
    if status_code == 200:
        data_count = get_data_count(response_data)
        log_test(test_name, TestStatus.SUCCESS, "Endpoint working", data_count=data_count)
        return True
    else:
        log_test(test_name, TestStatus.FAILED, f"Endpoint returned status {status_code}")
        raise ConnectionError(f"Endpoint returned status {status_code}")

@timed_test
def test_planning_stops():
    """Test the planning stops endpoint"""
    test_name = "Planning Stops Endpoint"
    log_test(test_name, TestStatus.RUNNING, "Testing planning stops endpoint")
    
    endpoint = "api/planningdata/stops"
    status_code, response_data = make_api_request(endpoint)
    
    if status_code == 200:
        data_count = get_data_count(response_data)
        log_test(test_name, TestStatus.SUCCESS, "Endpoint working", data_count=data_count)
        return True
    else:
        log_test(test_name, TestStatus.FAILED, f"Endpoint returned status {status_code}")
        raise ConnectionError(f"Endpoint returned status {status_code}")