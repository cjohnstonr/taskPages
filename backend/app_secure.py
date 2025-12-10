"""
Secure Flask backend server with Google OAuth authentication
Handles ClickUp API interactions with authentication and security
"""

import os
import sys
import logging
import json
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

# Import security modules
from config.security import SecureConfig
from auth.oauth_handler import auth_bp, init_redis, login_required, login_required_with_local_dev
from auth.security_middleware import SecurityMiddleware, RateLimiter

# Configure logging FIRST (before using logger)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
# Load from Local/api-keys/.env if it exists, otherwise use default .env
env_path = Path(__file__).parent.parent.parent / 'Local' / 'api-keys' / '.env'
if env_path.exists():
    load_dotenv(env_path)
    logger.info(f"Loaded environment from {env_path}")
else:
    load_dotenv()
    logger.info("Loaded environment from default .env")

# Import portal modules
from portal import PortalRegistry
from portal.apps.kpi_dashboard import KPIDashboardApp

# Note: OpenAI removed - using n8n for AI analysis instead

# Initialize Flask app with security config
app = Flask(__name__)
SecureConfig.init_app(app)

# Initialize Redis for sessions
if os.environ.get('DISABLE_REDIS', 'false').lower() == 'true':
    logger.warning("Redis disabled by environment variable - using Flask built-in sessions")
    redis_client = None
    # Don't use Flask-Session in local dev - use Flask's built-in cookie sessions
    # This avoids the bytes/string session ID issue
else:
    try:
        redis_client = init_redis(app)
        app.config['SESSION_REDIS'] = redis_client
        Session(app)
        logger.info("Redis session management initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        logger.warning("Falling back to Flask built-in sessions")
        redis_client = None
        # Don't use Flask-Session when Redis fails - use Flask's built-in cookie sessions

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
                timeout=120  # 120 second timeout
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
            logger.error(f"n8n webhook timed out after 120 seconds for task {task_id}")
            return jsonify({
                'success': False,
                'error': 'n8n timeout after 120 seconds. Please try again.'
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


@app.route('/api/task-helper/reopen-escalation/<task_id>', methods=['POST'])
@login_required
@rate_limiter.rate_limit(limit='10 per minute')
def reopen_escalation(task_id):
    """
    Reopen a resolved escalation by changing status back to "Not Escalated"
    Allows users to resubmit escalations if needed
    """
    try:
        # Log reopen action for audit
        logger.info(f"Reopening escalation for task {task_id} by {request.user.get('email')}")

        # Get ClickUp API configuration
        clickup_token = os.getenv('CLICKUP_API_KEY')
        if not clickup_token:
            logger.error("ClickUp API key not configured")
            return jsonify({"error": "ClickUp integration not configured"}), 500

        # Custom field ID for escalation status
        escalation_status_field_id = '8d784bd0-18e5-4db3-b45e-9a2900262e04'

        try:
            # Update escalation status to "Not Escalated" (orderindex 0)
            headers = {
                "Authorization": clickup_token,
                "Content-Type": "application/json"
            }

            field_response = requests.post(
                f"https://api.clickup.com/api/v2/task/{task_id}/field/{escalation_status_field_id}",
                headers=headers,
                json={"value": 0}  # orderindex 0 = 'Not Escalated'
            )

            if not field_response.ok:
                logger.error(f"Failed to update escalation status: {field_response.text}")
                return jsonify({"error": "Failed to update escalation status in ClickUp"}), 500

            logger.info(f"Successfully reopened escalation for task {task_id}")

            # Add comment to task for audit trail
            reopen_comment = f"""🔄 **ESCALATION REOPENED**

**Status changed to**: Not Escalated
**Reopened by**: {request.user.get('email')}
**Reopen Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

This escalation can now be resubmitted if needed.

----
*This action was recorded via Task Helper*"""

            comment_response = requests.post(
                f"https://api.clickup.com/api/v2/task/{task_id}/comment",
                headers={
                    "Authorization": clickup_token,
                    "Content-Type": "application/json"
                },
                json={
                    "comment_text": reopen_comment,
                    "notify_all": False
                }
            )

            if not comment_response.ok:
                logger.warning(f"Failed to add reopen comment: {comment_response.text}")

            # Success response
            response_data = {
                "success": True,
                "message": "Escalation reopened successfully",
                "task_id": task_id,
                "reopened_by": request.user.get('email'),
                "new_status": "Not Escalated",
                "timestamp": datetime.now().isoformat()
            }

            return jsonify(response_data)

        except requests.exceptions.RequestException as e:
            logger.error(f"ClickUp API request failed: {e}")
            return jsonify({"error": "Failed to communicate with ClickUp API"}), 500

    except Exception as e:
        logger.error(f"Error reopening escalation for task {task_id}: {e}")
        return jsonify({"error": f"Failed to reopen escalation: {str(e)}"}), 500


@app.route('/api/task-helper/escalations', methods=['GET'])
@login_required
@rate_limiter.rate_limit(limit='30 per minute')
def get_escalations():
    """
    Get filtered list of escalated tasks for the escalation dashboard.
    Query params: status, level, limit, offset

    Returns all tasks with the 'escalated' tag, filtered by status and level.
    """
    try:
        # Get query params
        status_filter = request.args.get('status', 'active')  # active|resolved|all
        level_filter = request.args.get('level', 'all')  # 0|1|all
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        # Get ClickUp API configuration
        clickup_token = os.getenv('CLICKUP_API_KEY')
        if not clickup_token:
            logger.error("ClickUp API key not configured")
            return jsonify({"error": "ClickUp integration not configured"}), 500

        # Custom field IDs from the plan document
        FIELD_IDS = {
            'ESCALATION_STATUS': '8d784bd0-18e5-4db3-b45e-9a2900262e04',
            'ESCLATION_LEVEL': '90d2fec8-7474-4221-84c0-b8c7fb5e4385',  # Note: typo is in ClickUp
            'ESCALATION_REASON_TEXT': 'c6e0281e-9001-42d7-a265-8f5da6b71132',
            'ESCALATION_SUBMITTED_DATE_TIME': '5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f',
            'ESCALATION_RESOLVED_DATE_TIME': 'c40bf1c4-7d33-4b2b-8765-0784cd88591a'
        }

        # Query ClickUp API for all tasks with 'escalated' tag
        headers = {
            'Authorization': clickup_token,
            'Content-Type': 'application/json'
        }

        workspace_id = CLICKUP_TEAM_ID
        url = f'https://api.clickup.com/api/v2/team/{workspace_id}/task'
        params = {
            'tags[]': 'escalated',
            'include_closed': 'true',
            'subtasks': 'true'
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        tasks = response.json().get('tasks', [])

        logger.info(f"Retrieved {len(tasks)} tasks with 'escalated' tag")

        # Helper function to extract custom field values
        def get_custom_field(task, field_id):
            """Extract custom field value, handling dropdowns as integers."""
            field = next((f for f in task.get('custom_fields', [])
                          if f['id'] == field_id), None)

            if not field or field.get('value') is None:
                return None

            # Dropdown fields return integers
            if field.get('type') == 'drop_down':
                try:
                    return int(field['value'])
                except (ValueError, TypeError):
                    return None

            # Date fields return strings that need parseInt
            if field.get('type') == 'date':
                try:
                    return int(field['value'])
                except (ValueError, TypeError):
                    return None

            # Text fields
            return field['value']

        # Transform and filter tasks
        escalations = []
        for task in tasks:
            # Parse custom fields
            status = get_custom_field(task, FIELD_IDS['ESCALATION_STATUS'])
            level = get_custom_field(task, FIELD_IDS['ESCLATION_LEVEL'])

            # Skip "Not Escalated" (status = 0) - these shouldn't have the tag but filter anyway
            if status == 0:
                continue

            # Apply status filter
            if status_filter == 'active' and status != 1:
                continue
            if status_filter == 'resolved' and status != 2:
                continue

            # Apply level filter
            if level_filter != 'all':
                try:
                    level_filter_int = int(level_filter)
                    # Normalize level: treat None as 0 (Shirley/Level 1)
                    # This matches the transformation logic and ensures tasks without
                    # Esclation_Level field set are treated as Level 1 (Shirley)
                    normalized_level = level if level is not None else 0
                    if normalized_level != level_filter_int:
                        continue
                except (ValueError, TypeError):
                    pass

            # Extract timestamps
            submitted_time = get_custom_field(task, FIELD_IDS['ESCALATION_SUBMITTED_DATE_TIME'])
            resolved_time = get_custom_field(task, FIELD_IDS['ESCALATION_RESOLVED_DATE_TIME'])

            # Transform to simplified structure
            escalation = {
                'id': task['id'],
                'custom_id': task.get('custom_id'),
                'name': task['name'],
                'status': status if status is not None else 0,
                'level': level if level is not None else 0,
                'escalation_reason': get_custom_field(task, FIELD_IDS['ESCALATION_REASON_TEXT']),
                'submitted_time': submitted_time,
                'resolved_time': resolved_time,
                'due_date': task.get('due_date'),
                'priority': task.get('priority', {}).get('id') if isinstance(task.get('priority'), dict) else None,
                'url': f"/pages/escalation-v3?task_id={task.get('custom_id') or task['id']}",
                'clickup_url': task.get('url')
            }

            escalations.append(escalation)

        # Calculate stats
        stats = {
            'active': len([e for e in escalations if e['status'] == 1]),
            'resolved': len([e for e in escalations if e['status'] == 2]),
            'level_1': len([e for e in escalations if e['level'] == 0]),
            'level_2': len([e for e in escalations if e['level'] == 1])
        }

        # Sort by submitted time (most recent first)
        escalations.sort(key=lambda e: e['submitted_time'] or 0, reverse=True)

        # Apply pagination
        total = len(escalations)
        escalations_page = escalations[offset:offset + limit]

        logger.info(f"Returning {len(escalations_page)} escalations (filtered from {total} total)")

        return jsonify({
            'success': True,
            'escalations': escalations_page,
            'total': total,
            'filtered': len(escalations_page),
            'stats': stats
        })

    except requests.exceptions.RequestException as e:
        logger.error(f"ClickUp API request failed: {e}")
        return jsonify({'error': 'Failed to communicate with ClickUp API'}), 500
    except Exception as e:
        logger.error(f"Error fetching escalations: {e}")
        return jsonify({'error': str(e)}), 500


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
# Field Operations Planning API Endpoints
# =====================================================

# Field IDs for Field Operations Planning
PROPERTY_LINK_FIELD_ID = '73999194-0433-433d-a27c-4d9c5f194fd0'
FIELD_OPS_LIST_ID = '901108930624'
SITE_VISITS_LIST_ID = '901112157682'

FIELD_OP_CUSTOM_FIELDS = {
    'linked_site_visit': 'a033b07e-355c-4532-bb15-a2f6ef8a3012',
    'visit_date': '4d241509-33bd-4be2-b3f1-c16ca224b733',
    'approval_status': 'bd6583ec-7c17-4440-9985-6bb413e040e9',
    'vendor': '6a29a9a7-cbc2-48e1-ab21-56ea70aa6ea1'
}

SITE_VISIT_CUSTOM_FIELDS = {
    'linked_field_operations': '662848b9-9681-4148-b418-28eb9cba46e7',
    'site_visit_date': '43694837-8454-444c-980f-a50590b6e483',  # CORRECTED
    'vendor': '17ce2a15-c8f9-4694-9c40-28ab5ef56284'  # CORRECTED
}


# ============================================================================
# TEST ADMINISTRATION ENDPOINTS
# ============================================================================

def parse_mc_options(question_text: str) -> List[Dict[str, str]]:
    """
    Parse multiple choice options from question text.

    Expected format:
    "Question text here? A. First option B. Second option C. Third option D. Fourth option"

    Returns:
    [
        {"letter": "A", "text": "First option"},
        {"letter": "B", "text": "Second option"},
        {"letter": "C", "text": "Third option"},
        {"letter": "D", "text": "Fourth option"}
    ]
    """
    import re

    options = []

    # Split on pattern like " A. " or " B. "
    # Use lookahead to split before the letter
    parts = re.split(r'\s+(?=[A-D]\.)', question_text)

    for part in parts:
        # Match pattern: "A. Option text"
        match = re.match(r'^([A-D])\.\s+(.+)', part.strip(), re.DOTALL)
        if match:
            options.append({
                'letter': match.group(1),
                'text': match.group(2).strip()
            })

    return options


@app.route('/api/test/initialize/<task_id>', methods=['GET'])
@login_required
@rate_limiter.rate_limit(limit='30 per minute')
def initialize_test(task_id):
    """
    Initialize test page with test data and all questions

    Returns:
    {
        "test_task": {task object},
        "questions": [
            {
                "id": "subtask_id",
                "name": "Q1",
                "order": 1,
                "question_type": 0,  // order index (0=MC, 1=SA)
                "question_text": "Full question text",
                "options": [{"letter": "A", "text": "..."}, ...],  // MC only
                "user_input": "previous answer or null"
            },
            ...
        ],
        "user_email": "user@example.com",
        "test_metadata": {
            "total_questions": 10,
            "completed_questions": 3,
            "test_name": "Task name"
        }
    }
    """
    try:
        logger.info(f"Initializing test for task: {task_id} by user: {request.user.get('email')}")

        # Fetch parent task with custom fields for time tracking
        test_task = clickup_service.get_task(task_id, custom_task_ids=True, include_subtasks=True)

        # Time tracking custom field IDs (on parent task)
        START_TIME_FIELD_ID = 'a2783917-49a9-453a-9d4b-fe9d43ecd055'
        END_TIME_FIELD_ID = '2ebae004-8f25-46b6-83c2-96007b339e1f'

        # Extract start/end times from parent task custom fields
        parent_custom_fields = {
            cf['id']: cf.get('value') for cf in test_task.get('custom_fields', [])
        }
        start_time_ms = parent_custom_fields.get(START_TIME_FIELD_ID)
        end_time_ms = parent_custom_fields.get(END_TIME_FIELD_ID)

        # Convert Unix timestamps to ISO strings for frontend
        from datetime import datetime
        start_time = None
        end_time = None
        if start_time_ms:
            start_time = datetime.fromtimestamp(int(start_time_ms) / 1000).isoformat(timespec='milliseconds') + 'Z'
        if end_time_ms:
            end_time = datetime.fromtimestamp(int(end_time_ms) / 1000).isoformat(timespec='milliseconds') + 'Z'

        # Fetch all subtasks with custom fields
        subtasks = clickup_service.fetch_subtasks_with_details(task_id)

        if not subtasks:
            return jsonify({
                "error": "No questions found for this test",
                "test_task": test_task
            }), 404

        # Parse and structure questions
        questions = []
        for idx, subtask in enumerate(subtasks, 1):
            # Extract custom fields
            custom_fields_dict = {
                cf['id']: cf.get('value') for cf in subtask.get('custom_fields', [])
            }

            # Test custom field IDs
            FIELD_IDS_TEST = {
                'QUESTION_TYPE': '6ecb4043-f8f7-46d2-8825-33d73bb1d1d0',
                'QUESTION_TEXT': '9a2cf78e-4c75-49f4-ac5e-cff324691c09',
                'QUESTION_ANSWER': 'f381c7bc-4677-4b3d-945d-a71d37d279e2',
                'ANSWER_RATIONALE': '39618fa8-0e13-4669-b9c8-f9a1f1fd55b7',
                'USER_INPUT': '1542be38-e716-4ae2-9513-25b5aa0c076a'
            }

            question_type = custom_fields_dict.get(FIELD_IDS_TEST['QUESTION_TYPE'])  # Returns 0 or 1
            question_text = custom_fields_dict.get(FIELD_IDS_TEST['QUESTION_TEXT'], '')
            user_input = custom_fields_dict.get(FIELD_IDS_TEST['USER_INPUT'], '')

            # Parse MC options if question_type == 0
            options = []
            if question_type == 0:  # Multiple Choice
                options = parse_mc_options(question_text)

            question_obj = {
                "id": subtask['id'],
                "name": subtask['name'],  # "Q1", "Q2", etc.
                "order": idx,
                "question_type": question_type,
                "question_text": question_text,
                "options": options,  # Empty for SA, populated for MC
                "user_input": user_input
            }

            questions.append(question_obj)

        # Sort by question number (parse from name: Q1, Q2, etc.)
        def get_question_number(q):
            try:
                # Extract number from "Q1", "Q2", etc.
                return int(q['name'][1:]) if q['name'][1:].isdigit() else 999
            except:
                return 999

        questions.sort(key=get_question_number)

        logger.info(f"Successfully initialized test {task_id} with {len(questions)} questions")

        return jsonify({
            "test_task": test_task,
            "questions": questions,
            "user_email": request.user.get('email'),
            "test_metadata": {
                "total_questions": len(questions),
                "completed_questions": sum(1 for q in questions if q['user_input']),
                "test_name": test_task.get('name', 'Test')
            },
            "time_tracking": {
                "start_time": start_time,  # ISO datetime string or null
                "end_time": end_time,      # ISO datetime string or null
                "time_limit_minutes": 60,  # 1 hour time limit
                "start_time_field_id": START_TIME_FIELD_ID,
                "end_time_field_id": END_TIME_FIELD_ID
            }
        })

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return jsonify({"error": "Test not found"}), 404
        logger.error(f"ClickUp API error: {e}")
        return jsonify({"error": "Failed to load test from ClickUp"}), 500
    except Exception as e:
        logger.error(f"Error initializing test {task_id}: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route('/api/test/submit-answer/<question_id>', methods=['POST'])
@login_required
@rate_limiter.rate_limit(limit='60 per minute')
def submit_answer(question_id):
    """
    Submit user's answer to a question

    Request Body:
    {
        "user_input": "A" (for multiple choice) or "text answer" (for short answer)
    }

    Returns:
    {
        "success": true,
        "question_id": "question_id",
        "answer_saved": true
    }
    """
    try:
        data = request.get_json()
        user_input = data.get('user_input', '').strip()

        if not user_input:
            return jsonify({"error": "Answer cannot be empty"}), 400

        logger.info(f"Submitting answer for question {question_id} by user {request.user.get('email')}")

        # Update ClickUp custom field
        USER_INPUT_FIELD_ID = '1542be38-e716-4ae2-9513-25b5aa0c076a'
        clickup_service.update_custom_field(question_id, USER_INPUT_FIELD_ID, user_input)

        logger.info(f"Successfully saved answer for question {question_id}")

        return jsonify({
            "success": True,
            "question_id": question_id,
            "answer_saved": True
        })

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return jsonify({"error": "Question not found"}), 404
        logger.error(f"ClickUp API error submitting answer: {e}")
        return jsonify({"error": "Failed to save answer to ClickUp"}), 500
    except Exception as e:
        logger.error(f"Error submitting answer for question {question_id}: {e}")
        return jsonify({"error": f"Failed to save answer: {str(e)}"}), 500


@app.route('/api/test/start/<task_id>', methods=['POST'])
@login_required
@rate_limiter.rate_limit(limit='10 per minute')
def start_test(task_id):
    """
    Record start time for a test in parent task custom field

    Returns:
    {
        "success": true,
        "start_time": "2025-12-09T22:30:00.000Z",
        "task_id": "868gne5g9"
    }
    """
    try:
        from datetime import datetime

        logger.info(f"Starting test {task_id} for user {request.user.get('email')}")

        # Generate Unix timestamp in milliseconds (ClickUp date field format)
        start_time = int(datetime.utcnow().timestamp() * 1000)

        # Update parent task custom field
        START_TIME_FIELD_ID = 'a2783917-49a9-453a-9d4b-fe9d43ecd055'
        clickup_service.update_custom_field(task_id, START_TIME_FIELD_ID, start_time)

        logger.info(f"Test {task_id} started at {start_time}")

        return jsonify({
            "success": True,
            "start_time": start_time,
            "task_id": task_id
        })

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return jsonify({"error": "Test not found"}), 404
        logger.error(f"ClickUp API error recording start time: {e}")
        return jsonify({"error": "Failed to record start time"}), 500
    except Exception as e:
        logger.error(f"Error starting test {task_id}: {e}")
        return jsonify({"error": f"Failed to start test: {str(e)}"}), 500


@app.route('/api/test/end/<task_id>', methods=['POST'])
@login_required
@rate_limiter.rate_limit(limit='10 per minute')
def end_test(task_id):
    """
    Record end time for a test in parent task custom field

    Returns:
    {
        "success": true,
        "end_time": "2025-12-09T23:30:00.000Z",
        "task_id": "868gne5g9",
        "duration_minutes": 60.5
    }
    """
    try:
        from datetime import datetime

        logger.info(f"Ending test {task_id} for user {request.user.get('email')}")

        # Generate Unix timestamp in milliseconds (ClickUp date field format)
        end_time = int(datetime.utcnow().timestamp() * 1000)

        # Update parent task custom field
        END_TIME_FIELD_ID = '2ebae004-8f25-46b6-83c2-96007b339e1f'
        clickup_service.update_custom_field(task_id, END_TIME_FIELD_ID, end_time)

        # Optionally calculate duration if start time exists
        duration_minutes = None
        try:
            # Fetch start time from task
            test_task = clickup_service.get_task(task_id, custom_task_ids=True)
            parent_custom_fields = {
                cf['id']: cf.get('value') for cf in test_task.get('custom_fields', [])
            }
            START_TIME_FIELD_ID = 'a2783917-49a9-453a-9d4b-fe9d43ecd055'
            start_time_ms = parent_custom_fields.get(START_TIME_FIELD_ID)

            if start_time_ms:
                # Both timestamps are Unix milliseconds
                duration_minutes = (end_time - int(start_time_ms)) / 1000 / 60
        except Exception as e:
            logger.warning(f"Could not calculate duration: {e}")

        logger.info(f"Test {task_id} ended at {end_time}")

        return jsonify({
            "success": True,
            "end_time": end_time,
            "task_id": task_id,
            "duration_minutes": duration_minutes
        })

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return jsonify({"error": "Test not found"}), 404
        logger.error(f"ClickUp API error recording end time: {e}")
        return jsonify({"error": "Failed to record end time"}), 500
    except Exception as e:
        logger.error(f"Error ending test {task_id}: {e}")
        return jsonify({"error": f"Failed to end test: {str(e)}"}), 500


@app.route('/api/property/<property_id>/field-operations/unplanned', methods=['GET'])
@login_required
@rate_limiter.rate_limit(limit='300 per hour')
def get_unplanned_field_operations(property_id):
    """
    Get all field operations for a property that are NOT linked to any site visit.

    Filtering logic:
    1. Filter field operations by property_link = property_id
    2. Filter where linked_site_visit is empty/null
    3. Return minimal data for left panel (ID, name, vendor, dates)
    """
    try:
        clickup_service = ClickUpService()

        # Fetch all field operations for this property
        # CRITICAL: Use ANY operator with array value + include_timl=true
        import json
        custom_fields_filter = [{
            "field_id": PROPERTY_LINK_FIELD_ID,
            "operator": "ANY",
            "value": [property_id]
        }]

        url = f"{CLICKUP_BASE_URL}/list/{FIELD_OPS_LIST_ID}/task"
        params = {
            "custom_fields": json.dumps(custom_fields_filter),
            "include_timl": True  # REQUIRED for Field Operations
        }

        response = requests.get(url, headers=clickup_service.headers, params=params, timeout=15)

        if response.status_code != 200:
            logger.error(f"Failed to get field operations: {response.text}")
            return jsonify({"error": "Failed to fetch field operations"}), response.status_code

        all_field_ops = response.json().get('tasks', [])

        # Filter for unplanned (no linked_site_visit)
        unplanned = []
        for task in all_field_ops:
            linked_site_visit = None
            vendor = None
            visit_date = None

            for field in task.get('custom_fields', []):
                if field['id'] == FIELD_OP_CUSTOM_FIELDS['linked_site_visit']:
                    value = field.get('value')
                    linked_site_visit = value if value else None
                elif field['id'] == FIELD_OP_CUSTOM_FIELDS['vendor']:
                    value = field.get('value', [])
                    vendor = value[0] if value else None
                elif field['id'] == FIELD_OP_CUSTOM_FIELDS['visit_date']:
                    visit_date = field.get('value')

            # Only include if NOT linked to a site visit
            if not linked_site_visit or (isinstance(linked_site_visit, list) and len(linked_site_visit) == 0):
                unplanned.append({
                    'id': task['id'],
                    'name': task['name'],
                    'custom_item_id': task.get('custom_item_id'),
                    'status': task['status']['status'],
                    'vendor': vendor,
                    'visit_date': visit_date,
                    'url': task.get('url')
                })

        logger.info(f"Found {len(unplanned)} unplanned field operations for property {property_id}")

        return jsonify({
            "success": True,
            "property_id": property_id,
            "unplanned_field_operations": unplanned,
            "count": len(unplanned)
        })

    except Exception as e:
        logger.error(f"Error fetching unplanned field operations: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch unplanned field operations",
            "details": str(e)
        }), 500


@app.route('/api/property/<property_id>/site-visits', methods=['GET'])
@login_required
@rate_limiter.rate_limit(limit='300 per hour')
def get_property_site_visits(property_id):
    """
    Get all site visits for a property with their linked field operations.

    Returns data formatted for calendar display.
    """
    try:
        clickup_service = ClickUpService()

        # Fetch all site visits for this property
        import json
        custom_fields_filter = [{
            "field_id": PROPERTY_LINK_FIELD_ID,
            "operator": "ANY",
            "value": [property_id]
        }]

        url = f"{CLICKUP_BASE_URL}/list/{SITE_VISITS_LIST_ID}/task"
        params = {
            "custom_fields": json.dumps(custom_fields_filter)
        }

        response = requests.get(url, headers=clickup_service.headers, params=params, timeout=15)

        if response.status_code != 200:
            logger.error(f"Failed to get site visits: {response.text}")
            return jsonify({"error": "Failed to fetch site visits"}), response.status_code

        site_visits_raw = response.json().get('tasks', [])

        # Format for calendar
        site_visits = []
        for task in site_visits_raw:
            linked_field_ops = []
            site_visit_date = None
            vendor = None

            for field in task.get('custom_fields', []):
                if field['id'] == SITE_VISIT_CUSTOM_FIELDS['linked_field_operations']:
                    value = field.get('value', [])
                    linked_field_ops = value if value else []
                elif field['id'] == SITE_VISIT_CUSTOM_FIELDS['site_visit_date']:
                    site_visit_date = field.get('value')
                elif field['id'] == SITE_VISIT_CUSTOM_FIELDS['vendor']:
                    value = field.get('value', [])
                    vendor = value[0] if value else None

            site_visits.append({
                'id': task['id'],
                'name': task['name'],
                'custom_item_id': task.get('custom_item_id'),
                'status': task['status']['status'],
                'site_visit_date': site_visit_date,
                'vendor': vendor,
                'linked_field_operations': linked_field_ops,
                'linked_field_operations_count': len(linked_field_ops) if linked_field_ops else 0,
                'url': task.get('url')
            })

        logger.info(f"Found {len(site_visits)} site visits for property {property_id}")

        return jsonify({
            "success": True,
            "property_id": property_id,
            "site_visits": site_visits,
            "count": len(site_visits)
        })

    except Exception as e:
        logger.error(f"Error fetching site visits: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch site visits",
            "details": str(e)
        }), 500


@app.route('/api/property/<property_id>/site-visit/link-field-op', methods=['POST'])
@login_required
@rate_limiter.rate_limit(limit='200 per hour')
def link_field_op_to_site_visit(property_id):
    """
    Link a field operation to a site visit (create or add to existing).

    Implements bidirectional sync:
    1. Update field_op.linked_site_visit
    2. Update site_visit.linked_field_operations
    3. Sync date and vendor from site visit to field op

    Request body:
    {
        "field_op_id": "868abc123",
        "site_visit_id": "868xyz789",  // Optional: if null, create new site visit
        "site_visit_date": 1730937600000,  // Required if creating new
        "vendor_id": "868vendor"  // Required if creating new
    }
    """
    try:
        data = request.get_json()
        field_op_id = data.get('field_op_id')
        site_visit_id = data.get('site_visit_id')
        site_visit_date = data.get('site_visit_date')
        vendor_id = data.get('vendor_id')

        if not field_op_id:
            return jsonify({"success": False, "error": "field_op_id is required"}), 400

        clickup_service = ClickUpService()

        # If no site visit ID provided, create new site visit
        if not site_visit_id:
            if not site_visit_date or not vendor_id:
                return jsonify({
                    "success": False,
                    "error": "site_visit_date and vendor_id required when creating new site visit"
                }), 400

            # Create new site visit
            create_url = f"{CLICKUP_BASE_URL}/list/{SITE_VISITS_LIST_ID}/task"
            create_payload = {
                "name": f"Site Visit - {datetime.fromtimestamp(site_visit_date/1000).strftime('%B %d, %Y')}",
                "custom_fields": [
                    {
                        "id": PROPERTY_LINK_FIELD_ID,  # ADD property_link
                        "value": [property_id]
                    },
                    {
                        "id": SITE_VISIT_CUSTOM_FIELDS['site_visit_date'],
                        "value": site_visit_date
                    },
                    {
                        "id": SITE_VISIT_CUSTOM_FIELDS['vendor'],
                        "value": [vendor_id]
                    },
                    {
                        "id": SITE_VISIT_CUSTOM_FIELDS['linked_field_operations'],
                        "value": [field_op_id]
                    }
                ]
            }

            create_response = requests.post(create_url, headers=clickup_service.headers,
                                          json=create_payload, timeout=15)

            if create_response.status_code not in [200, 201]:
                logger.error(f"Failed to create site visit: {create_response.text}")
                return jsonify({"error": "Failed to create site visit"}), create_response.status_code

            site_visit_id = create_response.json()['id']
            logger.info(f"Created new site visit {site_visit_id} for property {property_id}")

        else:
            # Add to existing site visit
            # First, get current linked field ops
            site_visit_task = clickup_service.get_task(site_visit_id)
            current_linked_ops = []

            for field in site_visit_task.get('custom_fields', []):
                if field['id'] == SITE_VISIT_CUSTOM_FIELDS['linked_field_operations']:
                    value = field.get('value', [])
                    current_linked_ops = [op['id'] if isinstance(op, dict) else op for op in value]
                    break
                elif field['id'] == SITE_VISIT_CUSTOM_FIELDS['site_visit_date']:
                    site_visit_date = field.get('value')
                elif field['id'] == SITE_VISIT_CUSTOM_FIELDS['vendor']:
                    value = field.get('value', [])
                    vendor_id = value[0]['id'] if (value and isinstance(value[0], dict)) else (value[0] if value else None)

            # Add new field op ID if not already linked
            if field_op_id not in current_linked_ops:
                current_linked_ops.append(field_op_id)

            # Update site visit with new linked field ops array
            update_url = f"{CLICKUP_BASE_URL}/task/{site_visit_id}"
            update_payload = {
                "custom_fields": [
                    {
                        "id": SITE_VISIT_CUSTOM_FIELDS['linked_field_operations'],
                        "value": current_linked_ops
                    }
                ]
            }

            update_response = requests.put(update_url, headers=clickup_service.headers,
                                          json=update_payload, timeout=15)

            if update_response.status_code != 200:
                logger.error(f"Failed to update site visit: {update_response.text}")
                return jsonify({"error": "Failed to update site visit"}), update_response.status_code

        # Update field operation: linked_site_visit + sync date and vendor
        field_op_update_url = f"{CLICKUP_BASE_URL}/task/{field_op_id}"
        field_op_payload = {
            "custom_fields": [
                {
                    "id": FIELD_OP_CUSTOM_FIELDS['linked_site_visit'],
                    "value": [site_visit_id]
                },
                {
                    "id": FIELD_OP_CUSTOM_FIELDS['visit_date'],
                    "value": site_visit_date
                },
                {
                    "id": FIELD_OP_CUSTOM_FIELDS['vendor'],
                    "value": [vendor_id] if vendor_id else None
                }
            ]
        }

        field_op_response = requests.put(field_op_update_url, headers=clickup_service.headers,
                                        json=field_op_payload, timeout=15)

        if field_op_response.status_code != 200:
            logger.error(f"Failed to update field operation: {field_op_response.text}")
            return jsonify({"error": "Failed to update field operation"}), field_op_response.status_code

        logger.info(f"Linked field op {field_op_id} to site visit {site_visit_id}")

        return jsonify({
            "success": True,
            "field_op_id": field_op_id,
            "site_visit_id": site_visit_id,
            "action": "created" if not data.get('site_visit_id') else "linked"
        })

    except Exception as e:
        logger.error(f"Error linking field operation to site visit: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to link field operation",
            "details": str(e)
        }), 500


@app.route('/api/property/<property_id>/site-visit/unlink-field-op', methods=['POST'])
@login_required
@rate_limiter.rate_limit(limit='200 per hour')
def unlink_field_op_from_site_visit(property_id):
    """
    Unlink a field operation from a site visit.

    Implements bidirectional sync + auto-delete:
    1. Remove field_op_id from site_visit.linked_field_operations
    2. Clear field_op.linked_site_visit
    3. If site visit has no remaining field ops, DELETE the site visit

    Request body:
    {
        "field_op_id": "868abc123",
        "site_visit_id": "868xyz789"
    }
    """
    try:
        data = request.get_json()
        field_op_id = data.get('field_op_id')
        site_visit_id = data.get('site_visit_id')

        if not field_op_id or not site_visit_id:
            return jsonify({"success": False, "error": "field_op_id and site_visit_id required"}), 400

        clickup_service = ClickUpService()

        # Get current site visit
        site_visit_task = clickup_service.get_task(site_visit_id)
        current_linked_ops = []

        for field in site_visit_task.get('custom_fields', []):
            if field['id'] == SITE_VISIT_CUSTOM_FIELDS['linked_field_operations']:
                value = field.get('value', [])
                current_linked_ops = [op['id'] if isinstance(op, dict) else op for op in value]
                break

        # Remove field op from list
        if field_op_id in current_linked_ops:
            current_linked_ops.remove(field_op_id)

        # If no remaining field ops, DELETE site visit
        if len(current_linked_ops) == 0:
            delete_url = f"{CLICKUP_BASE_URL}/task/{site_visit_id}"
            delete_response = requests.delete(delete_url, headers=clickup_service.headers, timeout=15)

            if delete_response.status_code not in [200, 204]:
                logger.error(f"Failed to delete empty site visit: {delete_response.text}")
                return jsonify({"error": "Failed to delete empty site visit"}), delete_response.status_code

            logger.info(f"Deleted empty site visit {site_visit_id}")
            action = "site_visit_deleted"

        else:
            # Update site visit with remaining field ops
            update_url = f"{CLICKUP_BASE_URL}/task/{site_visit_id}"
            update_payload = {
                "custom_fields": [
                    {
                        "id": SITE_VISIT_CUSTOM_FIELDS['linked_field_operations'],
                        "value": current_linked_ops
                    }
                ]
            }

            update_response = requests.put(update_url, headers=clickup_service.headers,
                                          json=update_payload, timeout=15)

            if update_response.status_code != 200:
                logger.error(f"Failed to update site visit: {update_response.text}")
                return jsonify({"error": "Failed to update site visit"}), update_response.status_code

            action = "unlinked"

        # Clear field operation's linked_site_visit
        field_op_update_url = f"{CLICKUP_BASE_URL}/task/{field_op_id}"
        field_op_payload = {
            "custom_fields": [
                {
                    "id": FIELD_OP_CUSTOM_FIELDS['linked_site_visit'],
                    "value": None
                }
            ]
        }

        field_op_response = requests.put(field_op_update_url, headers=clickup_service.headers,
                                        json=field_op_payload, timeout=15)

        if field_op_response.status_code != 200:
            logger.error(f"Failed to update field operation: {field_op_response.text}")
            return jsonify({"error": "Failed to update field operation"}), field_op_response.status_code

        logger.info(f"Unlinked field op {field_op_id} from site visit {site_visit_id}")

        return jsonify({
            "success": True,
            "field_op_id": field_op_id,
            "site_visit_id": site_visit_id,
            "action": action
        })

    except Exception as e:
        logger.error(f"Error unlinking field operation: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to unlink field operation",
            "details": str(e)
        }), 500


@app.route('/api/site-visit/<site_visit_id>/details', methods=['GET'])
@login_required
@rate_limiter.rate_limit(limit='300 per hour')
def get_site_visit_details(site_visit_id):
    """
    Get detailed information about a site visit including all linked field operations.

    Returns:
    - Site visit metadata (date, vendor, status)
    - Array of linked field operations with full details
    - Validation status (all required fields present)
    """
    try:
        clickup_service = ClickUpService()

        # Get site visit task
        site_visit = clickup_service.get_task(site_visit_id)

        # Extract custom fields
        linked_field_op_ids = []
        site_visit_date = None
        vendor = None

        for field in site_visit.get('custom_fields', []):
            if field['id'] == SITE_VISIT_CUSTOM_FIELDS['linked_field_operations']:
                value = field.get('value', [])
                linked_field_op_ids = [op['id'] if isinstance(op, dict) else op for op in value]
            elif field['id'] == SITE_VISIT_CUSTOM_FIELDS['site_visit_date']:
                site_visit_date = field.get('value')
            elif field['id'] == SITE_VISIT_CUSTOM_FIELDS['vendor']:
                value = field.get('value', [])
                vendor = value[0] if value else None

        # Fetch full details for each linked field operation
        linked_field_ops_details = []
        for field_op_id in linked_field_op_ids:
            try:
                field_op = clickup_service.get_task(field_op_id)
                linked_field_ops_details.append({
                    'id': field_op['id'],
                    'name': field_op['name'],
                    'custom_item_id': field_op.get('custom_item_id'),
                    'status': field_op['status']['status'],
                    'url': field_op.get('url')
                })
            except Exception as e:
                logger.warning(f"Failed to fetch field op {field_op_id}: {e}")
                linked_field_ops_details.append({
                    'id': field_op_id,
                    'error': 'Failed to load details'
                })

        # Validation
        is_valid = bool(site_visit_date and vendor)

        return jsonify({
            "success": True,
            "site_visit": {
                "id": site_visit['id'],
                "name": site_visit['name'],
                "custom_item_id": site_visit.get('custom_item_id'),
                "status": site_visit['status']['status'],
                "site_visit_date": site_visit_date,
                "vendor": vendor,
                "url": site_visit.get('url'),
                "linked_field_operations": linked_field_ops_details,
                "linked_field_operations_count": len(linked_field_ops_details),
                "is_valid": is_valid,
                "validation_errors": [] if is_valid else [
                    "Site visit date required" if not site_visit_date else None,
                    "Vendor required" if not vendor else None
                ]
            }
        })

    except Exception as e:
        logger.error(f"Error fetching site visit details: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch site visit details",
            "details": str(e)
        }), 500


# =====================================================
# Local Dev API Routes - Field Operations Planning
# =====================================================

@app.route('/api/local/property/<property_id>/field-operations/unplanned', methods=['GET'])
def get_unplanned_field_operations_local(property_id):
    """LOCAL DEV ONLY: Get unplanned field operations without authentication"""
    if not IS_LOCAL_DEV:
        logger.warning("Attempted to access /api/local/* in production mode")
        abort(404)

    try:
        clickup_service = ClickUpService()
        import json
        custom_fields_filter = [{
            "field_id": PROPERTY_LINK_FIELD_ID,
            "operator": "ANY",
            "value": [property_id]
        }]

        url = f"{CLICKUP_BASE_URL}/list/{FIELD_OPS_LIST_ID}/task"
        params = {
            "custom_fields": json.dumps(custom_fields_filter),
            "include_timl": True
        }

        response = requests.get(url, headers=clickup_service.headers, params=params, timeout=15)

        if response.status_code != 200:
            logger.error(f"Failed to get field operations: {response.text}")
            return jsonify({"error": "Failed to fetch field operations"}), response.status_code

        all_field_ops = response.json().get('tasks', [])
        unplanned = []

        for task in all_field_ops:
            linked_site_visit = None
            vendor = None
            visit_date = None

            for field in task.get('custom_fields', []):
                if field['id'] == FIELD_OP_CUSTOM_FIELDS['linked_site_visit']:
                    value = field.get('value')
                    linked_site_visit = value if value else None
                elif field['id'] == FIELD_OP_CUSTOM_FIELDS['vendor']:
                    vendor = field.get('value')
                elif field['id'] == FIELD_OP_CUSTOM_FIELDS['visit_date']:
                    visit_date = field.get('value')

            if not linked_site_visit or (isinstance(linked_site_visit, list) and len(linked_site_visit) == 0):
                unplanned.append({
                    "id": task['id'],
                    "name": task['name'],
                    "vendor": vendor,
                    "visit_date": visit_date,
                    "status": task['status']['status']
                })

        return jsonify({"success": True, "unplanned_field_operations": unplanned})

    except Exception as e:
        logger.error(f"Error getting unplanned field operations: {str(e)}")
        return jsonify({"success": False, "error": "Internal server error", "details": str(e)}), 500


@app.route('/api/local/property/<property_id>/site-visits', methods=['GET'])
def get_property_site_visits_local(property_id):
    """LOCAL DEV ONLY: Get property site visits without authentication"""
    if not IS_LOCAL_DEV:
        logger.warning("Attempted to access /api/local/* in production mode")
        abort(404)

    try:
        clickup_service = ClickUpService()
        import json
        custom_fields_filter = [{
            "field_id": PROPERTY_LINK_FIELD_ID,
            "operator": "ANY",
            "value": [property_id]
        }]

        url = f"{CLICKUP_BASE_URL}/list/{SITE_VISITS_LIST_ID}/task"
        params = {"custom_fields": json.dumps(custom_fields_filter)}

        response = requests.get(url, headers=clickup_service.headers, params=params, timeout=15)

        if response.status_code != 200:
            logger.error(f"Failed to get site visits: {response.text}")
            return jsonify({"error": "Failed to fetch site visits"}), response.status_code

        site_visits = response.json().get('tasks', [])
        site_visits_data = []

        for task in site_visits:
            linked_field_ops = []
            site_visit_date = None
            vendor = None

            for field in task.get('custom_fields', []):
                if field['id'] == SITE_VISIT_CUSTOM_FIELDS['linked_field_operations']:
                    value = field.get('value', [])
                    if value and isinstance(value, list):
                        linked_field_ops = [op['id'] if isinstance(op, dict) else op for op in value]
                elif field['id'] == SITE_VISIT_CUSTOM_FIELDS['site_visit_date']:
                    site_visit_date = field.get('value')
                elif field['id'] == SITE_VISIT_CUSTOM_FIELDS['vendor']:
                    vendor = field.get('value')

            site_visits_data.append({
                "id": task['id'],
                "name": task['name'],
                "date": site_visit_date,
                "vendor": vendor,
                "linked_field_ops_count": len(linked_field_ops),
                "linked_field_ops": linked_field_ops,
                "status": task['status']['status']
            })

        return jsonify({"success": True, "site_visits": site_visits_data})

    except Exception as e:
        logger.error(f"Error getting site visits: {str(e)}")
        return jsonify({"success": False, "error": "Internal server error", "details": str(e)}), 500


@app.route('/api/local/property/<property_id>/site-visit/link-field-op', methods=['POST'])
def link_field_op_to_site_visit_local(property_id):
    """LOCAL DEV ONLY: Link field op to site visit without authentication"""
    if not IS_LOCAL_DEV:
        logger.warning("Attempted to access /api/local/* in production mode")
        abort(404)

    try:
        data = request.json
        field_op_id = data.get('field_op_id')
        site_visit_id = data.get('site_visit_id')
        site_visit_date = data.get('site_visit_date')
        vendor_id = data.get('vendor_id')

        if not field_op_id:
            return jsonify({"error": "field_op_id is required"}), 400

        clickup_service = ClickUpService()

        if not site_visit_id and site_visit_date:
            from datetime import datetime
            date_obj = datetime.fromtimestamp(site_visit_date / 1000)
            site_visit_name = f"Site Visit - {date_obj.strftime('%B %d, %Y')}"

            create_payload = {
                "name": site_visit_name,
                "custom_fields": [
                    {"id": PROPERTY_LINK_FIELD_ID, "value": [property_id]},  # ADD property_link
                    {"id": SITE_VISIT_CUSTOM_FIELDS['site_visit_date'], "value": site_visit_date},
                    {"id": SITE_VISIT_CUSTOM_FIELDS['linked_field_operations'], "value": [field_op_id]}
                ]
            }

            if vendor_id:
                create_payload['custom_fields'].append({
                    "id": SITE_VISIT_CUSTOM_FIELDS['vendor'],
                    "value": vendor_id
                })

            create_url = f"{CLICKUP_BASE_URL}/list/{SITE_VISITS_LIST_ID}/task"
            create_response = requests.post(create_url, headers=clickup_service.headers, json=create_payload, timeout=15)

            if create_response.status_code != 200:
                logger.error(f"Failed to create site visit: {create_response.text}")
                return jsonify({"error": "Failed to create site visit"}), create_response.status_code

            site_visit_id = create_response.json()['id']

        else:
            get_url = f"{CLICKUP_BASE_URL}/task/{site_visit_id}"
            get_response = requests.get(get_url, headers=clickup_service.headers, timeout=15)

            if get_response.status_code != 200:
                return jsonify({"error": "Site visit not found"}), 404

            site_visit_data = get_response.json()
            current_linked_ops = []
            site_visit_date_value = None
            site_visit_vendor = None

            for field in site_visit_data.get('custom_fields', []):
                if field['id'] == SITE_VISIT_CUSTOM_FIELDS['linked_field_operations']:
                    value = field.get('value', [])
                    if value and isinstance(value, list):
                        current_linked_ops = [op['id'] if isinstance(op, dict) else op for op in value]
                elif field['id'] == SITE_VISIT_CUSTOM_FIELDS['site_visit_date']:
                    site_visit_date_value = field.get('value')
                elif field['id'] == SITE_VISIT_CUSTOM_FIELDS['vendor']:
                    site_visit_vendor = field.get('value')

            if field_op_id not in current_linked_ops:
                current_linked_ops.append(field_op_id)

                update_payload = {
                    "custom_fields": [
                        {"id": SITE_VISIT_CUSTOM_FIELDS['linked_field_operations'], "value": current_linked_ops}
                    ]
                }

                update_url = f"{CLICKUP_BASE_URL}/task/{site_visit_id}"
                update_response = requests.put(update_url, headers=clickup_service.headers, json=update_payload, timeout=15)

                if update_response.status_code != 200:
                    logger.error(f"Failed to update site visit: {update_response.text}")
                    return jsonify({"error": "Failed to update site visit"}), update_response.status_code

        field_op_update = {
            "custom_fields": [
                {"id": FIELD_OP_CUSTOM_FIELDS['linked_site_visit'], "value": [site_visit_id]},
                {"id": FIELD_OP_CUSTOM_FIELDS['visit_date'], "value": site_visit_date}  # ADD visit_date (bidirectional sync)
            ]
        }

        if vendor_id and not data.get('skip_vendor_sync'):
            field_op_update['custom_fields'].append({
                "id": FIELD_OP_CUSTOM_FIELDS['vendor'],
                "value": vendor_id
            })

        field_op_url = f"{CLICKUP_BASE_URL}/task/{field_op_id}"
        field_op_response = requests.put(field_op_url, headers=clickup_service.headers, json=field_op_update, timeout=15)

        if field_op_response.status_code != 200:
            logger.error(f"Failed to update field operation: {field_op_response.text}")
            return jsonify({"error": "Failed to update field operation"}), field_op_response.status_code

        return jsonify({
            "success": True,
            "site_visit_id": site_visit_id,
            "field_op_id": field_op_id
        })

    except Exception as e:
        logger.error(f"Error linking field op to site visit: {str(e)}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route('/api/local/property/<property_id>/site-visit/unlink-field-op', methods=['POST'])
def unlink_field_op_from_site_visit_local(property_id):
    """LOCAL DEV ONLY: Unlink field op from site visit without authentication"""
    if not IS_LOCAL_DEV:
        logger.warning("Attempted to access /api/local/* in production mode")
        abort(404)

    try:
        data = request.json
        field_op_id = data.get('field_op_id')
        site_visit_id = data.get('site_visit_id')

        if not field_op_id or not site_visit_id:
            return jsonify({"error": "field_op_id and site_visit_id are required"}), 400

        clickup_service = ClickUpService()

        get_url = f"{CLICKUP_BASE_URL}/task/{site_visit_id}"
        get_response = requests.get(get_url, headers=clickup_service.headers, timeout=15)

        if get_response.status_code != 200:
            return jsonify({"error": "Site visit not found"}), 404

        site_visit_data = get_response.json()
        current_linked_ops = []

        for field in site_visit_data.get('custom_fields', []):
            if field['id'] == SITE_VISIT_CUSTOM_FIELDS['linked_field_operations']:
                value = field.get('value', [])
                if value and isinstance(value, list):
                    current_linked_ops = [op['id'] if isinstance(op, dict) else op for op in value]
                break

        if field_op_id in current_linked_ops:
            current_linked_ops.remove(field_op_id)

        if len(current_linked_ops) == 0:
            delete_url = f"{CLICKUP_BASE_URL}/task/{site_visit_id}"
            delete_response = requests.delete(delete_url, headers=clickup_service.headers, timeout=15)

            if delete_response.status_code != 200:
                logger.error(f"Failed to delete site visit: {delete_response.text}")
                return jsonify({"error": "Failed to delete site visit"}), delete_response.status_code
        else:
            update_payload = {
                "custom_fields": [
                    {"id": SITE_VISIT_CUSTOM_FIELDS['linked_field_operations'], "value": current_linked_ops}
                ]
            }

            update_url = f"{CLICKUP_BASE_URL}/task/{site_visit_id}"
            update_response = requests.put(update_url, headers=clickup_service.headers, json=update_payload, timeout=15)

            if update_response.status_code != 200:
                logger.error(f"Failed to update site visit: {update_response.text}")
                return jsonify({"error": "Failed to update site visit"}), update_response.status_code

        field_op_update = {
            "custom_fields": [
                {"id": FIELD_OP_CUSTOM_FIELDS['linked_site_visit'], "value": []}
            ]
        }

        field_op_url = f"{CLICKUP_BASE_URL}/task/{field_op_id}"
        field_op_response = requests.put(field_op_url, headers=clickup_service.headers, json=field_op_update, timeout=15)

        if field_op_response.status_code != 200:
            logger.error(f"Failed to update field operation: {field_op_response.text}")
            return jsonify({"error": "Failed to update field operation"}), field_op_response.status_code

        return jsonify({
            "success": True,
            "site_visit_deleted": len(current_linked_ops) == 0
        })

    except Exception as e:
        logger.error(f"Error unlinking field op from site visit: {str(e)}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route('/api/local/site-visit/<site_visit_id>/details', methods=['GET'])
def get_site_visit_details_local(site_visit_id):
    """LOCAL DEV ONLY: Get site visit details without authentication"""
    if not IS_LOCAL_DEV:
        logger.warning("Attempted to access /api/local/* in production mode")
        abort(404)

    try:
        clickup_service = ClickUpService()

        get_url = f"{CLICKUP_BASE_URL}/task/{site_visit_id}"
        get_response = requests.get(get_url, headers=clickup_service.headers, timeout=15)

        if get_response.status_code != 200:
            logger.error(f"Failed to get site visit: {get_response.text}")
            return jsonify({"error": "Site visit not found"}), 404

        site_visit = get_response.json()
        linked_field_ops_ids = []
        site_visit_date = None
        vendor = None

        for field in site_visit.get('custom_fields', []):
            if field['id'] == SITE_VISIT_CUSTOM_FIELDS['linked_field_operations']:
                value = field.get('value', [])
                if value and isinstance(value, list):
                    linked_field_ops_ids = [op['id'] if isinstance(op, dict) else op for op in value]
            elif field['id'] == SITE_VISIT_CUSTOM_FIELDS['site_visit_date']:
                site_visit_date = field.get('value')
            elif field['id'] == SITE_VISIT_CUSTOM_FIELDS['vendor']:
                vendor = field.get('value')

        linked_field_ops = []
        for field_op_id in linked_field_ops_ids:
            field_op_url = f"{CLICKUP_BASE_URL}/task/{field_op_id}"
            field_op_response = requests.get(field_op_url, headers=clickup_service.headers, timeout=15)

            if field_op_response.status_code == 200:
                field_op_data = field_op_response.json()
                linked_field_ops.append({
                    "id": field_op_data['id'],
                    "name": field_op_data['name'],
                    "status": field_op_data['status']['status']
                })

        is_valid = site_visit_date is not None and len(linked_field_ops) > 0

        return jsonify({
            "success": True,
            "site_visit": {
                "id": site_visit['id'],
                "name": site_visit['name'],
                "date": site_visit_date,
                "vendor": vendor,
                "linked_field_operations": linked_field_ops,
                "linked_field_operations_count": len(linked_field_ops),
                "is_valid": is_valid,
                "status": site_visit['status']['status']
            }
        })

    except Exception as e:
        logger.error(f"Error getting site visit details: {str(e)}")
        return jsonify({"success": False, "error": "Internal server error", "details": str(e)}), 500


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


@app.route('/pages/escalations')
@login_required
@rate_limiter.rate_limit(limit='100 per hour')
def serve_escalations_dashboard():
    """
    Serve escalation dashboard page showing all escalated tasks.
    Mobile-friendly list view with filtering by status and level.
    Allows users to navigate to individual escalation detail pages.
    """
    # Log page access for security audit
    logger.info(f"Secure page access: escalations dashboard by {request.user.get('email')}")

    # Render the template
    return render_template('secured/escalations.html')


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


@app.route('/pages/test/<task_id>')
@login_required
@rate_limiter.rate_limit(limit='100 per hour')
def serve_test_administration(task_id):
    """
    Serve test administration page for ClickUp-based tests
    OAuth protected page for taking tests where each task represents a test
    and each subtask represents a question with custom fields for metadata
    """
    # Log page access for security audit
    logger.info(f"Secure page access: test-administration (task: {task_id}) by {request.user.get('email')}")

    # Render the test template with task_id passed as query param
    # The React app will read task_id from URL query parameters
    return render_template('secured/test-administration.html')


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


@app.route('/pages/field-operations-planning')
@login_required
@rate_limiter.rate_limit(limit='100 per hour')
def serve_field_operations_planning():
    """
    Serve Field Operations Planning page - Property Dashboard module
    Three-panel drag-and-drop interface for scheduling field operations into site visits

    Query parameters:
    - property_id: REQUIRED - The property to manage field operations for
    """
    # Log page access for security audit
    logger.info(f"Secure page access: field-operations-planning by {request.user.get('email')}")

    # Render the template - query parameters (property_id) automatically available
    return render_template('secured/field-operations-planning.html')


@app.route('/local/field-operations-planning')
def serve_field_operations_planning_local():
    """Local development route - bypasses OAuth when LOCAL_DEV_MODE=true"""
    if not IS_LOCAL_DEV:
        logger.warning("Attempted to access /local/* route in production mode")
        return jsonify({"error": "Not found"}), 404

    # Set dev session for local testing
    session['user_email'] = 'dev@oodahost.com'
    session['user_name'] = 'Local Dev User'

    logger.info(f"Local dev access: field-operations-planning")
    return render_template('secured/field-operations-planning.html')


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


# ============================================================================
# PROPERTY DASHBOARD API ENDPOINTS
# ============================================================================

# Environment check for local development mode
IS_LOCAL_DEV = os.getenv('LOCAL_DEV_MODE', 'false').lower() == 'true'
app.config['IS_LOCAL_DEV'] = IS_LOCAL_DEV

# Cache storage for properties (5-minute TTL)
PROPERTY_CACHE = {}
CACHE_TTL_SECONDS = 300  # 5 minutes

def get_cached_data(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get data from cache if not expired"""
    if cache_key in PROPERTY_CACHE:
        cached_data, timestamp = PROPERTY_CACHE[cache_key]
        age_seconds = (datetime.now() - timestamp).total_seconds()
        if age_seconds < CACHE_TTL_SECONDS:
            logger.info(f"Cache hit for {cache_key} (age: {age_seconds:.1f}s)")
            return cached_data
        else:
            logger.info(f"Cache expired for {cache_key} (age: {age_seconds:.1f}s)")
            del PROPERTY_CACHE[cache_key]
    return None

def set_cached_data(cache_key: str, data: Dict[str, Any]):
    """Store data in cache with timestamp"""
    PROPERTY_CACHE[cache_key] = (data, datetime.now())
    logger.info(f"Cached data for {cache_key}")

def fetch_with_retry(url: str, headers: Dict[str, str], params: Dict[str, Any] = None,
                     max_retries: int = 2) -> requests.Response:
    """
    Fetch data with exponential backoff retry logic
    Retry delays: 1s, 3s
    """
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            if attempt < max_retries:
                delay = 1 * (3 ** attempt)  # 1s, 3s
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {delay}s...")
                import time
                time.sleep(delay)
            else:
                logger.error(f"Request failed after {max_retries + 1} attempts: {e}")
                raise

# ============================================================================
# LOCAL DEV API ENDPOINTS (No Authentication Required)
# These endpoints are only available when LOCAL_DEV_MODE=true
# ============================================================================

@app.route('/api/local/properties', methods=['GET'])
def get_all_properties_local():
    """
    LOCAL DEV ONLY: Get all properties without authentication
    Returns 404 in production (LOCAL_DEV_MODE=false)
    """
    if not IS_LOCAL_DEV:
        logger.warning("Attempted to access /api/local/* in production mode")
        abort(404)

    try:
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'

        # Check cache unless force refresh
        cache_key = 'all_properties'
        if not force_refresh:
            cached_data = get_cached_data(cache_key)
            if cached_data:
                return jsonify(cached_data)

        # Fetch from ClickUp API with pagination
        properties_list_id = '901109451960'
        url = f"{CLICKUP_BASE_URL}/list/{properties_list_id}/task"
        headers = {
            "Authorization": CLICKUP_API_KEY,
            "Content-Type": "application/json"
        }
        params = {
            "include_closed": "false",
            "subtasks": "false"
        }

        all_tasks = []
        page = 0

        # Loop through all pages
        while True:
            logger.info(f"Fetching properties from ClickUp (page {page})...")
            params['page'] = page
            response = fetch_with_retry(url, headers, params)
            data = response.json()

            tasks = data.get('tasks', [])
            if not tasks:
                # Empty page means we've fetched all tasks
                logger.info(f"Page {page} returned no tasks - pagination complete")
                break

            all_tasks.extend(tasks)
            logger.info(f"Fetched {len(tasks)} properties from page {page} (total so far: {len(all_tasks)})")

            # If we got fewer than 100 tasks, this is the last page
            if len(tasks) < 100:
                logger.info(f"Page {page} returned fewer than 100 tasks - this is the last page")
                break

            page += 1

            # Safety limit to prevent infinite loops
            if page > 10:
                logger.warning("Reached page limit (10), stopping pagination")
                break

        # Count by company
        ooda_count = sum(1 for task in all_tasks
                        if any(cf.get('name') == 'Company Name ' and cf.get('value') == 'Oodahost'
                              for cf in task.get('custom_fields', [])))
        helm_count = sum(1 for task in all_tasks
                        if any(cf.get('name') == 'Company Name ' and cf.get('value') != 'Oodahost'
                              for cf in task.get('custom_fields', [])))

        # Build response
        response_data = {
            "success": True,
            "data": {
                "properties": all_tasks,
                "total_count": len(all_tasks),
                "ooda_count": ooda_count,
                "helm_count": helm_count,
                "cached_at": datetime.now().isoformat()
            }
        }

        # Cache the response
        set_cached_data(cache_key, response_data)

        logger.info(f"[LOCAL DEV] Successfully fetched {len(all_tasks)} properties (OODA: {ooda_count}, HELM: {helm_count})")
        return jsonify(response_data)

    except requests.RequestException as e:
        logger.error(f"ClickUp API error: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "API_ERROR",
                "message": "Failed to fetch properties from ClickUp"
            }
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": "An unexpected error occurred"
            }
        }), 500

@app.route('/api/local/property/<property_id>', methods=['GET'])
def get_single_property_local(property_id: str):
    """
    LOCAL DEV ONLY: Get single property without authentication
    Returns 404 in production (LOCAL_DEV_MODE=false)
    """
    if not IS_LOCAL_DEV:
        logger.warning("Attempted to access /api/local/* in production mode")
        abort(404)

    try:
        url = f"{CLICKUP_BASE_URL}/task/{property_id}"
        headers = {
            "Authorization": CLICKUP_API_KEY,
            "Content-Type": "application/json"
        }
        params = {
            "include_subtasks": "false"
        }

        logger.info(f"[LOCAL DEV] Fetching property {property_id}...")
        response = fetch_with_retry(url, headers, params)
        task_data = response.json()

        return jsonify({
            "success": True,
            "data": {
                "property": task_data
            }
        })

    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return jsonify({
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Property not found or you don't have access"
                }
            }), 404
        else:
            logger.error(f"ClickUp API error: {e}")
            return jsonify({
                "success": False,
                "error": {
                    "code": "API_ERROR",
                    "message": "Failed to fetch property from ClickUp"
                }
            }), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": "An unexpected error occurred"
            }
        }), 500

def transform_reservation_to_event(reservation_task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Transform ClickUp reservation task to calendar event format.

    Filters out cancelled reservations.
    Extracts: check-in/check-out dates, guest name, cleaning link, status.

    Returns None if:
    - Missing check-in or check-out dates
    - Status is 'cancelled'
    """
    try:
        # Filter out cancelled reservations
        status = reservation_task.get('status', {}).get('status', '').lower()
        if status == 'cancelled':
            return None

        # Extract custom fields
        custom_fields = reservation_task.get('custom_fields', [])

        # Required fields
        check_in_field_id = '29df3914-239c-4df8-a73c-5ba349f5076c'
        check_out_field_id = '9f3de1f0-244a-4882-8ebd-bb93c2c6c153'

        # Optional fields
        cleaning_link_field_id = '66c6bc7c-4616-40e5-9561-8c5017208799'
        property_link_field_id = '73999194-0433-433d-a27c-4d9c5f194fd0'

        check_in_timestamp = None
        check_out_timestamp = None
        cleaning_link = None
        property_link = None
        guest_name = None

        for field in custom_fields:
            field_id = field.get('id')
            if field_id == check_in_field_id:
                check_in_timestamp = field.get('value')
            elif field_id == check_out_field_id:
                check_out_timestamp = field.get('value')
            elif field_id == cleaning_link_field_id:
                # Task relationship field - value is array of task objects
                cleaning_value = field.get('value', [])
                if cleaning_value and len(cleaning_value) > 0:
                    cleaning_link = cleaning_value[0].get('id')
            elif field_id == property_link_field_id:
                # Task relationship field
                property_value = field.get('value', [])
                if property_value and len(property_value) > 0:
                    property_link = property_value[0].get('id')
            elif field.get('name') == 'Guest Name':
                guest_name = field.get('value')

        # Validation: Must have check-in and check-out dates
        if not check_in_timestamp or not check_out_timestamp:
            logger.warning(f"Reservation {reservation_task.get('id')} missing dates - skipping")
            return None

        # Parse task name for guest name if custom field is empty
        task_name = reservation_task.get('name', '')
        if not guest_name and ' - ' in task_name:
            guest_name = task_name.split(' - ')[0].strip()

        # Convert timestamps to ISO format
        check_in_date = datetime.fromtimestamp(int(check_in_timestamp) / 1000).isoformat()
        check_out_date = datetime.fromtimestamp(int(check_out_timestamp) / 1000).isoformat()

        # Build event object
        event = {
            "id": reservation_task.get('id'),
            "type": "reservation",
            "custom_item_id": reservation_task.get('custom_item_id', 1001),
            "title": guest_name or task_name,
            "task_name": task_name,
            "check_in": check_in_date,
            "check_out": check_out_date,
            "check_in_timestamp": int(check_in_timestamp),
            "check_out_timestamp": int(check_out_timestamp),
            "status": status,
            "clickup_url": reservation_task.get('url'),
            "details": {
                "guest_name": guest_name,
                "cleaning_link": cleaning_link,
                "property_link": property_link
            }
        }

        return event

    except Exception as e:
        logger.error(f"Error transforming reservation {reservation_task.get('id', 'unknown')}: {e}")
        return None

@app.route('/api/local/property/<property_id>/calendar', methods=['GET'])
def get_property_calendar_local(property_id: str):
    """
    LOCAL DEV ONLY: Get calendar events without authentication
    Returns 404 in production (LOCAL_DEV_MODE=false)
    V2: Fetches and transforms reservations from ClickUp
    """
    if not IS_LOCAL_DEV:
        logger.warning("Attempted to access /api/local/* in production mode")
        abort(404)

    try:
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'

        # Check cache unless force refresh
        cache_key = f'calendar_{property_id}'
        if not force_refresh:
            cached_data = get_cached_data(cache_key)
            if cached_data:
                logger.info(f"Cache hit for {cache_key}")
                return jsonify(cached_data)

        # Get date range from query params
        start_date = request.args.get('start_date', datetime.now().replace(day=1).isoformat()[:10])
        end_date = request.args.get('end_date', datetime.now().replace(day=28).isoformat()[:10])

        logger.info(f"[LOCAL DEV] Fetching calendar for property {property_id} ({start_date} to {end_date})")

        # Fetch reservations filtered by property_link
        reservations_list_id = '901109506017'
        property_link_field_id = '73999194-0433-433d-a27c-4d9c5f194fd0'

        # Build custom_fields filter for property_link
        # CRITICAL: Task relationship fields require ANY operator with array value
        # Reference: /Local/clickup-reference/CRITICAL-task-relationship-filtering.md
        import json as json_lib
        import urllib.parse
        custom_fields_filter = json_lib.dumps([{
            "field_id": property_link_field_id,
            "operator": "ANY",
            "value": [property_id]  # MUST be array for task relationship fields
        }])

        url = f"{CLICKUP_BASE_URL}/list/{reservations_list_id}/task"
        headers = {
            "Authorization": CLICKUP_API_KEY,
            "Content-Type": "application/json"
        }
        params = {
            "include_closed": "false",
            "subtasks": "false",
            "custom_fields": custom_fields_filter
        }

        # Fetch all pages of reservations
        all_reservations = []
        page = 0

        while True:
            logger.info(f"Fetching reservations (page {page})...")
            params['page'] = page

            # DEBUG: Log the filter being applied
            logger.info(f"[DEBUG] custom_fields filter: {custom_fields_filter}")
            logger.info(f"[DEBUG] Full params: {params}")

            response = fetch_with_retry(url, headers, params)
            data = response.json()

            tasks = data.get('tasks', [])
            if not tasks:
                logger.info(f"Page {page} returned no tasks - pagination complete")
                break

            all_reservations.extend(tasks)
            logger.info(f"Fetched {len(tasks)} reservations from page {page} (total: {len(all_reservations)})")

            if len(tasks) < 100:
                logger.info(f"Page {page} returned fewer than 100 tasks - last page")
                break

            page += 1
            if page > 10:
                logger.warning("Reached page limit (10)")
                break

        # The ClickUp API filter with ANY operator correctly filters by property_link
        # Reference: /Local/clickup-reference/CRITICAL-task-relationship-filtering.md
        # No client-side post-filtering needed - API returns pre-filtered results
        filtered_reservations = all_reservations
        logger.info(f"API returned {len(filtered_reservations)} reservations for property {property_id}")

        # Transform reservations to calendar events
        calendar_events = []
        for reservation in filtered_reservations:
            event = transform_reservation_to_event(reservation)
            if event:
                calendar_events.append(event)

        logger.info(f"Transformed {len(calendar_events)} reservations to calendar events")

        # Build response
        response_data = {
            "success": True,
            "data": {
                "property_id": property_id,
                "events": calendar_events,
                "total_count": len(calendar_events),
                "date_range": {
                    "start": start_date,
                    "end": end_date
                },
                "cached_at": datetime.now().isoformat()
            }
        }

        # Cache the response
        set_cached_data(cache_key, response_data)

        return jsonify(response_data)

    except requests.RequestException as e:
        logger.error(f"ClickUp API error: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "API_ERROR",
                "message": "Failed to fetch calendar events from ClickUp"
            }
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": "An unexpected error occurred"
            }
        }), 500

@app.route('/api/local/user/role', methods=['GET'])
def get_user_role_local():
    """
    LOCAL DEV ONLY: Get user role without authentication
    Returns 404 in production (LOCAL_DEV_MODE=false)
    """
    if not IS_LOCAL_DEV:
        logger.warning("Attempted to access /api/local/* in production mode")
        abort(404)

    return jsonify({
        'role': 'user',
        'user_email': 'dev@oodahost.com',
        'is_supervisor': False
    })

# ============================================================================
# PRODUCTION API ENDPOINTS (Authentication Required)
# ============================================================================

@app.route('/api/properties', methods=['GET'])
@login_required
def get_all_properties():
    """
    Get all properties from ClickUp Properties list
    Returns complete ClickUp API response with no backend filtering
    Implements 5-minute caching and retry logic
    """
    try:
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'

        # Check cache unless force refresh
        cache_key = 'all_properties'
        if not force_refresh:
            cached_data = get_cached_data(cache_key)
            if cached_data:
                return jsonify(cached_data)

        # Fetch from ClickUp API
        properties_list_id = '901109451960'
        url = f"{CLICKUP_BASE_URL}/list/{properties_list_id}/task"
        headers = {
            "Authorization": CLICKUP_API_KEY,
            "Content-Type": "application/json"
        }
        params = {
            "include_closed": "false",
            "subtasks": "false"
        }

        # Fetch first page
        logger.info("Fetching properties from ClickUp (page 0)...")
        response = fetch_with_retry(url, headers, params)
        data = response.json()

        all_tasks = data.get('tasks', [])
        logger.info(f"Fetched {len(all_tasks)} properties from page 0")

        # Handle pagination (PRD mentions 2 pages total)
        # ClickUp pagination uses 'last_id' cursor
        if 'last_id' in data and data['last_id']:
            logger.info("Fetching properties from ClickUp (page 1)...")
            params['page'] = 1
            response_page2 = fetch_with_retry(url, headers, params)
            data_page2 = response_page2.json()
            tasks_page2 = data_page2.get('tasks', [])
            all_tasks.extend(tasks_page2)
            logger.info(f"Fetched {len(tasks_page2)} properties from page 1")

        # Count by company
        ooda_count = sum(1 for task in all_tasks
                        if any(cf.get('name') == 'Company Name ' and cf.get('value') == 'Oodahost'
                              for cf in task.get('custom_fields', [])))
        helm_count = sum(1 for task in all_tasks
                        if any(cf.get('name') == 'Company Name ' and cf.get('value') != 'Oodahost'
                              for cf in task.get('custom_fields', [])))

        # Build response
        response_data = {
            "success": True,
            "data": {
                "properties": all_tasks,  # Complete task objects from ClickUp
                "total_count": len(all_tasks),
                "ooda_count": ooda_count,
                "helm_count": helm_count,
                "cached_at": datetime.now().isoformat()
            }
        }

        # Cache the response
        set_cached_data(cache_key, response_data)

        logger.info(f"Successfully fetched {len(all_tasks)} properties (OODA: {ooda_count}, HELM: {helm_count})")
        return jsonify(response_data)

    except requests.RequestException as e:
        logger.error(f"ClickUp API error: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "API_ERROR",
                "message": "Failed to fetch properties from ClickUp"
            }
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": "An unexpected error occurred"
            }
        }), 500

@app.route('/api/property/<property_id>', methods=['GET'])
@login_required
def get_single_property(property_id: str):
    """
    Get single property details by ID
    Returns complete task object with all custom fields
    """
    try:
        url = f"{CLICKUP_BASE_URL}/task/{property_id}"
        headers = {
            "Authorization": CLICKUP_API_KEY,
            "Content-Type": "application/json"
        }
        params = {
            "include_subtasks": "false"
        }

        logger.info(f"Fetching property {property_id}...")
        response = fetch_with_retry(url, headers, params)
        task_data = response.json()

        return jsonify({
            "success": True,
            "data": {
                "property": task_data  # Complete task object
            }
        })

    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return jsonify({
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Property not found or you don't have access"
                }
            }), 404
        else:
            logger.error(f"ClickUp API error: {e}")
            return jsonify({
                "success": False,
                "error": {
                    "code": "API_ERROR",
                    "message": "Failed to fetch property from ClickUp"
                }
            }), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": "An unexpected error occurred"
            }
        }), 500

@app.route('/api/property/<property_id>/calendar', methods=['GET'])
@login_required_with_local_dev
@rate_limiter.rate_limit(limit='300 per hour')
def get_property_calendar(property_id: str):
    """
    Get calendar events for a property
    V2: Fetches reservations with check-in/check-out dates

    Lists to aggregate:
    - Reservations: 901109506017 (IMPLEMENTED)
    - Cleanings: 901108930620 (Future)
    - Field Ops: 901108930624 (Future)
    - Calendar Blocks: 901111267656 (Future)

    Filter by property_link field ID: 73999194-0433-433d-a27c-4d9c5f194fd0
    """
    try:
        # List and field IDs
        reservations_list_id = '901109506017'
        check_in_field_id = '29df3914-239c-4df8-a73c-5ba349f5076c'
        check_out_field_id = '9f3de1f0-244a-4882-8ebd-bb93c2c6c153'

        logger.info(f"Fetching calendar for property {property_id}")

        # Build filter for reservations by property_link
        custom_fields_filter = [{
            "field_id": PROPERTY_LINK_FIELD_ID,
            "operator": "ANY",
            "value": [property_id]
        }]

        url = f"{CLICKUP_BASE_URL}/list/{reservations_list_id}/task"
        params = {
            "custom_fields": json.dumps(custom_fields_filter)
        }

        response = requests.get(
            url,
            headers=clickup_service.headers,
            params=params,
            timeout=15
        )

        if response.status_code != 200:
            logger.error(f"Failed to fetch reservations: {response.text}")
            return jsonify({"error": "Failed to fetch reservations"}), response.status_code

        raw_reservations = response.json().get('tasks', [])
        logger.info(f"Found {len(raw_reservations)} reservations for property {property_id}")

        # Parse reservations into calendar events
        events = []
        for task in raw_reservations:
            check_in_ts = None
            check_out_ts = None

            # Extract date custom fields
            for field in task.get('custom_fields', []):
                if field['id'] == check_in_field_id:
                    check_in_ts = field.get('value')
                elif field['id'] == check_out_field_id:
                    check_out_ts = field.get('value')

            # Parse dates
            if check_in_ts and check_out_ts:
                try:
                    # Convert string timestamps to integers if needed
                    if isinstance(check_in_ts, str):
                        check_in_ts = int(check_in_ts)
                    if isinstance(check_out_ts, str):
                        check_out_ts = int(check_out_ts)

                    # Convert to datetime objects
                    check_in_dt = datetime.fromtimestamp(check_in_ts / 1000)
                    check_out_dt = datetime.fromtimestamp(check_out_ts / 1000)

                    # Format as YYYY-MM-DD for frontend
                    check_in_key = check_in_dt.strftime('%Y-%m-%d')
                    check_out_key = check_out_dt.strftime('%Y-%m-%d')

                    # Calculate duration
                    duration = (check_out_dt - check_in_dt).days

                    events.append({
                        "id": task['id'],
                        "type": "reservation",
                        "title": task['name'],
                        "check_in": check_in_key,
                        "check_out": check_out_key,
                        "check_in_ts": check_in_ts,
                        "check_out_ts": check_out_ts,
                        "duration_days": duration,
                        "status": task.get('status', {}).get('status', 'unknown'),
                        "url": task.get('url')
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse dates for task {task['id']}: {e}")
                    continue

        logger.info(f"Parsed {len(events)} calendar events from reservations")

        return jsonify({
            "success": True,
            "data": {
                "property_id": property_id,
                "events": events,
                "event_sources": {
                    "reservations": raw_reservations,  # Full task data
                    "cleanings": [],     # Future
                    "field_ops": [],     # Future
                    "calendar_blocks": []  # Future
                }
            }
        })

    except Exception as e:
        logger.error(f"Calendar fetch error: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e)
            }
        }), 500

# Route-based separation: Production vs Local Development
# Production routes (OAuth required)
@app.route('/pages/property-dashboard')
@login_required
def serve_property_dashboard():
    """Production route - OAuth authentication required"""
    return render_template('secured/property-dashboard.html')

# Local development routes (OAuth bypassed)
@app.route('/local/property-dashboard')
def serve_property_dashboard_local():
    """Local development route - bypasses OAuth when LOCAL_DEV_MODE=true"""
    if not IS_LOCAL_DEV:
        logger.warning("Attempted to access /local/* route in production mode")
        return jsonify({"error": "Not found"}), 404

    # Bypass authentication in local dev
    session['user_email'] = os.getenv('DEV_USER_EMAIL', 'dev@oodahost.com')
    session['auth_token'] = 'local-dev-token'
    session['authenticated'] = True

    logger.info(f"Local dev access - bypassing OAuth for {session['user_email']}")
    return render_template('secured/property-dashboard.html')

@app.route('/local/test-calendar-v3')
def serve_test_calendar_v3():
    """Test route for Calendar V3 (day-based architecture)"""
    if not IS_LOCAL_DEV:
        logger.warning("Attempted to access /local/* route in production mode")
        return jsonify({"error": "Not found"}), 404

    # Bypass authentication in local dev
    session['user_email'] = os.getenv('DEV_USER_EMAIL', 'dev@oodahost.com')
    session['auth_token'] = 'local-dev-token'
    session['authenticated'] = True

    logger.info(f"Calendar V3 test access - bypassing OAuth for {session['user_email']}")

    # Serve the test HTML file from Local directory
    from flask import send_from_directory
    local_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'Local')
    return send_from_directory(local_dir, 'test-calendar-v3.html')

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