"""
FastAPI Analytics Service
=========================

Provides a REST API for accessing Langfuse analytics data.
Acts as a proxy between the frontend and Langfuse.
"""

from .app import create_app, app

__all__ = ["create_app", "app"]
