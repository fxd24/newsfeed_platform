"""
Scheduler module for managing background polling jobs.

This module integrates APScheduler to handle periodic polling of news sources.
"""

from .scheduler_manager import SchedulerManager

__all__ = ['SchedulerManager'] 