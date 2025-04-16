"""
API Configuration Package

Import configuration settings from this package.
"""

from .pagination import (
    PAGINATION_SETTINGS,
    get_pagination_settings,
    API_NAME,
    API_VERSION
)

__all__ = [
    'PAGINATION_SETTINGS',
    'get_pagination_settings',
    'API_NAME',
    'API_VERSION'
]