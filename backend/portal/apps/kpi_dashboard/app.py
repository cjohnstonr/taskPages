"""
KPI Dashboard App
Main application module for the KPI Dashboard
"""

import logging
from flask import Blueprint, render_template, jsonify, request
from auth.oauth_handler import login_required
from ..base_app import BaseApp
from .queries import get_kpi_data

logger = logging.getLogger(__name__)


class KPIDashboardApp(BaseApp):
    """
    KPI Dashboard Application

    Displays key performance indicators including:
    - Task statistics
    - Escalation metrics
    - Team activity
    """

    def __init__(self):
        super().__init__()

        # App metadata
        self.app_id = 'kpi_dashboard'
        self.app_name = 'KPI Dashboard'
        self.icon = 'fas fa-chart-line'
        self.route_prefix = '/portal/apps/kpi'
        self.permissions = ['user', 'supervisor', 'admin']
        self.description = 'View key performance indicators and metrics'
        self.sort_order = 10  # First in sidebar

        # Create blueprint
        self.blueprint = Blueprint(
            'kpi_dashboard',
            __name__,
            url_prefix=self.route_prefix,
            template_folder='../../../templates/portal/apps/kpi_dashboard'
        )

        # Register routes
        self.register_routes(self.blueprint)

    def register_routes(self, bp):
        """Register KPI Dashboard routes"""

        @bp.route('/')
        @login_required
        def index():
            """Render KPI Dashboard page"""
            logger.info(f"KPI Dashboard accessed by {request.user.get('email')}")

            return render_template(
                'index.html',
                user_email=request.user.get('email'),
                user_role=request.user.get('role', 'user')
            )

        @bp.route('/api/data')
        @login_required
        def get_data():
            """Get KPI data via API"""
            try:
                logger.info(f"KPI data requested by {request.user.get('email')}")

                # Fetch KPI data
                kpi_data = get_kpi_data(request.user)

                return jsonify({
                    'success': True,
                    'data': kpi_data
                })

            except Exception as e:
                logger.error(f"Error fetching KPI data: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @bp.route('/api/refresh')
        @login_required
        def refresh_data():
            """Force refresh KPI data (bypass cache if implemented)"""
            try:
                logger.info(f"KPI refresh requested by {request.user.get('email')}")

                kpi_data = get_kpi_data(request.user)

                return jsonify({
                    'success': True,
                    'data': kpi_data,
                    'refreshed': True
                })

            except Exception as e:
                logger.error(f"Error refreshing KPI data: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
