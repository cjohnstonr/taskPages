"""
KPI Dashboard - Data Queries
Aggregates data from ClickUp and Supabase for dashboard metrics
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import requests

logger = logging.getLogger(__name__)

CLICKUP_API_KEY = os.getenv('CLICKUP_API_KEY')
CLICKUP_TEAM_ID = os.getenv('CLICKUP_TEAM_ID', '9011954126')
CLICKUP_BASE_URL = "https://api.clickup.com/api/v2"


def get_clickup_headers() -> Dict[str, str]:
    """Get headers for ClickUp API requests"""
    return {
        "Authorization": CLICKUP_API_KEY,
        "Content-Type": "application/json"
    }


def get_workspace_tasks_summary() -> Dict[str, Any]:
    """
    Get summary of tasks across workspace

    Returns:
        Dict with task statistics
    """
    try:
        headers = get_clickup_headers()

        # Get all spaces in team
        spaces_response = requests.get(
            f"{CLICKUP_BASE_URL}/team/{CLICKUP_TEAM_ID}/space",
            headers=headers,
            params={"archived": "false"},
            timeout=10
        )
        spaces_response.raise_for_status()
        spaces = spaces_response.json().get('spaces', [])

        total_tasks = 0
        tasks_by_status = {
            'open': 0,
            'in_progress': 0,
            'completed': 0,
            'blocked': 0
        }

        # Get tasks from each space (limited sample for KPI dashboard)
        for space in spaces[:3]:  # Limit to first 3 spaces for performance
            space_id = space['id']

            tasks_response = requests.get(
                f"{CLICKUP_BASE_URL}/space/{space_id}/task",
                headers=headers,
                params={
                    "archived": "false",
                    "page": 0,
                    "order_by": "updated",
                    "reverse": "true",
                    "subtasks": "false",
                    "include_closed": "true"
                },
                timeout=10
            )

            if tasks_response.ok:
                tasks = tasks_response.json().get('tasks', [])
                total_tasks += len(tasks)

                for task in tasks:
                    status = task.get('status', {}).get('status', '').lower()

                    if 'complete' in status or 'closed' in status or 'done' in status:
                        tasks_by_status['completed'] += 1
                    elif 'progress' in status or 'doing' in status:
                        tasks_by_status['in_progress'] += 1
                    elif 'block' in status or 'wait' in status:
                        tasks_by_status['blocked'] += 1
                    else:
                        tasks_by_status['open'] += 1

        return {
            'total_tasks': total_tasks,
            'by_status': tasks_by_status,
            'spaces_count': len(spaces)
        }

    except Exception as e:
        logger.error(f"Error fetching workspace tasks summary: {e}")
        return {
            'total_tasks': 0,
            'by_status': {'open': 0, 'in_progress': 0, 'completed': 0, 'blocked': 0},
            'spaces_count': 0,
            'error': str(e)
        }


def get_escalation_metrics() -> Dict[str, Any]:
    """
    Get escalation statistics from custom fields

    Returns:
        Dict with escalation metrics
    """
    try:
        # This would query tasks with escalation custom fields
        # For now, return placeholder data
        # TODO: Implement actual query based on escalation field IDs

        return {
            'total_escalations': 0,
            'pending': 0,
            'resolved': 0,
            'level_1': 0,
            'level_2': 0
        }

    except Exception as e:
        logger.error(f"Error fetching escalation metrics: {e}")
        return {
            'total_escalations': 0,
            'pending': 0,
            'resolved': 0,
            'level_1': 0,
            'level_2': 0,
            'error': str(e)
        }


def get_team_activity_summary() -> Dict[str, Any]:
    """
    Get team activity summary for the past 7 days

    Returns:
        Dict with activity metrics
    """
    try:
        headers = get_clickup_headers()

        # Get team members
        team_response = requests.get(
            f"{CLICKUP_BASE_URL}/team",
            headers=headers,
            timeout=10
        )
        team_response.raise_for_status()
        teams = team_response.json().get('teams', [])

        if not teams:
            return {'members_count': 0, 'active_members': 0}

        team = teams[0]
        members_count = len(team.get('members', []))

        return {
            'members_count': members_count,
            'active_members': members_count,  # Placeholder
            'team_name': team.get('name', 'Unknown')
        }

    except Exception as e:
        logger.error(f"Error fetching team activity: {e}")
        return {
            'members_count': 0,
            'active_members': 0,
            'error': str(e)
        }


def get_kpi_data(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get all KPI data for dashboard

    Args:
        user: User object with email and role

    Returns:
        Dict with all KPI metrics
    """
    logger.info(f"Fetching KPI data for user: {user.get('email')}")

    # Aggregate all metrics
    tasks_summary = get_workspace_tasks_summary()
    escalation_metrics = get_escalation_metrics()
    team_activity = get_team_activity_summary()

    return {
        'tasks': tasks_summary,
        'escalations': escalation_metrics,
        'team': team_activity,
        'timestamp': datetime.now().isoformat(),
        'user_role': user.get('role', 'user')
    }
