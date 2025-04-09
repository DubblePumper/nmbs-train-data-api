"""
Tests for API health endpoint
"""
from .test_utils import make_api_request, log_test, TestStatus, timed_test

@timed_test
def test_api_health():
    """Test if the API health endpoint is responding correctly"""
    test_name = "API Health Check"
    log_test(test_name, TestStatus.RUNNING, "Checking if API is healthy")
    
    # Make request to health endpoint
    status_code, response_data = make_api_request("api/health")
    
    # Check if request was successful
    if status_code == 200:
        if isinstance(response_data, dict) and response_data.get("status") == "healthy":
            log_test(test_name, TestStatus.SUCCESS, "API is healthy")
            return True
        else:
            log_test(test_name, TestStatus.FAILED, f"API response does not indicate health: {response_data}")
            raise ValueError(f"API health check failed: {response_data}")
    else:
        log_test(test_name, TestStatus.FAILED, f"API health endpoint returned status {status_code}")
        raise ConnectionError(f"API health endpoint returned status {status_code}")