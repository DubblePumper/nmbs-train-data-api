"""
Advanced Logging Utilities for NMBS Train Data API

This module provides enhanced logging functionality with:
1. Colored output (red for errors, yellow for warnings, white for info)
2. Grouping of related log messages
3. Log filtering to prevent spam
4. Context-aware formatting
5. Different logging levels for console and file
"""
import logging
import os
import sys
import time
from datetime import datetime
from functools import wraps
import threading
import colorama
from colorama import Fore, Back, Style

# Initialize colorama for cross-platform colored terminal output
colorama.init(autoreset=True)

# Store the last log message and its count to prevent spam
_last_log = {
    'message': '',
    'count': 0,
    'timestamp': 0,
    'level': None
}
_log_lock = threading.RLock()

# Log rate limiting settings
_RATE_LIMIT_SECONDS = 5  # Combine identical messages within this time window
_RATE_LIMIT_THRESHOLD = 3  # Show rate limiting message after this many duplicates

# Constants for log groups
_ACTIVE_GROUPS = {}  # Track active groups
_GROUP_INDENTATION = 0  # Track indentation level

class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors and improved formatting to log records"""
    
    # ANSI color codes for different log levels
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.WHITE,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT + Back.WHITE
    }
    
    # Format strings for different log levels
    FORMATS = {
        'DEBUG': '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        'INFO': '%(asctime)s | %(levelname)-8s | %(message)s',
        'WARNING': '%(asctime)s | %(levelname)-8s | %(message)s',
        'ERROR': '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        'CRITICAL': '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    }
    
    def __init__(self, use_colors=True):
        super().__init__(fmt="%(asctime)s | %(levelname)-8s | %(message)s", 
                         datefmt="%Y-%m-%d %H:%M:%S")
        self.use_colors = use_colors and sys.stdout.isatty()  # Only use colors in interactive terminal
    
    def format(self, record):
        # Save the original format
        orig_fmt = self._fmt
        
        # Apply indentation for groups
        indent = ' ' * (_GROUP_INDENTATION * 2)
        record.message = record.getMessage()
        record.message = f"{indent}{record.message}"
        record.msg = f"{indent}{record.msg}"
        
        # Apply custom format based on log level
        self._fmt = self.FORMATS.get(record.levelname, self.FORMATS['INFO'])
        
        # Format the record
        result = logging.Formatter.format(self, record)
        
        # Add color if enabled
        if self.use_colors:
            color = self.COLORS.get(record.levelname, Fore.WHITE)
            result = f"{color}{result}{Style.RESET_ALL}"
        
        # Restore the original format
        self._fmt = orig_fmt
        
        return result

class RateLimitingFilter(logging.Filter):
    """Filter to prevent log spam by combining repeated messages"""
    
    def __init__(self):
        super().__init__()
        self.pending_summaries = []  # Store pending summary messages

    def filter(self, record):
        global _last_log, _RATE_LIMIT_SECONDS, _RATE_LIMIT_THRESHOLD
        
        current_time = time.time()
        message = record.getMessage()
        
        with _log_lock:
            # Check if this is a repeated message within the time window
            if (_last_log['message'] == message and 
                _last_log['level'] == record.levelno and
                current_time - _last_log['timestamp'] < _RATE_LIMIT_SECONDS):
                
                _last_log['count'] += 1
                
                # Only show the first message and a summary after THRESHOLD repeats
                if _last_log['count'] == _RATE_LIMIT_THRESHOLD:
                    record.msg = f"{record.msg} (repeated multiple times, will be summarized...)"
                    return True
                elif _last_log['count'] > _RATE_LIMIT_THRESHOLD:
                    # Suppress intermediate repeated logs
                    return False
            else:
                # If we had previous repeated messages, store summary info for later emission
                if _last_log['count'] > _RATE_LIMIT_THRESHOLD:
                    # Create a new summary record instead of modifying the current one
                    self.pending_summaries.append({
                        'name': record.name,
                        'msg': f"Previous message repeated {_last_log['count']} times",
                        'level': _last_log['level'],
                        'levelname': logging.getLevelName(_last_log['level'])
                    })
                
                # Reset for the new message
                _last_log['message'] = message
                _last_log['count'] = 1
                _last_log['timestamp'] = current_time
                _last_log['level'] = record.levelno
            
            return True
            
    def emit_pending_summaries(self):
        """Emit any pending summary messages using a separate method"""
        summaries = self.pending_summaries.copy()
        self.pending_summaries = []
        
        for summary in summaries:
            logger = logging.getLogger(summary['name'])
            level = summary['level']
            msg = summary['msg']
            
            # Use log method directly instead of handle() to avoid recursion
            logger.log(level, msg)

class LogGroup:
    """Context manager for grouping related log messages visually"""
    
    def __init__(self, logger, title=None):
        self.logger = logger
        self.title = title
        self.group_id = id(self)
    
    def __enter__(self):
        global _GROUP_INDENTATION, _ACTIVE_GROUPS
        
        # Increment indentation level
        _GROUP_INDENTATION += 1
        _ACTIVE_GROUPS[self.group_id] = True
        
        # Log the group header if title is provided
        if self.title:
            # Log a separator line before the group
            self.logger.info("─" * 50)
            self.logger.info(f"▶ {self.title}")
            self.logger.info("─" * 50)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        global _GROUP_INDENTATION, _ACTIVE_GROUPS
        
        # Log the group footer if title is provided
        if self.title:
            self.logger.info("─" * 50)
            # Log a separator line after the group
            if exc_type is not None:
                # If there was an exception, log it in the footer
                self.logger.error(f"✘ {self.title} - Failed with: {exc_val}")
            else:
                self.logger.info(f"✓ {self.title} - Completed")
        
        # Decrement indentation level
        _GROUP_INDENTATION -= 1
        if _GROUP_INDENTATION < 0:
            _GROUP_INDENTATION = 0
        
        if self.group_id in _ACTIVE_GROUPS:
            del _ACTIVE_GROUPS[self.group_id]

def setup_logging(console_level=logging.INFO, log_file=None, log_file_level=logging.WARNING, use_colors=True):
    """
    Set up the enhanced logging system with separate levels for console and file output
    
    Args:
        console_level: The logging level for console output (default: INFO)
        log_file: Optional file path to save logs (default: None)
        log_file_level: The logging level for file output (default: WARNING)
        use_colors: Whether to use colors in console output (default: True)
    
    Returns:
        The configured root logger
    """
    # Reset logging config
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Create formatters
    colored_formatter = ColoredFormatter(use_colors=use_colors)
    file_formatter = ColoredFormatter(use_colors=False)
    
    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(colored_formatter)
    console_handler.setLevel(console_level)
    
    # Configure root logger with the lowest level of either console or file
    root_logger = logging.getLogger()
    min_level = min(console_level, log_file_level) if log_file else console_level
    root_logger.setLevel(min_level)
    root_logger.addHandler(console_handler)
    
    # Create and configure the rate limiting filter
    rate_limiting_filter = RateLimitingFilter()
    
    # Custom handler class that will emit pending summaries after handling each record
    class SummaryAwareHandler(logging.Handler):
        def __init__(self, base_handler, rate_filter):
            super().__init__()
            self.base_handler = base_handler
            self.rate_filter = rate_filter
            
        def emit(self, record):
            self.base_handler.emit(record)
            # After each emission, check if there are summaries to emit
            self.rate_filter.emit_pending_summaries()
            
    # Wrap the console handler
    summary_console_handler = SummaryAwareHandler(console_handler, rate_limiting_filter)
    summary_console_handler.addFilter(rate_limiting_filter)
    root_logger.addHandler(summary_console_handler)
    root_logger.removeHandler(console_handler)  # Remove the original handler
    
    # Add file handler if specified
    if log_file:
        # Create the directory for the log file if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        # Create a file handler with specified level (typically WARNING or higher)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(log_file_level)
        
        # Wrap the file handler
        summary_file_handler = SummaryAwareHandler(file_handler, rate_limiting_filter)
        summary_file_handler.addFilter(rate_limiting_filter)
        root_logger.addHandler(summary_file_handler)
    
    # Disable propagation for these common noisy modules
    for logger_name in ['urllib3', 'requests', 'chardet.charsetprober']:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    # Return the configured logger
    return root_logger

def get_logger(name=None):
    """
    Get a logger with the specified name 
    
    Args:
        name: The logger name (default: root logger)
        
    Returns:
        The configured logger
    """
    logger = logging.getLogger(name)
    
    # Add log_group method to the logger
    def log_group(title=None):
        return LogGroup(logger, title)
    
    # Attach the method to the logger
    logger.group = log_group
    
    return logger

def log_execution_time(logger=None, level=logging.INFO):
    """
    Decorator to log the execution time of a function
    
    Args:
        logger: The logger to use (default: root logger)
        level: The logging level (default: INFO)
    """
    if logger is None:
        logger = logging.getLogger()
        
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__
            
            logger.log(level, f"Starting {func_name}()")
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.log(level, f"Completed {func_name}() in {elapsed:.2f} seconds")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.exception(f"Failed {func_name}() after {elapsed:.2f} seconds: {str(e)}")
                raise
        
        return wrapper
    
    return decorator

# Utility function to format log messages with context
def format_with_context(message, context):
    """Format a message with context information"""
    context_str = ' | '.join(f"{k}={v}" for k, v in context.items())
    return f"{message} [{context_str}]"