"""
Secure Flask backend server with Google OAuth authentication
Handles ClickUp API interactions with authentication and security
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, session, render_template
from flask_session import Session
from flask_cors import CORS
from dotenv import load_dotenv
import redis
import requests
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

# Load environment variables FIRST (before any imports that read from os.environ)
load_dotenv()

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

# Configure logging (before using logger)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import security modules (AFTER load_dotenv so config reads correct env vars)
from config.security import SecureConfig
from auth.oauth_handler import auth_bp, init_redis, login_required
from auth.security_middleware import SecurityMiddleware, RateLimiter

# Import portal modules
from portal import PortalRegistry
from portal.apps.kpi_dashboard import KPIDashboardApp

# Note: OpenAI removed - using n8n for AI analysis instead

# Initialize Flask app with security config
app = Flask(__name__)
SecureConfig.init_app(app)

# Initialize Redis for sessions
if os.environ.get('DISABLE_REDIS', 'false').lower() == 'true':
    logger.warning("Redis disabled by environment variable - using filesystem sessions")
    redis_client = None
    app.config['SESSION_TYPE'] = 'filesystem'
    # Fix for Python 3.13 compatibility
    app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'
    app.config['SESSION_FILE_THRESHOLD'] = 100
    Session(app)
else:
    try:
        redis_client = init_redis(app)
        app.config['SESSION_REDIS'] = redis_client
        Session(app)
        logger.info("Redis session management initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        logger.warning("Falling back to filesystem sessions")
        redis_client = None
        app.config['SESSION_TYPE'] = 'filesystem'
        # Fix for Python 3.13 compatibility
        app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'
        app.config['SESSION_FILE_THRESHOLD'] = 100
        Session(app)

# Initialize security middleware
security_middleware = SecurityMiddleware(app)

# Initialize rate limiter
rate_limiter = RateLimiter(redis_client, default_limit='100 per hour')

# Configure CORS with security
CORS(app, 
     origins=app.config['CORS_ORIGINS'],
     supports_credentials=app.config['CORS_SUPPORTS_CREDENTIALS'],
     methods=app.config['CORS_METHODS'],
     allow_headers=app.config['CORS_ALLOW_HEADERS'])

# Register authentication blueprint
app.register_blueprint(auth_bp)

# =====================================================
# Portal Setup - Modular App Framework
# =====================================================

# Initialize portal registry
portal_registry = PortalRegistry()

# Register portal apps
kpi_dashboard_app = KPIDashboardApp()
portal_registry.register(kpi_dashboard_app)
app.register_blueprint(kpi_dashboard_app.get_blueprint())

logger.info(f"Portal initialized with {portal_registry.get_app_count()} apps")

# ClickUp API Configuration
CLICKUP_API_KEY = os.getenv('CLICKUP_API_KEY')
CLICKUP_TEAM_ID = os.getenv('CLICKUP_TEAM_ID', '9011954126')
CLICKUP_BASE_URL = "https://api.clickup.com/api/v2"

# Custom field IDs
FIELD_IDS = {
    'WAIT_CONFIG': '993f6a27-54e9-4901-a846-20f87a8694b0',
    'WAIT_STATUS': '02486fba-7ddc-49fa-a18e-7a772d23132a',
    'AI_PROPOSED_ACTION': '6c4ca5f9-d9eb-453a-8058-2cdfe40b0ea0',
    'AI_PROPOSED_VALUE': '3c28debd-e8ea-446b-b145-afd982ffe9ce',
    'PROCESS_TEXT': 'b2587292-c1bc-4ee0-8dcb-a69db68d5fe8',
    'ACCUMULATIVE_CONTEXT': '08cb7050-9860-44c8-960c-30862004f95b',
    'STEP_INSIGHTS': 'd6fe462e-d163-488a-af80-7861c42c789b',
    'STEP_NUMBER': '68441ecb-470b-441c-ae24-916688595c05',
    'EXECUTED': '13d4d660-432d-4033-9805-2ffc7d793c92',
    'HUMAN_APPROVED_ACTION': 'a441971f-6fa4-41fd-91d9-e38b31266698',
    'HUMAN_APPROVED_VALUE': '6f6830f9-90f8-4614-a75d-0ab708c245b9',
    'LIBRARY_LEVEL': 'e49ccff6-f042-4e47-b452-0812ba128cfb'
}

PROCESS_LIBRARY_TYPE = 1018  # custom_item_id for Process Library tasks

# Thread pool for parallel requests
executor = ThreadPoolExecutor(max_workers=10)


class ClickUpService:
    """Service class for ClickUp API interactions"""
    
    def __init__(self):
        if not CLICKUP_API_KEY:
            raise ValueError("CLICKUP_API_KEY environment variable is required")
        
        self.headers = {
            "Authorization": CLICKUP_API_KEY,
            "Content-Type": "application/json"
        }
    
    def get_task(self, task_id: str, custom_task_ids: bool = False, 
                 include_subtasks: bool = False) -> Dict[str, Any]:
        """Fetch task details from ClickUp"""
        params = {"team_id": CLICKUP_TEAM_ID}
        if custom_task_ids:
            params["custom_task_ids"] = "true"
        if include_subtasks:
            params["include_subtasks"] = "true"
        
        url = f"{CLICKUP_BASE_URL}/task/{task_id}"
        response = requests.get(url, headers=self.headers, params=params, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Failed to get task {task_id}: {response.text}")
            response.raise_for_status()
        
        return response.json()
    
    def get_task_comments(self, task_id: str, start: int = 0, limit: int = 10) -> Dict[str, Any]:
        """Fetch comments for a ClickUp task"""
        url = f"{CLICKUP_BASE_URL}/task/{task_id}/comment"
        params = {
            "team_id": CLICKUP_TEAM_ID,
            "start": start,
            "limit": min(limit, 100)  # ClickUp max is 100
        }
        
        response = requests.get(url, headers=self.headers, params=params, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Failed to get comments for task {task_id}: {response.text}")
            response.raise_for_status()
        
        data = response.json()
        
        # Process and normalize the comment data
        comments = []
        for comment in data.get('comments', []):
            # Format the date for frontend compatibility
            raw_date = comment.get('date')
            date_formatted = None
            if raw_date:
                try:
                    from datetime import datetime
                    timestamp = int(raw_date) if isinstance(raw_date, str) else raw_date
                    dt = datetime.fromtimestamp(timestamp / 1000)  # ClickUp uses milliseconds
                    date_formatted = dt.strftime('%b %d, %Y')
                except (ValueError, TypeError):
                    date_formatted = 'Invalid date'
            
            comments.append({
                'id': comment.get('id'),
                'text': comment.get('comment_text', ''),
                'date': comment.get('date'),
                'date_formatted': date_formatted or 'No date',
                'user': {
                    'id': comment.get('user', {}).get('id'),
                    'username': comment.get('user', {}).get('username', 'Unknown'),
                    'email': comment.get('user', {}).get('email', ''),
                    'initials': comment.get('user', {}).get('initials', '??'),
                    'color': comment.get('user', {}).get('color', '#808080')
                }
            })
        
        return {
            'comments': comments,
            'has_more': len(comments) == limit,  # If we got a full page, there might be more
            'total': len(comments)  # ClickUp doesn't always provide total count
        }
    
    def update_custom_field(self, task_id: str, field_id: str, value: Any) -> Dict[str, Any]:
        """Update a custom field on a task"""
        url = f"{CLICKUP_BASE_URL}/task/{task_id}/field/{field_id}"
        data = {"value": value}
        
        response = requests.post(url, headers=self.headers, json=data, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Failed to update field {field_id} on task {task_id}: {response.text}")
            response.raise_for_status()
        
        return response.json()
    
    def find_process_library_root(self, start_task_id: str) -> Dict[str, Any]:
        """Find the top-level Process Library parent task and its parent"""
        current_task = self.get_task(start_task_id, custom_task_ids=True)
        last_process_library_task = None
        parent_task = None
        visited = set()  # Prevent infinite loops
        max_depth = 10  # Safety limit
        depth = 0
        
        # If the starting task is a Process Library task, include it
        if current_task.get('custom_item_id') == PROCESS_LIBRARY_TYPE:
            last_process_library_task = current_task
        
        # Traverse up the parent chain
        while current_task.get('parent') and current_task['id'] not in visited and depth < max_depth:
            visited.add(current_task['id'])
            depth += 1
            logger.info(f"Checking task {current_task['id']} (type: {current_task.get('custom_item_id')})")
            
            try:
                potential_parent = self.get_task(current_task['parent'], custom_task_ids=True)
                
                if potential_parent.get('custom_item_id') == PROCESS_LIBRARY_TYPE:
                    # This parent is still a Process Library task
                    last_process_library_task = potential_parent
                    current_task = potential_parent
                else:
                    # This parent is NOT a Process Library task, so we stop
                    parent_task = potential_parent
                    logger.info(f"Found parent task: {parent_task['id']} - {parent_task.get('name')}")
                    break
            except Exception as e:
                logger.error(f"Error fetching parent task: {e}")
                break
        
        logger.info(f"Process Library root found: {last_process_library_task.get('id') if last_process_library_task else None}")
        logger.info(f"Parent task found: {parent_task.get('id') if parent_task else None}")
        
        return {
            'process_root': last_process_library_task,
            'parent_task': parent_task  # May be None if Process Library is top-level
        }
    
    def fetch_subtasks_with_details(self, parent_task_id: str) -> List[Dict[str, Any]]:
        """Fetch all subtasks with their custom fields"""
        # First get parent with subtasks to get IDs
        parent_with_subtasks = self.get_task(parent_task_id, include_subtasks=True)
        
        subtasks = parent_with_subtasks.get('subtasks', [])
        if not subtasks:
            logger.info('No subtasks found')
            return []
        
        logger.info(f'Found {len(subtasks)} subtasks')
        
        # Fetch each subtask individually to get custom fields (in parallel)
        def fetch_subtask(subtask):
            return self.get_task(subtask['id'], custom_task_ids=True)
        
        # Use thread pool to fetch subtasks in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            subtask_details = list(executor.map(fetch_subtask, subtasks))
        
        # Sort by step number
        def get_step_number(task):
            for field in task.get('custom_fields', []):
                if field['id'] == FIELD_IDS['STEP_NUMBER']:
                    value = field.get('value', 0)
                    if value:
                        try:
                            # Try to convert to float to handle decimals like "2.1"
                            return float(value)
                        except (ValueError, TypeError):
                            # If conversion fails, return 0
                            return 0
                    return 0
            return 0
        
        sorted_subtasks = sorted(subtask_details, key=get_step_number)
        return sorted_subtasks


# Initialize service
clickup_service = ClickUpService()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint - minimal information"""
    return 'OK', 200


@app.route('/api/auth/check', methods=['GET'])
def auth_check():
    """Check if user is authenticated for API access"""
    if 'session_id' in session:
        return jsonify({"authenticated": True}), 200
    return jsonify({"authenticated": False}), 401


# ============= PROTECTED API ROUTES =============
# All routes below require authentication

@app.route('/api/wait-node/initialize/<task_id>', methods=['GET'])
@login_required
@rate_limiter.rate_limit(limit='50 per minute')
def initialize_wait_node(task_id):
    """
    Combined endpoint to fetch all necessary data for wait node interface
    Returns root task, wait task, and all subtasks in a single response
    """
    try:
        logger.info(f"Initializing wait node for task: {task_id} by user: {request.user.get('email')}")
        
        # Find process library root and parent
        result = clickup_service.find_process_library_root(task_id)
        if not result.get('process_root'):
            return jsonify({"error": "Could not find Process Library root task"}), 404
        
        root_task = result['process_root']
        parent_task = result.get('parent_task')  # May be None if Process Library is top-level
        
        # Get wait task details
        wait_task = clickup_service.get_task(task_id, custom_task_ids=True)
        
        # Get all subtasks
        subtasks = clickup_service.fetch_subtasks_with_details(root_task['id'])
        
        # Build hierarchy info for clarity
        hierarchy = {
            "parent_id": parent_task['id'] if parent_task else None,
            "parent_name": parent_task['name'] if parent_task else None,
            "process_library_id": root_task['id'],
            "process_library_name": root_task['name'],
            "wait_node_id": wait_task['id'],
            "wait_node_name": wait_task['name']
        }
        
        logger.info(f"Hierarchy: Parent={hierarchy['parent_name']}, Process={hierarchy['process_library_name']}, Wait={hierarchy['wait_node_name']}")
        
        return jsonify({
            "parent_task": parent_task,  # NEW: The actual parent (may be None)
            "root_task": root_task,
            "wait_task": wait_task,
            "main_task": root_task,  # Keep for backward compatibility
            "subtasks": subtasks,
            "hierarchy": hierarchy  # NEW: Clear hierarchy info
        })
    
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error in initialize_wait_node: {e}")
        return jsonify({"error": "Failed to fetch task data"}), e.response.status_code if e.response else 500
    except Exception as e:
        logger.error(f"Error in initialize_wait_node: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/wait-node/approve/<task_id>', methods=['POST'])
@login_required
@rate_limiter.rate_limit(limit='10 per minute')
def approve_task(task_id):
    """
    Handle approval submission
    Updates multiple custom fields and returns verified task data
    """
    try:
        approval_data = request.json
        logger.info(f"Processing approval for task {task_id} by user: {request.user.get('email')}")
        
        if not approval_data:
            return jsonify({"error": "No approval data provided"}), 400
        
        # Validate approval data
        allowed_fields = set(FIELD_IDS.values())
        for field_id in approval_data.keys():
            if field_id not in allowed_fields:
                return jsonify({"error": f"Invalid field ID: {field_id}"}), 400
        
        # Update fields in parallel
        results = []
        errors = []
        
        def update_field(field_id, value):
            try:
                return clickup_service.update_custom_field(task_id, field_id, value)
            except Exception as e:
                errors.append({"field_id": field_id, "error": str(e)})
                return None
        
        # Use thread pool for parallel updates
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for field_id, value in approval_data.items():
                futures.append(executor.submit(update_field, field_id, value))
            
            for future in futures:
                result = future.result()
                if result:
                    results.append(result)
        
        if errors:
            logger.error(f"Errors updating fields: {errors}")
            return jsonify({
                "success": False,
                "errors": errors,
                "partial_updates": results
            }), 500
        
        # Verify the update by fetching the task again
        import time
        time.sleep(1)  # Give ClickUp a moment to process
        verified_task = clickup_service.get_task(task_id, custom_task_ids=True)
        
        # Log approval action for audit trail
        logger.info(f"Approval completed for task {task_id} by {request.user.get('email')}")
        
        return jsonify({
            "success": True,
            "task": verified_task,
            "updates": results
        })
    
    except Exception as e:
        logger.error(f"Error in approve_task: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/task/<task_id>', methods=['GET'])
@login_required
@rate_limiter.rate_limit(limit='100 per minute')
def get_task(task_id):
    """Get task details"""
    try:
        custom_task_ids = request.args.get('custom_task_ids', 'false').lower() == 'true'
        include_subtasks = request.args.get('include_subtasks', 'false').lower() == 'true'
        
        task = clickup_service.get_task(task_id, custom_task_ids, include_subtasks)
        return jsonify(task)
    
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": "Failed to fetch task"}), e.response.status_code if e.response else 500
    except Exception as e:
        logger.error(f"Error in get_task: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/task/<task_id>/process-root', methods=['GET'])
@login_required
@rate_limiter.rate_limit(limit='50 per minute')
def get_process_root(task_id):
    """Find process library root for a task"""
    try:
        root_task = clickup_service.find_process_library_root(task_id)
        if not root_task:
            return jsonify({"error": "Process library root not found"}), 404
        return jsonify(root_task)
    
    except Exception as e:
        logger.error(f"Error in get_process_root: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/task/<task_id>/subtasks-detailed', methods=['GET'])
@login_required
@rate_limiter.rate_limit(limit='50 per minute')
def get_subtasks_detailed(task_id):
    """Get all subtasks with details"""
    try:
        subtasks = clickup_service.fetch_subtasks_with_details(task_id)
        return jsonify({"subtasks": subtasks})
    
    except Exception as e:
        logger.error(f"Error in get_subtasks_detailed: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/task/<task_id>/comments', methods=['GET'])
@login_required
@rate_limiter.rate_limit(limit='100 per minute')
def get_task_comments(task_id):
    """Get comments for a task from ClickUp"""
    try:
        # Get pagination parameters
        start = request.args.get('start', 0, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        logger.info(f"Fetching comments for task {task_id} (start={start}, limit={limit})")
        
        # Fetch comments from ClickUp API
        comments_data = clickup_service.get_task_comments(task_id, start=start, limit=limit)
        
        logger.info(f"Retrieved {len(comments_data['comments'])} comments for task {task_id}")
        
        return jsonify(comments_data)
    
    except requests.exceptions.RequestException as e:
        logger.error(f"ClickUp API error in get_task_comments for task {task_id}: {e}")
        return jsonify({"error": "Failed to fetch comments from ClickUp"}), 502
    except Exception as e:
        logger.error(f"Error in get_task_comments for task {task_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/task/<task_id>/field/<field_id>', methods=['PUT'])
@login_required
@rate_limiter.rate_limit(limit='20 per minute')
def update_field(task_id, field_id):
    """Update a single custom field"""
    try:
        # Validate field ID
        if field_id not in FIELD_IDS.values():
            return jsonify({"error": "Invalid field ID"}), 400
        
        data = request.json
        if 'value' not in data:
            return jsonify({"error": "Value is required"}), 400
        
        result = clickup_service.update_custom_field(task_id, field_id, data['value'])
        
        # Log field update for audit
        logger.info(f"Field {field_id} updated on task {task_id} by {request.user.get('email')}")
        
        return jsonify(result)
    
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": "Failed to update field"}), e.response.status_code if e.response else 500
    except Exception as e:
        logger.error(f"Error in update_field: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/task/<task_id>/custom-field', methods=['PUT'])
@login_required
@rate_limiter.rate_limit(limit='50 per minute')
def update_single_custom_field(task_id):
    """
    Update a single custom field on a task
    Used by the editable page for auto-save functionality
    """
    try:
        data = request.json
        
        if not data or 'field_id' not in data or 'value' not in data:
            return jsonify({"error": "field_id and value are required"}), 400
        
        field_id = data['field_id']
        value = data['value']
        field_type = data.get('field_type', 'text')
        
        # Special handling for checkbox type
        if field_type == 'checkbox':
            value = value in [True, 'true', 'True', 1, '1']
        
        # Make the ClickUp API call
        url = f"https://api.clickup.com/api/v2/task/{task_id}/field/{field_id}"
        payload = {"value": value}
        
        headers = {
            "Authorization": CLICKUP_API_KEY,
            "Content-Type": "application/json"
        }
        
        params = {"custom_task_ids": "true", "team_id": CLICKUP_TEAM_ID}
        
        response = requests.post(url, headers=headers, params=params, json=payload)
        response.raise_for_status()
        
        logger.info(f"Updated field {field_id} on task {task_id} by {request.user.get('email')}")
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "field_id": field_id,
            "value": value
        })
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"ClickUp API error updating field: {e.response.text if e.response else str(e)}")
        return jsonify({"error": "Failed to update field"}), e.response.status_code if e.response else 500
    except Exception as e:
        logger.error(f"Error updating custom field: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/task/<task_id>', methods=['DELETE'])
@login_required
@rate_limiter.rate_limit(limit='20 per minute')
def delete_task(task_id):
    """
    Delete a task from ClickUp
    Used by the editable page for step deletion
    """
    try:
        # Make the ClickUp API call
        url = f"https://api.clickup.com/api/v2/task/{task_id}"
        
        headers = {
            "Authorization": CLICKUP_API_KEY
        }
        
        params = {"custom_task_ids": "true", "team_id": CLICKUP_TEAM_ID}
        
        response = requests.delete(url, headers=headers, params=params)
        response.raise_for_status()
        
        logger.info(f"Deleted task {task_id} by {request.user.get('email')}")
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": "Task deleted successfully"
        })
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"ClickUp API error deleting task: {e.response.text if e.response else str(e)}")
        return jsonify({"error": "Failed to delete task"}), e.response.status_code if e.response else 500
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        return jsonify({"error": str(e)}), 500


# =====================================================
# Task Helper API Endpoints
# =====================================================

@app.route('/api/task-helper/initialize/<task_id>', methods=['GET'])
@login_required
@rate_limiter.rate_limit(limit='50 per minute')
def initialize_task_helper(task_id):
    """
    Initialize task helper with task data and hierarchy
    Uses ClickUpService to properly fetch task with custom fields
    """
    try:
        logger.info(f"Initializing task-helper for task: {task_id} by user: {request.user.get('email')}")

        # Fetch the main task with custom fields using the service
        main_task = clickup_service.get_task(task_id, custom_task_ids=True, include_subtasks=True)

        # Initialize response structure
        response_data = {
            "main_task": main_task,
            "parent_task": None,
            "subtasks": [],
            "hierarchy": {
                "has_parent": False,
                "parent_id": None,
                "is_subtask": False
            }
        }

        # Check if this task has a parent
        if main_task.get('parent'):
            parent_id = main_task['parent']
            try:
                parent_task = clickup_service.get_task(parent_id, custom_task_ids=True)
                response_data["parent_task"] = parent_task
                response_data["hierarchy"]["has_parent"] = True
                response_data["hierarchy"]["parent_id"] = parent_id
                response_data["hierarchy"]["is_subtask"] = True
            except Exception as e:
                logger.warning(f"Could not fetch parent task {parent_id}: {e}")

        # Get subtasks if any (already included with include_subtasks=True, but get full details)
        if main_task.get('subtasks'):
            subtask_ids = [st['id'] for st in main_task['subtasks']]
            for subtask_id in subtask_ids[:10]:  # Limit to 10 for performance
                try:
                    subtask = clickup_service.get_task(subtask_id, custom_task_ids=True)
                    response_data["subtasks"].append(subtask)
                except Exception as e:
                    logger.warning(f"Could not fetch subtask {subtask_id}: {e}")

        logger.info(f"Successfully initialized task-helper for {task_id} with {len(response_data['subtasks'])} subtasks")
        return jsonify(response_data)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return jsonify({"error": "Task not found"}), 404
        logger.error(f"ClickUp API error: {e}")
        return jsonify({"error": "Failed to fetch task from ClickUp"}), 500
    except Exception as e:
        logger.error(f"Error initializing task helper for task {task_id}: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


# ============================================================================
# PROPERTY LINK VALIDATION HELPERS (Phase 2)
# ============================================================================

def is_custom_task_id(task_id: str) -> bool:
    """
    Detect if task_id is a custom ID format (e.g., TICKET-43999).

    Args:
        task_id: Task ID to check

    Returns:
        True if custom ID format, False if regular ID
    """
    return 'TICKET' in task_id.upper() or '-' in task_id or task_id[0].isupper()


def get_custom_field_value(task: Dict[str, Any], field_id: str) -> Optional[Any]:
    """
    Extract custom field value from task.

    Args:
        task: Task data dict
        field_id: Custom field ID to search for

    Returns:
        Field value or None if not found/empty
    """
    custom_fields = task.get('custom_fields', [])
    for field in custom_fields:
        if field['id'] == field_id:
            value = field.get('value')
            if value is None or value == [] or value == '':
                return None
            return value
    return None


def get_parent_task_id(task: Dict[str, Any]) -> Optional[str]:
    """
    Extract parent task ID from task structure.

    Args:
        task: Task data dict

    Returns:
        Parent task ID or None if no parent
    """
    parent_id = task.get('parent')
    if not parent_id:
        parent_id = task.get('top_level_parent')
    return parent_id


def ensure_property_link(task_id: str, clickup_token: str, team_id: str = '9011954126') -> Optional[List[str]]:
    """
    Ensure task has property_link, propagate from parent if missing.

    Args:
        task_id: Task ID (can be custom like TICKET-43999 or regular)
        clickup_token: ClickUp API token
        team_id: ClickUp team/workspace ID

    Returns:
        List of property link task IDs, or None if not found
    """
    PROPERTY_LINK_FIELD_ID = '73999194-0433-433d-a27c-4d9c5f194fd0'
    BASE_URL = 'https://api.clickup.com/api/v2'
    headers = {'Authorization': clickup_token, 'Content-Type': 'application/json'}

    # Step 1: Get task
    params = {'team_id': team_id}
    if is_custom_task_id(task_id):
        params['custom_task_ids'] = 'true'

    response = requests.get(f'{BASE_URL}/task/{task_id}', headers=headers, params=params)
    response.raise_for_status()
    task = response.json()
    task_regular_id = task['id']  # Always get regular ID for POST requests

    # Step 2: Check if property_link exists
    property_link = get_custom_field_value(task, PROPERTY_LINK_FIELD_ID)
    if property_link:
        # Extract just the IDs
        return [p['id'] for p in property_link]

    # Step 3: Get parent task
    parent_id = get_parent_task_id(task)
    if not parent_id:
        return None

    # Step 4: Get parent's property_link
    parent_response = requests.get(
        f'{BASE_URL}/task/{parent_id}',
        headers=headers,
        params={'team_id': team_id}
    )
    parent_response.raise_for_status()
    parent_task = parent_response.json()

    parent_property_link = get_custom_field_value(parent_task, PROPERTY_LINK_FIELD_ID)
    if not parent_property_link:
        return None

    # Step 5: Extract IDs and set on subtask
    property_link_ids = [p['id'] for p in parent_property_link]

    # CRITICAL: Use regular task ID, not custom ID
    # Payload format: {"value": {"add": [task_ids]}}
    set_response = requests.post(
        f'{BASE_URL}/task/{task_regular_id}/field/{PROPERTY_LINK_FIELD_ID}',
        headers=headers,
        json={'value': {'add': property_link_ids}}
    )
    set_response.raise_for_status()

    logger.info(f"Propagated property_link from parent {parent_id} to subtask {task_id}: {property_link_ids}")
    return property_link_ids


@app.route('/api/task-helper/validate-property-link/<task_id>', methods=['GET'])
@login_required
@rate_limiter.rate_limit(limit='30 per minute')
def validate_property_link(task_id):
    """
    Validate and ensure task has property_link (Phase 2).
    Propagates from parent if missing.
    """
    try:
        clickup_token = os.getenv('CLICKUP_API_KEY')
        if not clickup_token:
            logger.error("ClickUp API key not configured")
            return jsonify({"error": "ClickUp integration not configured"}), 500

        # Call ensure_property_link helper
        property_link_ids = ensure_property_link(task_id, clickup_token)

        if property_link_ids:
            return jsonify({
                "success": True,
                "has_property_link": True,
                "property_link_ids": property_link_ids,
                "message": "Property link validated"
            })
        else:
            return jsonify({
                "success": False,
                "has_property_link": False,
                "property_link_ids": None,
                "error": "No property link found on task or parent. This task must be linked to a property."
            }), 400

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return jsonify({"error": "Task not found"}), 404
        logger.error(f"ClickUp API error validating property link: {e}")
        return jsonify({"error": "Failed to validate property link"}), 500
    except Exception as e:
        logger.error(f"Error validating property link for task {task_id}: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route('/api/task-helper/generate-ai/<task_id>', methods=['POST'])
@login_required
@rate_limiter.rate_limit(limit='10 per minute')
def generate_ai_analysis(task_id):
    """
    Generate or retrieve AI analysis fields (summary + suggestion)
    WRITES to ClickUp immediately if fields don't exist
    Does NOT change escalation status - only generates AI fields
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        escalation_reason = data.get('reason', '').strip()

        if not escalation_reason:
            return jsonify({"error": "Escalation reason is required for AI analysis"}), 400

        # Log AI generation attempt
        logger.info(f"AI analysis requested for task {task_id} by {request.user.get('email')}")

        # Get ClickUp API configuration
        clickup_token = os.getenv('CLICKUP_API_KEY')
        if not clickup_token:
            logger.error("ClickUp API key not configured")
            return jsonify({"error": "ClickUp integration not configured"}), 500

        # Field IDs for AI analysis
        FIELD_AI_SUMMARY = 'e9e831f2-b439-4067-8e88-6b715f4263b2'  # ESCALATION_REASON_AI
        FIELD_AI_SUGGESTION = 'bc5e9359-01cd-408f-adb9-c7bdf1f2dd29'  # ESCALATION_AI_SUGGESTION

        # Fetch task to check for existing AI fields
        params = {}
        if is_custom_task_id(task_id):
            params = {
                'custom_task_ids': 'true',
                'team_id': '9011954126'
            }

        task_response = requests.get(
            f"https://api.clickup.com/api/v2/task/{task_id}",
            headers={"Authorization": clickup_token},
            params=params
        )

        if not task_response.ok:
            logger.error(f"Failed to fetch task {task_id}: {task_response.text}")
            return jsonify({"error": "Failed to fetch task from ClickUp"}), 500

        task = task_response.json()

        # Check if BOTH AI fields already exist (cached)
        existing_summary = get_custom_field_value(task, FIELD_AI_SUMMARY)
        existing_suggestion = get_custom_field_value(task, FIELD_AI_SUGGESTION)

        # Check if user wants to force regeneration (bypass cache)
        force_regenerate = data.get('force_regenerate', False)

        # If BOTH exist AND not forcing regeneration, return cached values (no n8n call)
        if existing_summary and existing_suggestion and not force_regenerate:
            logger.info(f"Using cached AI fields for task {task_id}")
            return jsonify({
                'success': True,
                'ai_summary': existing_summary,
                'ai_suggestion': existing_suggestion,
                'cached': True
            })

        # Log if regenerating
        if force_regenerate:
            logger.info(f"Force regenerating AI fields for task {task_id} (bypassing cache)")

        # Call n8n to generate BOTH AI fields
        n8n_url = 'https://n8n.oodahost.ai/webhook/d176be54-1622-4b73-a5ce-e02d619a53b9'
        logger.info(f"Calling n8n to generate AI analysis for task {task_id}")

        try:
            n8n_response = requests.post(
                n8n_url,
                json={'task_id': task_id},
                timeout=30  # 30 second timeout
            )

            if n8n_response.ok:
                n8n_data = n8n_response.json()
                ai_summary = n8n_data.get('summary', '')
                ai_suggestion = n8n_data.get('suggestion', '')

                if not ai_summary or not ai_suggestion:
                    logger.error(f"n8n returned incomplete data: summary={bool(ai_summary)}, suggestion={bool(ai_suggestion)}")
                    return jsonify({
                        'success': False,
                        'error': 'n8n returned incomplete AI analysis'
                    }), 500

                # WRITE both fields to ClickUp IMMEDIATELY
                headers = {
                    "Authorization": clickup_token,
                    "Content-Type": "application/json"
                }

                fields_to_update = [
                    (FIELD_AI_SUMMARY, {"value": ai_summary}),
                    (FIELD_AI_SUGGESTION, {"value": ai_suggestion})
                ]

                for field_id, field_data in fields_to_update:
                    field_response = requests.post(
                        f"https://api.clickup.com/api/v2/task/{task_id}/field/{field_id}",
                        headers=headers,
                        json=field_data
                    )

                    if not field_response.ok:
                        logger.error(f"Failed to write AI field {field_id} to ClickUp: {field_response.text}")
                        return jsonify({
                            'success': False,
                            'error': f'Failed to save AI analysis to ClickUp'
                        }), 500
                    else:
                        logger.info(f"Successfully wrote AI field {field_id} to ClickUp")

                logger.info(f"AI fields written to ClickUp for task {task_id}")

                return jsonify({
                    'success': True,
                    'ai_summary': ai_summary,
                    'ai_suggestion': ai_suggestion,
                    'cached': False
                })

            else:
                logger.error(f"n8n webhook failed: {n8n_response.status_code} - {n8n_response.text}")
                return jsonify({
                    'success': False,
                    'error': f'n8n error: {n8n_response.status_code}'
                }), 500

        except requests.exceptions.Timeout:
            logger.error(f"n8n webhook timed out after 30 seconds for task {task_id}")
            return jsonify({
                'success': False,
                'error': 'n8n timeout after 30 seconds. Please try again.'
            }), 500

        except requests.exceptions.RequestException as n8n_error:
            logger.error(f"Error calling n8n webhook: {n8n_error}")
            return jsonify({
                'success': False,
                'error': f'Network error calling n8n: {str(n8n_error)}'
            }), 500

    except Exception as e:
        logger.error(f"Error generating AI analysis for task {task_id}: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route('/api/task-helper/escalate/<task_id>', methods=['POST'])
@login_required
@rate_limiter.rate_limit(limit='10 per minute')
def escalate_task(task_id):
    """
    Escalate a task - changes status to ESCALATED
    Expects AI fields to already exist in ClickUp (set via /api/task-helper/generate-ai/<task_id>)
    Adds escalation reason, timestamp, and creates notification
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        escalation_reason = data.get('reason', '').strip()
        # Note: ai_summary is now generated by n8n, not from request body
        task_context = data.get('task_context', {})

        if not escalation_reason:
            return jsonify({"error": "Escalation reason is required"}), 400

        # Log escalation attempt for audit
        logger.info(f"Task escalation requested for {task_id} by {request.user.get('email')}")

        # Get ClickUp API configuration
        clickup_token = os.getenv('CLICKUP_API_KEY')
        if not clickup_token:
            logger.error("ClickUp API key not configured")
            return jsonify({"error": "ClickUp integration not configured"}), 500

        # Custom field IDs for escalation - ALL EXIST IN CLICKUP
        escalation_fields = {
            'ESCALATION_REASON_TEXT': 'c6e0281e-9001-42d7-a265-8f5da6b71132',
            'ESCALATION_REASON_AI': 'e9e831f2-b439-4067-8e88-6b715f4263b2',
            'ESCALATION_AI_SUGGESTION': 'bc5e9359-01cd-408f-adb9-c7bdf1f2dd29',
            'ESCALATION_STATUS': '8d784bd0-18e5-4db3-b45e-9a2900262e04',
            'ESCALATION_SUBMITTED_DATE_TIME': '5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f',
            'ESCALATION_RESPONSE_TEXT': 'a077ecc9-1a59-48af-b2cd-42a63f5a7f86',
            'ESCALATION_RESOLVED_DATE_TIME': 'c40bf1c4-7d33-4b2b-8765-0784cd88591a',
            'ESCALATION_AI_GRADE': '629ca244-a6d3-46dd-9f1e-6a0ded40f519',
            'ESCALATION_HISTORY': '94790367-5d1f-4300-8f79-e13819f910d4',
            'ESCALATION_LEVEL': '90d2fec8-7474-4221-84c0-b8c7fb5e4385',  # Dropdown: 0=Shirley, 1=Christian
            'ESCALATION_RFI_STATUS': 'f94c0b4b-0c70-4c23-9633-07af2fa6ddc6',  # Dropdown: 0=RFI Requested, 1=RFI Completed
            'ESCALATION_RFI_REQUEST': '0e7dd6f8-3167-4df5-964e-574734ffd4ed',
            'ESCALATION_RFI_RESPONSE': 'b5c52661-8142-45e0-bec5-14f3c135edbc',
            'PROPERTY_LINK': '73999194-0433-433d-a27c-4d9c5f194fd0'  # Task Relationship field
        }

        # PHASE 3: Ensure property_link exists BEFORE everything else
        logger.info(f"Phase 3: Validating property link for task {task_id}")
        property_link_ids = ensure_property_link(task_id, clickup_token)

        if not property_link_ids:
            logger.error(f"No property link found for task {task_id}")
            return jsonify({
                'success': False,
                'error': 'No property link found. This task must be linked to a property before escalation.'
            }), 400

        logger.info(f"Property link validated: {property_link_ids}")

        # PHASE 3: Fetch task to check for cached AI suggestion
        params = {}
        if is_custom_task_id(task_id):
            params = {
                'custom_task_ids': 'true',
                'team_id': '9011954126'
            }

        task_response = requests.get(
            f"https://api.clickup.com/api/v2/task/{task_id}",
            headers={"Authorization": clickup_token},
            params=params
        )

        if not task_response.ok:
            logger.error(f"Failed to fetch task {task_id}: {task_response.text}")
            return jsonify({"error": "Failed to fetch task from ClickUp"}), 500

        task = task_response.json()

        # PHASE 4: Read AI fields from ClickUp (should already exist from generate-ai endpoint)
        # These fields are written by /api/task-helper/generate-ai/<task_id> before escalation
        ai_summary = get_custom_field_value(task, escalation_fields['ESCALATION_REASON_AI'])
        ai_suggestion = get_custom_field_value(task, escalation_fields['ESCALATION_AI_SUGGESTION'])

        # Use fallback text if AI fields don't exist (they should exist in normal flow)
        if not ai_summary:
            ai_summary = "AI summary not generated - please use 'Generate AI Analysis' button first"
            logger.warning(f"AI summary missing for task {task_id} during escalation")

        if not ai_suggestion:
            ai_suggestion = "AI suggestion not generated - please use 'Generate AI Analysis' button first"
            logger.warning(f"AI suggestion missing for task {task_id} during escalation")

        logger.info(f"Read AI fields from ClickUp for task {task_id}: summary={bool(ai_summary)}, suggestion={bool(ai_suggestion)}")

        # Get escalated_to from request (supervisor selection)
        escalated_to = data.get('escalated_to', '')  # User ID or email

        try:
            # 1. Update task custom fields with escalation data - ONE AT A TIME
            headers = {
                "Authorization": clickup_token,
                "Content-Type": "application/json"
            }
            
            # Set each field individually using the correct API endpoint
            # NOTE: AI fields should already exist from generate-ai endpoint, but we re-write them here for safety
            fields_to_update = [
                (escalation_fields['ESCALATION_REASON_TEXT'], {"value": escalation_reason}),
                (escalation_fields['ESCALATION_REASON_AI'], {"value": ai_summary}),  # Should already exist
                (escalation_fields['ESCALATION_STATUS'], {"value": 1}),  # orderindex 1 = 'Escalated'
                (escalation_fields['ESCALATION_SUBMITTED_DATE_TIME'], {
                    "value": int(datetime.now().timestamp() * 1000),
                    "value_options": {"time": True}  # Include time for date field
                }),
                (escalation_fields['ESCALATION_AI_SUGGESTION'], {"value": ai_suggestion})  # Should already exist
            ]

            # Add escalated_to level if provided (0=Shirley, 1=Christian)
            if escalated_to:
                fields_to_update.append((escalation_fields['ESCALATION_LEVEL'], {"value": escalated_to}))
            
            # Update each field individually
            for field_id, field_data in fields_to_update:
                field_response = requests.post(
                    f"https://api.clickup.com/api/v2/task/{task_id}/field/{field_id}",
                    headers=headers,
                    json=field_data
                )
                
                if not field_response.ok:
                    logger.error(f"Failed to update field {field_id}: {field_response.text}")
                    # Continue trying other fields even if one fails
                else:
                    logger.info(f"Successfully updated field {field_id}")
            
            # All fields attempted, continue with the rest

            # 2. Add escalation comment to task
            escalation_comment = f"""🚨 **TASK ESCALATED**

**Reason**: {escalation_reason}

**AI Summary**: 
{ai_summary}

**Escalated by**: {request.user.get('email')}
**Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

---
*This escalation was generated via Task Helper*"""

            comment_response = requests.post(
                f"https://api.clickup.com/api/v2/task/{task_id}/comment",
                headers={
                    "Authorization": clickup_token,
                    "Content-Type": "application/json"
                },
                json={
                    "comment_text": escalation_comment,
                    "notify_all": True
                }
            )
            
            if not comment_response.ok:
                logger.warning(f"Failed to add escalation comment: {comment_response.text}")
            
            # 3. Add "escalated" tag to task (if it doesn't exist)
            try:
                tag_response = requests.post(
                    f"https://api.clickup.com/api/v2/task/{task_id}/tag/escalated",
                    headers={
                        "Authorization": clickup_token,
                        "Content-Type": "application/json"
                    }
                )
                # Tag addition may fail if tag doesn't exist or task already has it - that's OK
            except Exception as tag_error:
                logger.warning(f"Failed to add escalated tag: {tag_error}")

            # Success response with escalation details
            escalation_id = f"ESC-{task_id}-{int(datetime.now().timestamp())}"
            
            response_data = {
                "success": True,
                "message": "Task escalated successfully and saved to ClickUp",
                "escalation_id": escalation_id,
                "task_id": task_id,
                "escalated_by": request.user.get('email'),
                "escalation_data": {
                    "reason": escalation_reason,
                    "ai_summary": ai_summary,
                    "ai_suggestion": ai_suggestion,  # PHASE 3: Return AI suggestion to frontend
                    "property_link_ids": property_link_ids,  # PHASE 3: Return validated property links
                    "context": task_context,
                    "timestamp": datetime.now().isoformat()
                },
                "clickup_updated": True,
                "comment_added": comment_response.ok
            }
            
            return jsonify(response_data)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"ClickUp API request failed: {e}")
            return jsonify({"error": "Failed to communicate with ClickUp API"}), 500
        
    except Exception as e:
        logger.error(f"Error escalating task {task_id}: {e}")
        return jsonify({"error": f"Failed to escalate task: {str(e)}"}), 500


@app.route('/api/task-helper/supervisor-response/<task_id>', methods=['POST'])
@login_required
@rate_limiter.rate_limit(limit='10 per minute')
def supervisor_response(task_id):
    """
    Handle response to an escalated task (anyone can respond)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        supervisor_response_text = data.get('response', '').strip()
        
        if not supervisor_response_text:
            return jsonify({"error": "Supervisor response is required"}), 400

        # Log supervisor response for audit
        logger.info(f"Supervisor response for task {task_id} by {request.user.get('email')}")

        # Get ClickUp API configuration
        clickup_token = os.getenv('CLICKUP_API_KEY')
        if not clickup_token:
            logger.error("ClickUp API key not configured")
            return jsonify({"error": "ClickUp integration not configured"}), 500

        # Custom field IDs
        escalation_fields = {
            'ESCALATION_STATUS': '8d784bd0-18e5-4db3-b45e-9a2900262e04',
            'SUPERVISOR_RESPONSE': 'a077ecc9-1a59-48af-b2cd-42a63f5a7f86',
            'ESCALATION_RESOLVED_TIMESTAMP': 'c40bf1c4-7d33-4b2b-8765-0784cd88591a'
        }

        try:
            # Update task custom fields with supervisor response - ONE AT A TIME
            headers = {
                "Authorization": clickup_token,
                "Content-Type": "application/json"
            }
            
            # Set each field individually using the correct API endpoint
            fields_to_update = [
                (escalation_fields['SUPERVISOR_RESPONSE'], {"value": supervisor_response_text}),
                (escalation_fields['ESCALATION_STATUS'], {"value": 2}),  # orderindex 2 = 'Resolved'
                (escalation_fields['ESCALATION_RESOLVED_TIMESTAMP'], {
                    "value": int(datetime.now().timestamp() * 1000),
                    "value_options": {"time": True}  # Include time for date field
                })
            ]
            
            # Update each field individually
            for field_id, field_data in fields_to_update:
                field_response = requests.post(
                    f"https://api.clickup.com/api/v2/task/{task_id}/field/{field_id}",
                    headers=headers,
                    json=field_data
                )
                
                if not field_response.ok:
                    logger.error(f"Failed to update field {field_id}: {field_response.text}")
                    # Continue trying other fields even if one fails
                else:
                    logger.info(f"Successfully updated field {field_id}")
            
            # All fields attempted, continue with the rest

            # Add resolution comment to task
            resolution_comment = f"""✅ **ESCALATION RESOLVED**

**Response**: 
{supervisor_response_text}

**Resolved by**: {request.user.get('email')}
**Resolution Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

----
*This resolution was recorded via Task Helper*"""

            comment_response = requests.post(
                f"https://api.clickup.com/api/v2/task/{task_id}/comment",
                headers={
                    "Authorization": clickup_token,
                    "Content-Type": "application/json"
                },
                json={
                    "comment_text": resolution_comment,
                    "notify_all": True
                }
            )
            
            if not comment_response.ok:
                logger.warning(f"Failed to add resolution comment: {comment_response.text}")
            
            # Success response
            response_data = {
                "success": True,
                "message": "Supervisor response recorded successfully",
                "task_id": task_id,
                "resolved_by": request.user.get('email'),
                "resolution": {
                    "response": supervisor_response_text,
                    "timestamp": datetime.now().isoformat()
                },
                "clickup_updated": True
            }
            
            return jsonify(response_data)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"ClickUp API request failed: {e}")
            return jsonify({"error": "Failed to communicate with ClickUp API"}), 500
        
    except Exception as e:
        logger.error(f"Error recording supervisor response for task {task_id}: {e}")
        return jsonify({"error": f"Failed to record supervisor response: {str(e)}"}), 500


@app.route('/api/task-helper/request-info/<task_id>', methods=['POST'])
@login_required
@rate_limiter.rate_limit(limit='10 per minute')
def request_info(task_id):
    """
    Request information from employee (Phase 4: Supervisor Multi-Action UI)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        rfi_question = data.get('question', '').strip()

        if not rfi_question:
            return jsonify({"error": "RFI question is required"}), 400

        # Log RFI request for audit
        logger.info(f"RFI requested for task {task_id} by {request.user.get('email')}")

        # Get ClickUp API configuration
        clickup_token = os.getenv('CLICKUP_API_KEY')
        if not clickup_token:
            logger.error("ClickUp API key not configured")
            return jsonify({"error": "ClickUp integration not configured"}), 500

        # Custom field IDs
        escalation_fields = {
            'ESCALATION_RFI_REQUEST': '0e7dd6f8-3167-4df5-964e-574734ffd4ed',
            'ESCALATION_RFI_STATUS': 'f94c0b4b-0c70-4c23-9633-07af2fa6ddc6',
            'ESCALATION_STATUS': '8d784bd0-18e5-4db3-b45e-9a2900262e04'
        }

        try:
            headers = {
                "Authorization": clickup_token,
                "Content-Type": "application/json"
            }

            # Update fields: RFI_REQUEST, RFI_STATUS=0 (RFI Requested), ESCALATION_STATUS=4 (AWAITING_INFO)
            fields_to_update = [
                (escalation_fields['ESCALATION_RFI_REQUEST'], {"value": rfi_question}),
                (escalation_fields['ESCALATION_RFI_STATUS'], {"value": 0}),  # orderindex 0 = 'RFI Requested'
                (escalation_fields['ESCALATION_STATUS'], {"value": 4})  # orderindex 4 = 'AWAITING_INFO'
            ]

            # Update each field individually
            for field_id, field_data in fields_to_update:
                field_response = requests.post(
                    f"https://api.clickup.com/api/v2/task/{task_id}/field/{field_id}",
                    headers=headers,
                    json=field_data
                )

                if not field_response.ok:
                    logger.error(f"Failed to update field {field_id}: {field_response.text}")
                else:
                    logger.info(f"Successfully updated field {field_id}")

            # Add RFI comment to task
            rfi_comment = f"""❓ **INFORMATION REQUESTED**

**Question**:
{rfi_question}

**Requested by**: {request.user.get('email')}
**Request Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

----
*Please respond with the requested information*"""

            comment_response = requests.post(
                f"https://api.clickup.com/api/v2/task/{task_id}/comment",
                headers=headers,
                json={
                    "comment_text": rfi_comment,
                    "notify_all": True
                }
            )

            if not comment_response.ok:
                logger.warning(f"Failed to add RFI comment: {comment_response.text}")

            # Success response
            response_data = {
                "success": True,
                "message": "Information request sent to employee",
                "task_id": task_id,
                "requested_by": request.user.get('email'),
                "rfi_question": rfi_question,
                "timestamp": datetime.now().isoformat()
            }

            return jsonify(response_data)

        except requests.exceptions.RequestException as e:
            logger.error(f"ClickUp API request failed: {e}")
            return jsonify({"error": "Failed to communicate with ClickUp API"}), 500

    except Exception as e:
        logger.error(f"Error requesting info for task {task_id}: {e}")
        return jsonify({"error": f"Failed to request information: {str(e)}"}), 500


@app.route('/api/task-helper/escalate-to-level-2/<task_id>', methods=['POST'])
@login_required
@rate_limiter.rate_limit(limit='10 per minute')
def escalate_to_level_2(task_id):
    """
    Escalate task to Level 2 (Christian) (Phase 4: Supervisor Multi-Action UI)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        additional_context = data.get('context', '').strip()

        # Log escalation for audit
        logger.info(f"Level 2 escalation for task {task_id} by {request.user.get('email')}")

        # Get ClickUp API configuration
        clickup_token = os.getenv('CLICKUP_API_KEY')
        if not clickup_token:
            logger.error("ClickUp API key not configured")
            return jsonify({"error": "ClickUp integration not configured"}), 500

        # Custom field IDs
        escalation_fields = {
            'ESCALATION_LEVEL': '90d2fec8-7474-4221-84c0-b8c7fb5e4385',
            'ESCALATION_STATUS': '8d784bd0-18e5-4db3-b45e-9a2900262e04'
        }

        try:
            headers = {
                "Authorization": clickup_token,
                "Content-Type": "application/json"
            }

            # Update fields: ESCALATION_LEVEL=1 (Christian), ESCALATION_STATUS=3 (ESCALATED_LEVEL_2)
            fields_to_update = [
                (escalation_fields['ESCALATION_LEVEL'], {"value": 1}),  # orderindex 1 = 'Christian'
                (escalation_fields['ESCALATION_STATUS'], {"value": 3})  # orderindex 3 = 'ESCALATED_LEVEL_2'
            ]

            # Update each field individually
            for field_id, field_data in fields_to_update:
                field_response = requests.post(
                    f"https://api.clickup.com/api/v2/task/{task_id}/field/{field_id}",
                    headers=headers,
                    json=field_data
                )

                if not field_response.ok:
                    logger.error(f"Failed to update field {field_id}: {field_response.text}")
                else:
                    logger.info(f"Successfully updated field {field_id}")

            # Build escalation comment
            l2_comment = f"""⬆️ **ESCALATED TO LEVEL 2 (CHRISTIAN)**

**Escalated by**: {request.user.get('email')}
**Escalation Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"""

            if additional_context:
                l2_comment += f"""

**Additional Context**:
{additional_context}"""

            l2_comment += """

----
*This escalation requires executive review*"""

            comment_response = requests.post(
                f"https://api.clickup.com/api/v2/task/{task_id}/comment",
                headers=headers,
                json={
                    "comment_text": l2_comment,
                    "notify_all": True
                }
            )

            if not comment_response.ok:
                logger.warning(f"Failed to add Level 2 escalation comment: {comment_response.text}")

            # Success response
            response_data = {
                "success": True,
                "message": "Task escalated to Level 2 (Christian)",
                "task_id": task_id,
                "escalated_by": request.user.get('email'),
                "additional_context": additional_context,
                "timestamp": datetime.now().isoformat()
            }

            return jsonify(response_data)

        except requests.exceptions.RequestException as e:
            logger.error(f"ClickUp API request failed: {e}")
            return jsonify({"error": "Failed to communicate with ClickUp API"}), 500

    except Exception as e:
        logger.error(f"Error escalating to Level 2 for task {task_id}: {e}")
        return jsonify({"error": f"Failed to escalate to Level 2: {str(e)}"}), 500


@app.route('/api/task-helper/respond-to-rfi/<task_id>', methods=['POST'])
@login_required
@rate_limiter.rate_limit(limit='10 per minute')
def respond_to_rfi(task_id):
    """
    Employee responds to RFI (Phase 5: RFI System)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        rfi_response = data.get('response', '').strip()

        if not rfi_response:
            return jsonify({"error": "RFI response is required"}), 400

        # Log RFI response for audit
        logger.info(f"RFI response for task {task_id} by {request.user.get('email')}")

        # Get ClickUp API configuration
        clickup_token = os.getenv('CLICKUP_API_KEY')
        if not clickup_token:
            logger.error("ClickUp API key not configured")
            return jsonify({"error": "ClickUp integration not configured"}), 500

        # Custom field IDs
        escalation_fields = {
            'ESCALATION_RFI_RESPONSE': 'b5c52661-8142-45e0-bec5-14f3c135edbc',
            'ESCALATION_RFI_STATUS': 'f94c0b4b-0c70-4c23-9633-07af2fa6ddc6',
            'ESCALATION_STATUS': '8d784bd0-18e5-4db3-b45e-9a2900262e04'
        }

        try:
            headers = {
                "Authorization": clickup_token,
                "Content-Type": "application/json"
            }

            # Update 3 fields: RFI_RESPONSE, RFI_STATUS=1 (Completed), ESCALATION_STATUS=1 (back to supervisor)
            fields_to_update = [
                (escalation_fields['ESCALATION_RFI_RESPONSE'], {"value": rfi_response}),
                (escalation_fields['ESCALATION_RFI_STATUS'], {"value": 1}),  # orderindex 1 = 'RFI Completed'
                (escalation_fields['ESCALATION_STATUS'], {"value": 1})  # orderindex 1 = 'ESCALATED' (back to supervisor)
            ]

            # Update each field individually
            for field_id, field_data in fields_to_update:
                field_response = requests.post(
                    f"https://api.clickup.com/api/v2/task/{task_id}/field/{field_id}",
                    headers=headers,
                    json=field_data
                )

                if not field_response.ok:
                    logger.error(f"Failed to update field {field_id}: {field_response.text}")
                else:
                    logger.info(f"Successfully updated field {field_id}")

            # Add RFI response comment
            rfi_comment = f"""✅ **RFI RESPONSE SUBMITTED**

**Response**:
{rfi_response}

**Submitted by**: {request.user.get('email')}
**Response Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

----
*Escalation returned to supervisor for review*"""

            comment_response = requests.post(
                f"https://api.clickup.com/api/v2/task/{task_id}/comment",
                headers=headers,
                json={
                    "comment_text": rfi_comment,
                    "notify_all": True
                }
            )

            if not comment_response.ok:
                logger.warning(f"Failed to add RFI response comment: {comment_response.text}")

            # Success response
            response_data = {
                "success": True,
                "message": "RFI response submitted successfully",
                "task_id": task_id,
                "submitted_by": request.user.get('email'),
                "rfi_response": rfi_response,
                "timestamp": datetime.now().isoformat()
            }

            return jsonify(response_data)

        except requests.exceptions.RequestException as e:
            logger.error(f"ClickUp API request failed: {e}")
            return jsonify({"error": "Failed to communicate with ClickUp API"}), 500

    except Exception as e:
        logger.error(f"Error responding to RFI for task {task_id}: {e}")
        return jsonify({"error": f"Failed to submit RFI response: {str(e)}"}), 500


@app.route('/api/task-helper/christian-response/<task_id>', methods=['POST', 'OPTIONS'])
@login_required
@rate_limiter.rate_limit(limit='10 per minute')
def christian_response(task_id):
    """
    Handle Christian's response to a Level 2 escalation

    This endpoint:
    1. Updates ESCALATION_STATUS from ESCALATED to RESOLVED (orderindex 1 → 2)
    2. Writes Christian's response to ESCALATION_RESPONSE_TEXT
    3. Updates ESCALATION_RESOLVED_TIMESTAMP
    4. Adds a comment to the task

    Request body:
    {
        "response": "Christian's response text"
    }

    Returns:
    {
        "success": true,
        "message": "Level 2 escalation resolved successfully",
        "task_id": "...",
        "resolved_at": "..."
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        christian_response_text = data.get('response', '').strip()

        if not christian_response_text:
            return jsonify({"error": "Christian's response is required"}), 400

        # Log Christian's response for audit
        logger.info(f"Christian (L2) response for task {task_id} by {request.user.get('email')}")

        # Get ClickUp API configuration
        clickup_token = os.getenv('CLICKUP_API_KEY')
        if not clickup_token:
            logger.error("ClickUp API key not configured")
            return jsonify({"error": "ClickUp integration not configured"}), 500

        # Custom field IDs
        escalation_fields = {
            'ESCALATION_STATUS': '8d784bd0-18e5-4db3-b45e-9a2900262e04',
            'CHRISTIAN_RESPONSE': 'a077ecc9-1a59-48af-b2cd-42a63f5a7f86',  # ESCALATION_RESPONSE_TEXT
            'ESCALATION_RESOLVED_TIMESTAMP': 'c40bf1c4-7d33-4b2b-8765-0784cd88591a'
        }

        try:
            # Update task custom fields with Christian's response - ONE AT A TIME
            headers = {
                "Authorization": clickup_token,
                "Content-Type": "application/json"
            }

            # Set each field individually using the correct API endpoint
            resolved_timestamp = int(datetime.now().timestamp() * 1000)

            fields_to_update = [
                (escalation_fields['CHRISTIAN_RESPONSE'], {"value": christian_response_text}),
                (escalation_fields['ESCALATION_STATUS'], {"value": 2}),  # orderindex 2 = 'Resolved'
                (escalation_fields['ESCALATION_RESOLVED_TIMESTAMP'], {
                    "value": resolved_timestamp,
                    "value_options": {"time": True}  # Include time for date field
                })
            ]

            # Update each field individually
            for field_id, field_data in fields_to_update:
                field_response = requests.post(
                    f"https://api.clickup.com/api/v2/task/{task_id}/field/{field_id}",
                    headers=headers,
                    json=field_data
                )

                if not field_response.ok:
                    logger.error(f"Failed to update field {field_id}: {field_response.text}")
                    # Continue trying other fields even if one fails
                else:
                    logger.info(f"Successfully updated field {field_id}")

            # All fields attempted, continue with the rest

            # Add resolution comment to task
            resolution_comment = f"""✅ **LEVEL 2 ESCALATION RESOLVED BY CHRISTIAN**

**Response**:
{christian_response_text}

**Resolved by**: {request.user.get('email')}
**Resolution Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

----
*This Level 2 resolution was recorded via Task Helper*"""

            comment_response = requests.post(
                f"https://api.clickup.com/api/v2/task/{task_id}/comment",
                headers={
                    "Authorization": clickup_token,
                    "Content-Type": "application/json"
                },
                json={
                    "comment_text": resolution_comment,
                    "notify_all": True
                }
            )

            if not comment_response.ok:
                logger.error(f"Failed to add resolution comment: {comment_response.text}")
            else:
                logger.info(f"Successfully added L2 resolution comment to task {task_id}")

            return jsonify({
                "success": True,
                "message": "Level 2 escalation resolved successfully by Christian",
                "task_id": task_id,
                "resolved_at": datetime.now().isoformat(),
                "resolved_timestamp": resolved_timestamp
            })

        except requests.exceptions.RequestException as e:
            logger.error(f"ClickUp API error for task {task_id}: {e}")
            return jsonify({"error": "Failed to communicate with ClickUp API"}), 500

    except Exception as e:
        logger.error(f"Error in Christian's L2 response for task {task_id}: {e}")
        return jsonify({"error": f"Failed to submit L2 resolution: {str(e)}"}), 500


@app.route('/api/task-helper/attachments/<task_id>', methods=['GET', 'OPTIONS'])
@login_required
@rate_limiter.rate_limit(limit='20 per minute')
def get_task_attachments(task_id):
    """
    Fetch all attachments for a task by retrieving the full task object

    Note: ClickUp API v2 does not have a dedicated attachment endpoint.
    We fetch the full task object and extract the attachments array.

    This endpoint retrieves all files attached to a ClickUp task,
    including images, PDFs, and other document types.

    Returns:
    {
        "success": true,
        "attachments": [
            {
                "id": "attachment_id",
                "title": "photo.jpg",
                "url": "https://...",
                "thumbnail_small": "https://...",
                "thumbnail_medium": "https://...",
                "date": 1234567890,
                "type": "image/jpeg",
                "size": 102400,
                "user": {
                    "id": 123,
                    "username": "john.doe@example.com",
                    "email": "john.doe@example.com"
                }
            }
        ],
        "count": 1
    }
    """
    try:
        # Log attachment fetch for audit
        logger.info(f"Fetching attachments for task {task_id} by {request.user.get('email')}")

        # Get ClickUp API configuration
        clickup_token = os.getenv('CLICKUP_API_KEY')
        if not clickup_token:
            logger.error("ClickUp API key not configured")
            return jsonify({"error": "ClickUp integration not configured"}), 500

        try:
            # Fetch task object from ClickUp (contains attachments array)
            headers = {
                "Authorization": clickup_token,
                "Content-Type": "application/json"
            }

            response = requests.get(
                f"https://api.clickup.com/api/v2/task/{task_id}",
                headers=headers
            )

            if not response.ok:
                logger.error(f"Failed to fetch task for attachments: {response.status_code} - {response.text}")
                return jsonify({
                    "error": f"Failed to fetch task from ClickUp: {response.status_code}"
                }), response.status_code

            task_data = response.json()

            # Extract attachments array from task object
            attachments = task_data.get('attachments', [])
            processed_attachments = []

            for att in attachments:
                processed_att = {
                    'id': att.get('id'),
                    'title': att.get('title', att.get('name', 'Untitled')),
                    'url': att.get('url'),
                    'date': att.get('date'),
                    'type': att.get('mimetype', att.get('type', 'application/octet-stream')),
                    'size': att.get('size', 0),
                    'user': {
                        'id': att.get('user', {}).get('id'),
                        'username': att.get('user', {}).get('username'),
                        'email': att.get('user', {}).get('email')
                    }
                }

                # Add thumbnail URLs if they exist (for images)
                if 'thumbnail_small' in att:
                    processed_att['thumbnail_small'] = att['thumbnail_small']
                if 'thumbnail_medium' in att:
                    processed_att['thumbnail_medium'] = att['thumbnail_medium']
                if 'thumbnail_large' in att:
                    processed_att['thumbnail_large'] = att['thumbnail_large']

                processed_attachments.append(processed_att)

            logger.info(f"Successfully fetched {len(processed_attachments)} attachments for task {task_id}")

            return jsonify({
                "success": True,
                "attachments": processed_attachments,
                "count": len(processed_attachments)
            })

        except requests.exceptions.RequestException as e:
            logger.error(f"ClickUp API error for task {task_id}: {e}")
            return jsonify({"error": "Failed to communicate with ClickUp API"}), 500

    except Exception as e:
        logger.error(f"Error fetching attachments for task {task_id}: {e}")
        return jsonify({"error": f"Failed to fetch attachments: {str(e)}"}), 500


@app.route('/api/task-helper/upload-attachment/<task_id>', methods=['POST', 'OPTIONS'])
@login_required
@rate_limiter.rate_limit(limit='10 per minute')
def upload_task_attachment(task_id):
    """
    Upload an attachment to a task

    This endpoint accepts a file upload and attaches it to a ClickUp task.

    Request: multipart/form-data with 'file' field

    File Requirements:
    - Max size: 10MB
    - Allowed types: images (jpg, png, gif), PDF, Excel, Word documents

    Returns:
    {
        "success": true,
        "attachment": {
            "id": "attachment_id",
            "title": "document.pdf",
            "url": "https://...",
            "date": 1234567890,
            "type": "application/pdf",
            "size": 102400
        }
    }
    """
    try:
        # Log upload attempt for audit
        logger.info(f"Upload attachment for task {task_id} by {request.user.get('email')}")

        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']

        # Check if filename is empty
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Validate file size (10MB limit)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset file pointer

        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            return jsonify({
                "error": f"File size ({file_size} bytes) exceeds maximum allowed size (10MB)"
            }), 400

        # Validate file type
        allowed_types = {
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
            'application/pdf',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }

        # Get mimetype from file
        file_type = file.content_type
        if file_type not in allowed_types:
            return jsonify({
                "error": f"File type '{file_type}' not supported. Allowed: images, PDF, Excel, Word"
            }), 400

        # Get ClickUp API configuration
        clickup_token = os.getenv('CLICKUP_API_KEY')
        if not clickup_token:
            logger.error("ClickUp API key not configured")
            return jsonify({"error": "ClickUp integration not configured"}), 500

        try:
            # Upload to ClickUp
            headers = {
                "Authorization": clickup_token
            }

            # ClickUp expects the file in 'attachment' field
            files = {
                'attachment': (file.filename, file.stream, file.content_type)
            }

            response = requests.post(
                f"https://api.clickup.com/api/v2/task/{task_id}/attachment",
                headers=headers,
                files=files
            )

            if not response.ok:
                logger.error(f"Failed to upload attachment: {response.status_code} - {response.text}")
                return jsonify({
                    "error": f"Failed to upload to ClickUp: {response.status_code}"
                }), response.status_code

            attachment_data = response.json()

            logger.info(f"Successfully uploaded attachment '{file.filename}' to task {task_id}")

            # Return attachment details
            return jsonify({
                "success": True,
                "attachment": {
                    "id": attachment_data.get('id'),
                    "title": attachment_data.get('title', file.filename),
                    "url": attachment_data.get('url'),
                    "date": attachment_data.get('date'),
                    "type": file_type,
                    "size": file_size
                },
                "message": "File uploaded successfully"
            })

        except requests.exceptions.RequestException as e:
            logger.error(f"ClickUp API error for task {task_id}: {e}")
            return jsonify({"error": "Failed to communicate with ClickUp API"}), 500

    except Exception as e:
        logger.error(f"Error uploading attachment for task {task_id}: {e}")
        return jsonify({"error": f"Failed to upload attachment: {str(e)}"}), 500


# =====================================================
# Secure Page Routes - Server-Side Rendering
# =====================================================

@app.route('/pages/wait-node-v2')
@login_required
@rate_limiter.rate_limit(limit='100 per hour')
def serve_wait_node_v2():
    """
    Serve wait-node-v2 page only to authenticated users
    This ensures the HTML is never sent without authentication
    """
    # Log page access for security audit
    logger.info(f"Secure page access: wait-node-v2 by {request.user.get('email')}")

    # Render the template - query parameters are automatically available in the template
    return render_template('secured/wait-node-v2.html')


@app.route('/pages/escalation-v2')
@login_required
@rate_limiter.rate_limit(limit='100 per hour')
def serve_escalation_v2():
    """
    Serve escalation-v2 page only to authenticated users
    Three-panel layout for escalation workflow management
    """
    # Log page access for security audit
    logger.info(f"Secure page access: escalation-v2 by {request.user.get('email')}")

    # Render the template - query parameters are automatically available in the template
    return render_template('secured/escalation-v2.html')


@app.route('/pages/escalation-v3')
@login_required
@rate_limiter.rate_limit(limit='100 per hour')
def serve_escalation_v3():
    """
    Serve escalation-v3 page (Phase 4: Supervisor Multi-Action UI)
    Five-state system with 3-button supervisor panel:
    - Answer (resolve)
    - Request Info (ask employee for details)
    - Escalate to Level 2 (send to Christian)
    """
    # Log page access for security audit
    logger.info(f"Secure page access: escalation-v3 by {request.user.get('email')}")

    # Render the template - query parameters are automatically available in the template
    return render_template('secured/escalationv3.html')


@app.route('/pages/wait-node-editable')
@login_required
@rate_limiter.rate_limit(limit='100 per hour')
def serve_wait_node_editable():
    """
    Serve wait-node-editable page with edit capabilities
    OAuth protected page for editing Process Library steps
    """
    # Log page access for security audit
    logger.info(f"Secure page access: wait-node-editable by {request.user.get('email')}")
    
    # Render the editable template - query parameters are automatically available
    return render_template('secured/wait-node-editable.html')


@app.route('/pages/task-helper')
@login_required
@rate_limiter.rate_limit(limit='100 per hour')
def serve_task_helper():
    """
    Serve task-helper page for escalation and task management
    OAuth protected page for team task escalation workflow
    """
    # Log page access for security audit
    logger.info(f"Secure page access: task-helper by {request.user.get('email')}")
    
    # Render the task helper template - query parameters are automatically available
    return render_template('secured/task-helper.html')


@app.route('/pages/wait-node')
@login_required
@rate_limiter.rate_limit(limit='100 per hour')
def serve_wait_node():
    """
    Serve wait-node page only to authenticated users
    Legacy version - consider using wait-node-v2
    """
    # Log page access for security audit
    logger.info(f"Secure page access: wait-node by {request.user.get('email')}")
    
    return render_template('secured/wait-node.html')


@app.route('/portal')
@login_required
@rate_limiter.rate_limit(limit='100 per hour')
def portal_home():
    """
    Company Portal home page
    Displays sidebar with all available apps
    """
    # Log portal access
    logger.info(f"Portal accessed by {request.user.get('email')}")

    # Get user role for permission filtering
    user_role = request.user.get('role', 'user')

    # Get sidebar items based on permissions
    portal_apps = portal_registry.get_sidebar_items(user_role)

    # Render portal with first app selected by default
    default_app = portal_apps[0] if portal_apps else None

    return render_template(
        'portal/base.html',
        portal_apps=portal_apps,
        user_email=request.user.get('email'),
        current_app_id=default_app['id'] if default_app else None,
        current_app_name=default_app['name'] if default_app else 'Portal',
        current_app_icon=default_app['icon'] if default_app else 'fas fa-home',
        current_app_description=default_app['description'] if default_app else ''
    )


@app.route('/pages/health')
def pages_health():
    """Health check for secure pages - no auth required"""
    return jsonify({
        'status': 'healthy',
        'pages_available': True,
        'pages': ['wait-node', 'wait-node-v2', 'wait-node-editable', 'task-helper'],
        'portal_enabled': True,
        'portal_apps': portal_registry.get_app_count()
    }), 200


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error"}), 500


@app.route('/api/user/role', methods=['GET'])
@login_required
def get_user_role():
    """Get user role for supervisor detection"""
    try:
        # For now, implement basic supervisor detection
        # This can be enhanced with proper role management later
        # FIXED: Use request.user (set by @login_required) instead of session
        user_email = request.user.get('email', '')
        
        # Simple supervisor detection - can be made more sophisticated
        is_supervisor = any([
            'supervisor' in user_email.lower(),
            'manager' in user_email.lower(),
            'admin' in user_email.lower(),
            # Add more supervisor email patterns as needed
            user_email.endswith('@supervisors.company.com'),  # Example domain
        ])
        
        logger.info(f"User role check - Email: {user_email}, Is supervisor: {is_supervisor}")
        
        return jsonify({
            'role': 'supervisor' if is_supervisor else 'user',
            'user_email': user_email,
            'is_supervisor': is_supervisor
        })
        
    except Exception as e:
        logger.error(f"Error checking user role: {e}")
        return jsonify({'error': 'Failed to check user role'}), 500


if __name__ == '__main__':
    # Check for required environment variables
    required_vars = [
        'CLICKUP_API_KEY',
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET',
        'SESSION_SECRET'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print("ERROR: Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these in your .env file or Render environment")
        exit(1)
    
    # Production check
    if os.environ.get('FLASK_ENV') == 'production':
        print("Running in PRODUCTION mode")
        print("Use a production WSGI server like Gunicorn")
        print("Example: gunicorn -w 4 -b 0.0.0.0:10000 app_secure:app")
    else:
        print(f"Starting secure Flask server...")
        print(f"Team ID: {CLICKUP_TEAM_ID}")
        print(f"Server running at: http://localhost:5678")
        print(f"Health check: http://localhost:5678/health")
        print(f"OAuth login: http://localhost:5678/auth/login")
        
        app.run(host='0.0.0.0', port=5678, debug=False)  # Never use debug=True in production