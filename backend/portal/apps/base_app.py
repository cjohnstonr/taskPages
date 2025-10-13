"""
Base App Class for Portal Applications
All portal apps must inherit from this base class
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseApp(ABC):
    """
    Base class for all portal applications

    Provides common interface for:
    - App registration
    - Route management
    - Sidebar configuration
    - Permission checking
    """

    def __init__(self):
        self.app_id: Optional[str] = None
        self.app_name: Optional[str] = None
        self.icon: Optional[str] = None  # Font Awesome icon class
        self.route_prefix: Optional[str] = None
        self.permissions: List[str] = ['user']  # Default: all users
        self.blueprint = None
        self.description: str = ""
        self.sort_order: int = 100  # For sidebar ordering

    @abstractmethod
    def register_routes(self, blueprint):
        """
        Override this method to register app-specific routes

        Args:
            blueprint: Flask Blueprint instance
        """
        raise NotImplementedError("Apps must implement register_routes()")

    def get_sidebar_config(self) -> Dict:
        """
        Return sidebar item configuration

        Returns:
            Dict with app metadata for sidebar rendering
        """
        return {
            'id': self.app_id,
            'name': self.app_name,
            'icon': self.icon,
            'route': self.route_prefix,
            'description': self.description,
            'sort_order': self.sort_order
        }

    def has_permission(self, user_role: str) -> bool:
        """
        Check if user role has permission to access this app

        Args:
            user_role: User's role string

        Returns:
            True if user has permission, False otherwise
        """
        if not self.permissions:
            return True  # No restrictions

        return user_role in self.permissions

    def get_blueprint(self):
        """Get the Flask blueprint for this app"""
        return self.blueprint
