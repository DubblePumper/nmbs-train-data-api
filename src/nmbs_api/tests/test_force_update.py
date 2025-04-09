"""
Tests for API force update endpoint
"""
from .test_utils import make_api_request, log_test, TestStatus, timed_test

@timed_test
def test_force_update():
    """Test if the API force update endpoint is working correctly"""
    test_name = "Force Update Test"
    log_test(test_name, TestStatus.RUNNING, "Testing force update functionality")
    
    # Make request to update endpoint
    status_code, response_data = make_api_request("api/update", method="POST")
    
    # Check if request was successful
    if status_code == 200:
        if isinstance(response_data, dict) and response_data.get("status") == "success":
            log_test(test_name, TestStatus.SUCCESS, "Force update completed successfully")
            return True
        else:
            log_test(test_name, TestStatus.FAILED, f"Force update response does not indicate success: {response_data}")
            raise ValueError(f"Force update failed: {response_data}")
    else:
        log_test(test_name, TestStatus.FAILED, f"Force update endpoint returned status {status_code}")
        raise ConnectionError(f"Force update endpoint returned status {status_code}")