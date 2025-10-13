"""
Portal Core - Registry and Management
Central registry for managing all portal applications
"""

import logging
from typing import Dict, List, Optional
from .apps.base_app import BaseApp

logger = logging.getLogger(__name__)


class PortalRegistry:
    """
    Registry for managing portal apps

    Provides:
    - App registration
    - Sidebar generation
    - Permission-based filtering
    - App lookup
    """

    def __init__(self):
        self._apps: Dict[str, BaseApp] = {}
        logger.info("Portal registry initialized")

    def register(self, app_instance: BaseApp):
        """
        Register a portal app

        Args:
            app_instance: Instance of a BaseApp subclass

        Raises:
            ValueError: If app_id is already registered or invalid
        """
        if not isinstance(app_instance, BaseApp):
            raise ValueError("App must inherit from BaseApp")

        if not app_instance.app_id:
            raise ValueError("App must have an app_id")

        if app_instance.app_id in self._apps:
            raise ValueError(f"App '{app_instance.app_id}' already registered")

        self._apps[app_instance.app_id] = app_instance
        logger.info(f"Registered portal app: {app_instance.app_id} ({app_instance.app_name})")

    def unregister(self, app_id: str):
        """
        Unregister a portal app

        Args:
            app_id: ID of the app to unregister
        """
        if app_id in self._apps:
            del self._apps[app_id]
            logger.info(f"Unregistered portal app: {app_id}")

    def get_app(self, app_id: str) -> Optional[BaseApp]:
        """
        Get app instance by ID

        Args:
            app_id: App ID

        Returns:
            BaseApp instance or None
        """
        return self._apps.get(app_id)

    def get_all_apps(self) -> List[BaseApp]:
        """
        Get all registered apps

        Returns:
            List of all BaseApp instances
        """
        return list(self._apps.values())

    def get_sidebar_items(self, user_role: str = 'user') -> List[Dict]:
        """
        Get sidebar items based on user permissions

        Args:
            user_role: User's role (e.g., 'user', 'supervisor', 'admin')

        Returns:
            List of sidebar item configs, sorted by sort_order
        """
        items = []

        for app in self._apps.values():
            if app.has_permission(user_role):
                items.append(app.get_sidebar_config())

        # Sort by sort_order
        items.sort(key=lambda x: x.get('sort_order', 100))

        logger.debug(f"Generated {len(items)} sidebar items for role: {user_role}")
        return items

    def get_app_count(self) -> int:
        """Get total number of registered apps"""
        return len(self._apps)

    def list_app_ids(self) -> List[str]:
        """Get list of all registered app IDs"""
        return list(self._apps.keys())
