"""
Search module providing unified search functionality.

This module provides a unified interface for search operations through SearchService.
All search operations should go through this service to ensure consistency.
"""

# Main public interface
from .service import SearchService

# Export only the public interface
__all__ = ['SearchService']
