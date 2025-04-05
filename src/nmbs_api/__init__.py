"""
NMBS Train Data API

A standalone API for accessing Belgian railways (NMBS/SNCB) real-time train data.
"""

from .api import get_realtime_data, start_data_service, force_update

__all__ = ['get_realtime_data', 'start_data_service', 'force_update']