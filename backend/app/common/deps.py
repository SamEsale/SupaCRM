"""
Shared FastAPI dependency exports.

This module provides a stable import location for common dependencies
used across routes and services.
"""

from app.db import get_db

__all__ = ["get_db"]