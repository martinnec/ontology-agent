"""
Index module for building and searching legal act indexes.

This module provides a unified interface for index management through IndexService.
All index operations should go through this service to ensure consistency.
"""

# Main public interface
from .service import IndexService

# Export only the public interface
__all__ = ['IndexService']
