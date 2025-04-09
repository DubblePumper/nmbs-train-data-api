"""
Test Runner for NMBS Train Data API

This module discovers and runs all tests for the NMBS Train Data API.
"""
import os
import sys
import time
import logging
import importlib
import inspect
import traceback
from typing import Dict, List, Callable, Any, Tuple
from datetime import datetime
from colorama import Fore, Back, Style, init

from .test_utils import TestStatus, log_test, timed_test, format_status_message
from .test_utils import HEADER_SEPARATOR, SECTION_SEPARATOR, TEST_SEPARATOR, log_section

# Initialize colorama
init(autoreset=True)

class TestRunner:
    """Discovers and runs all tests for the NMBS Train Data API"""
    
    def __init__(self, logger):
        """Initialize the test runner"""
        self.logger = logger
        self.test_modules = []
        self.test_results = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'details': {}
        }
    
    def discover_tests(self) -> List[Tuple[str, Callable]]:
        """
        Discover all test functions in the tests directory
        
        Returns:
            List of (test_name, test_function) tuples
        """
        tests_dir = os.path.dirname(__file__)
        module_files = [
            f[:-3] for f in os.listdir(tests_dir) 
            if f.startswith('test_') and f.endswith('.py') and f != 'test_utils.py' and f != 'test_runner.py'
        ]
        
        # Sort modules to get a consistent order
        module_files.sort()
        
        discovered_tests = []
        
        for module_name in module_files:
            try:
                # Import the module
                module_path = f"src.nmbs_api.tests.{module_name}"
                module = importlib.import_module(module_path)
                self.test_modules.append(module)
                
                # Find all test functions in the module and sort them
                test_functions = []
                for name, obj in inspect.getmembers(module):
                    if name.startswith('test_') and callable(obj):
                        test_functions.append((name, obj))
                
                # Sort test functions by name for consistent ordering
                test_functions.sort(key=lambda x: x[0])
                
                # Add sorted tests to discovered tests
                for name, obj in test_functions:
                    discovered_tests.append((f"{module_name}.{name}", obj))
            
            except ImportError as e:
                self.logger.error(format_status_message(
                    TestStatus.FAILED, 
                    f"Failed to import test module {module_name}: {e}"
                ))
        
        return discovered_tests
    
    def group_tests_by_category(self, tests: List[Tuple[str, Callable]]) -> Dict[str, List[Tuple[str, Callable]]]:
        """Group tests by their category (first part of the module name)"""
        grouped_tests = {}
        
        for test_name, test_func in tests:
            # Extract the module category (e.g., 'test_api_health' -> 'api_health')
            module_name = test_name.split('.')[0]
            category = module_name.replace('test_', '', 1)
            
            if category not in grouped_tests:
                grouped_tests[category] = []
                
            grouped_tests[category].append((test_name, test_func))
            
        return grouped_tests
    
    @timed_test
    def run_tests(self) -> Dict[str, Any]:
        """
        Run all discovered tests
        
        Returns:
            Dictionary with test results summary
        """
        self.logger.info(HEADER_SEPARATOR)
        self.logger.info(format_status_message(
            TestStatus.INFO,
            f"🚂 NMBS Train Data API Tests - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ))
        self.logger.info(HEADER_SEPARATOR)
        
        # Discover tests
        tests = self.discover_tests()
        self.test_results['total'] = len(tests)
        
        if not tests:
            self.logger.warning(format_status_message(
                TestStatus.SKIPPED,
                "⚠ No tests discovered!"
            ))
            return self.test_results
        
        self.logger.info(format_status_message(
            TestStatus.INFO,
            f"📋 Discovered {len(tests)} tests"
        ))
        
        # Group tests by category
        grouped_tests = self.group_tests_by_category(tests)
        
        # Run tests by category
        for category, category_tests in grouped_tests.items():
            category_display = category.replace('_', ' ').title()
            log_section(f"{category_display} Tests")
            
            for test_name, test_func in category_tests:
                # Extract just the function name for display
                func_name = test_name.split('.')[-1]
                display_name = func_name.replace('test_', '').replace('_', ' ').title()
                
                try:
                    log_test(display_name, TestStatus.RUNNING)
                    
                    # Run the test and capture start/end time
                    start_time = time.time()
                    test_func()
                    elapsed = time.time() - start_time
                    
                    # Record success
                    self.test_results['success'] += 1
                    self.test_results['details'][test_name] = {
                        'status': 'success',
                        'time': elapsed
                    }
                    
                    # Small separator between tests for better readability
                    self.logger.info(TEST_SEPARATOR)
                    
                except Exception as e:
                    self.test_results['failed'] += 1
                    self.test_results['details'][test_name] = {
                        'status': 'failed',
                        'error': str(e)
                    }
                    log_test(display_name, TestStatus.FAILED, exception=e)
                    
                    # Print traceback for debugging
                    formatted_traceback = ''.join(traceback.format_exception(
                        type(e), e, e.__traceback__
                    ))
                    self.logger.error(f"{Fore.RED}{formatted_traceback}{Style.RESET_ALL}")
                    
                    # Small separator between tests for better readability
                    self.logger.info(TEST_SEPARATOR)
        
        # Log summary with colorful formatting
        success_rate = 0
        if self.test_results['total'] > 0:
            success_rate = (self.test_results['success'] / self.test_results['total']) * 100
            
        self.logger.info(HEADER_SEPARATOR)
        
        summary = (f"Test Summary: "
                  f"{Fore.GREEN}{self.test_results['success']}{Style.RESET_ALL}/{self.test_results['total']} "
                  f"tests passed ({Fore.CYAN}{success_rate:.0f}%{Style.RESET_ALL})")
        
        self.logger.info(summary)
        
        if self.test_results['failed'] > 0:
            self.logger.error(format_status_message(
                TestStatus.FAILED,
                f"✗ {self.test_results['failed']} tests failed"
            ))
            
        if self.test_results['skipped'] > 0:
            self.logger.warning(format_status_message(
                TestStatus.SKIPPED,
                f"⚠ {self.test_results['skipped']} tests skipped"
            ))
            
        if self.test_results['failed'] == 0:
            self.logger.info(format_status_message(
                TestStatus.SUCCESS,
                "✓ All tests passed successfully! 🎉"
            ))
            
        self.logger.info(HEADER_SEPARATOR)
        
        return self.test_results

# Create a function to run tests that can be imported and called from other modules
def run_all_tests():
    """Run all tests and return the results"""
    logger = logging.getLogger("nmbs_api.tests")
    runner = TestRunner(logger)
    return runner.run_tests()

if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("nmbs_api.tests")
    
    # Run tests
    runner = TestRunner(logger)
    results = runner.run_tests()
    
    # Exit with appropriate status code
    sys.exit(1 if results['failed'] > 0 else 0)