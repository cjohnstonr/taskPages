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
import openai
from flask_session import Session
from flask_cors import CORS
from dotenv import load_dotenv
import redis
import requests
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

# Import security modules
from config.security import SecureConfig
from auth.oauth_handler import auth_bp, init_redis, login_required
from auth.security_middleware import SecurityMiddleware, RateLimiter

# Configure logging FIRST (before using logger)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    logger.warning("OpenAI API key not found in environment variables")
else:
    # Mask the API key for logging
    masked_key = f"{openai.api_key[:10]}...{openai.api_key[-10:]}" if len(openai.api_key) > 20 else "***"
    logger.info(f"OpenAI API key loaded: {masked_key}")

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
        logger.info(f"Initializing wait node for task: {task_id} by user: {session.get('user', {}).get('email', 'Unknown')}")
        
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
        logger.info(f"Processing approval for task {task_id} by user: {session.get('user', {}).get('email', 'Unknown')}")
        
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
        logger.info(f"Approval completed for task {task_id} by {session.get('user', {}).get('email', 'Unknown')}")
        
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
        logger.info(f"Field {field_id} updated on task {task_id} by {session.get('user', {}).get('email', 'Unknown')}")
        
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
        
        logger.info(f"Updated field {field_id} on task {task_id} by {session.get('user', {}).get('email', 'Unknown')}")
        
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
        
        logger.info(f"Deleted task {task_id} by {session.get('user', {}).get('email', 'Unknown')}")
        
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
    Reuses wait-node logic but can be customized for task-helper specific needs
    """
    try:
        # Get ClickUp API configuration
        clickup_token = os.getenv('CLICKUP_API_KEY')
        if not clickup_token:
            logger.error("ClickUp API key not configured")
            return jsonify({"error": "ClickUp integration not configured"}), 500

        # Fetch the main task
        task_response = requests.get(
            f"https://api.clickup.com/api/v2/task/{task_id}",
            headers={"Authorization": clickup_token},
            params={"include_subtasks": "true"}
        )
        
        if task_response.status_code == 404:
            return jsonify({"error": "Task not found"}), 404
        elif not task_response.ok:
            logger.error(f"ClickUp API error fetching task: {task_response.status_code}")
            return jsonify({"error": "Failed to fetch task from ClickUp"}), 500
        
        main_task = task_response.json()
        
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
            parent_response = requests.get(
                f"https://api.clickup.com/api/v2/task/{parent_id}",
                headers={"Authorization": clickup_token}
            )
            
            if parent_response.ok:
                response_data["parent_task"] = parent_response.json()
                response_data["hierarchy"]["has_parent"] = True
                response_data["hierarchy"]["parent_id"] = parent_id
                response_data["hierarchy"]["is_subtask"] = True
        
        # Get subtasks if any
        if main_task.get('subtasks'):
            subtask_ids = [st['id'] for st in main_task['subtasks']]
            for subtask_id in subtask_ids[:10]:  # Limit to 10 for performance
                subtask_response = requests.get(
                    f"https://api.clickup.com/api/v2/task/{subtask_id}",
                    headers={"Authorization": clickup_token}
                )
                if subtask_response.ok:
                    response_data["subtasks"].append(subtask_response.json())
        
        return jsonify(response_data)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"ClickUp API request failed: {e}")
        return jsonify({"error": "Failed to communicate with ClickUp API"}), 500
    except Exception as e:
        logger.error(f"Error initializing task helper for task {task_id}: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route('/api/task-helper/escalate/<task_id>', methods=['POST'])
@login_required
@rate_limiter.rate_limit(limit='10 per minute')
def escalate_task(task_id):
    """
    Escalate a task - adds escalation custom fields and creates notification
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        escalation_reason = data.get('reason', '').strip()
        ai_summary = data.get('ai_summary', '').strip()
        task_context = data.get('task_context', {})

        if not escalation_reason:
            return jsonify({"error": "Escalation reason is required"}), 400

        # Log escalation attempt for audit
        logger.info(f"Task escalation requested for {task_id} by {session.get('user', {}).get('email', 'Unknown')}")

        # Get ClickUp API configuration
        clickup_token = os.getenv('CLICKUP_API_KEY')
        if not clickup_token:
            logger.error("ClickUp API key not configured")
            return jsonify({"error": "ClickUp integration not configured"}), 500

        # Custom field IDs for escalation - ALL 7 FIELDS
        escalation_fields = {
            'ESCALATION_REASON': 'c6e0281e-9001-42d7-a265-8f5da6b71132',
            'ESCALATION_AI_SUMMARY': 'e9e831f2-b439-4067-8e88-6b715f4263b2', 
            'ESCALATION_STATUS': '8d784bd0-18e5-4db3-b45e-9a2900262e04',
            'ESCALATED_TO': '934811f1-239f-4d53-880c-3655571fd02e',
            'ESCALATION_TIMESTAMP': '5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f',
            'SUPERVISOR_RESPONSE': 'a077ecc9-1a59-48af-b2cd-42a63f5a7f86',
            'ESCALATION_RESOLVED_TIMESTAMP': 'c40bf1c4-7d33-4b2b-8765-0784cd88591a'
        }

        # Get escalated_to from request (supervisor selection)
        escalated_to = data.get('escalated_to', '')  # User ID or email

        try:
            # 1. Update task custom fields with escalation data
            custom_fields = [
                {"id": escalation_fields['ESCALATION_REASON'], "value": escalation_reason},
                {"id": escalation_fields['ESCALATION_AI_SUMMARY'], "value": ai_summary},
                {"id": escalation_fields['ESCALATION_STATUS'], "value": "pending"},  # Set to pending until supervisor responds
                {"id": escalation_fields['ESCALATION_TIMESTAMP'], "value": int(datetime.now().timestamp() * 1000)}
            ]
            
            # Add escalated_to if provided
            if escalated_to:
                custom_fields.append({"id": escalation_fields['ESCALATED_TO'], "value": escalated_to})
            
            # Update task with custom fields
            update_response = requests.put(
                f"https://api.clickup.com/api/v2/task/{task_id}",
                headers={
                    "Authorization": clickup_token,
                    "Content-Type": "application/json"
                },
                json={"custom_fields": custom_fields}
            )
            
            if not update_response.ok:
                logger.error(f"Failed to update task custom fields: {update_response.text}")
                return jsonify({"error": "Failed to save escalation to ClickUp"}), 500

            # 2. Add escalation comment to task
            escalation_comment = f"""🚨 **TASK ESCALATED**

**Reason**: {escalation_reason}

**AI Summary**: 
{ai_summary}

**Escalated by**: {session.get('user', {}).get('email', 'Unknown')}
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
                "escalated_by": session.get('user', {}).get('email', 'Unknown'),
                "escalation_data": {
                    "reason": escalation_reason,
                    "ai_summary": ai_summary,
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
    Handle supervisor response to an escalated task
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        supervisor_response_text = data.get('response', '').strip()
        
        if not supervisor_response_text:
            return jsonify({"error": "Supervisor response is required"}), 400

        # Log supervisor response for audit
        logger.info(f"Supervisor response for task {task_id} by {session.get('user', {}).get('email', 'Unknown')}")

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
            # Update task custom fields with supervisor response
            custom_fields = [
                {"id": escalation_fields['SUPERVISOR_RESPONSE'], "value": supervisor_response_text},
                {"id": escalation_fields['ESCALATION_STATUS'], "value": "resolved"},  # Update status to resolved
                {"id": escalation_fields['ESCALATION_RESOLVED_TIMESTAMP'], "value": int(datetime.now().timestamp() * 1000)}
            ]
            
            # Update task with custom fields
            update_response = requests.put(
                f"https://api.clickup.com/api/v2/task/{task_id}",
                headers={
                    "Authorization": clickup_token,
                    "Content-Type": "application/json"
                },
                json={"custom_fields": custom_fields}
            )
            
            if not update_response.ok:
                logger.error(f"Failed to update task with supervisor response: {update_response.text}")
                return jsonify({"error": "Failed to save supervisor response to ClickUp"}), 500

            # Add resolution comment to task
            resolution_comment = f"""✅ **ESCALATION RESOLVED**

**Supervisor Response**: 
{supervisor_response_text}

**Resolved by**: {session.get('user', {}).get('email', 'Unknown')}
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
                "resolved_by": session.get('user', {}).get('email', 'Unknown'),
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


@app.route('/api/ai/generate-escalation-summary', methods=['POST'])
@login_required  
@rate_limiter.rate_limit(limit='20 per minute')
def generate_escalation_summary():
    """
    Generate AI summary for task escalation using OpenAI/ChatGPT
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        task_id = data.get('task_id')
        reason = data.get('reason', '').strip()
        context = data.get('context', {})

        if not task_id or not reason:
            return jsonify({"error": "task_id and reason are required"}), 400

        # Log AI summary generation for audit
        logger.info(f"AI summary generation requested for task {task_id} by {session.get('user', {}).get('email', 'Unknown')}")

        # Format task context for AI prompt
        task_info = context.get('task', {})
        parent_task_info = context.get('parent_task', {})
        subtasks_info = context.get('subtasks', [])
        
        # [DEBUG] Add comprehensive logging before prompt construction
        logger.info(f"[AI DEBUG] === Starting prompt construction ===")
        logger.info(f"[AI DEBUG] task_info type: {type(task_info)}")
        logger.info(f"[AI DEBUG] task_info keys: {list(task_info.keys()) if task_info else 'None'}")
        
        # Check status field specifically
        status_field = task_info.get('status')
        logger.info(f"[AI DEBUG] task_info.get('status') = {status_field}")
        logger.info(f"[AI DEBUG] status type: {type(status_field)}")
        
        # Check priority field specifically  
        priority_field = task_info.get('priority')
        logger.info(f"[AI DEBUG] task_info.get('priority') = {priority_field}")
        logger.info(f"[AI DEBUG] priority type: {type(priority_field)}")
        
        # Check subtasks
        logger.info(f"[AI DEBUG] subtasks_info count: {len(subtasks_info)}")
        for i, subtask in enumerate(subtasks_info[:3]):  # Log first 3 subtasks
            subtask_status = subtask.get('status')
            logger.info(f"[AI DEBUG] subtask[{i}].get('status') = {subtask_status}, type = {type(subtask_status)}")
        
        # FIX: Safely get status text (handle None values from ClickUp)
        status_obj = task_info.get('status')
        if status_obj is None:
            status_text = 'Unknown'
            logger.info(f"[AI DEBUG] status is None, using 'Unknown'")
        else:
            status_text = status_obj.get('status', 'Unknown') if isinstance(status_obj, dict) else 'Unknown'
            logger.info(f"[AI DEBUG] status_text extracted: {status_text}")
        
        # FIX: Safely get priority text (handle None values from ClickUp)
        priority_obj = task_info.get('priority')
        if priority_obj is None:
            priority_text = 'None'
            logger.info(f"[AI DEBUG] priority is None, using 'None'")
        else:
            priority_text = priority_obj.get('priority', 'None') if isinstance(priority_obj, dict) else 'None'
            logger.info(f"[AI DEBUG] priority_text extracted: {priority_text}")
        
        # Build comprehensive context for AI
        ai_prompt = f"""You are an expert project manager helping to prioritize task escalations. 

ESCALATION REQUEST:
- Task: {task_info.get('name', 'Unknown Task')} (ID: {task_id})
- Escalated by: {session.get('user', {}).get('email', 'Unknown')}
- Reason for escalation: {reason}

TASK CONTEXT:
- Status: {status_text}
- Priority: {priority_text}
- Assignees: {', '.join([a.get('username', 'Unknown') for a in task_info.get('assignees', [])])}
- Due Date: {task_info.get('due_date', 'Not set')}
- Description: {(task_info.get('description', 'No description')[:200] + '...' if len(task_info.get('description', '')) > 200 else task_info.get('description', 'No description'))}

HIERARCHY CONTEXT:
- Parent Task: {parent_task_info.get('name', 'None')}
- Subtasks: {len(subtasks_info)} total
- Completed Subtasks: {len([s for s in subtasks_info if s.get('status') and isinstance(s.get('status'), dict) and s.get('status').get('type', '') == 'closed'])}

Please provide a concise escalation summary that:
1. Clearly explains the issue and why it needs attention
2. Provides relevant context about the task and its place in the project
3. Suggests a priority level and recommended timeline for resolution
4. Keeps the summary under 300 words

Format your response as a professional escalation summary."""

        try:
            # Extensive logging for debugging
            logger.info(f"[AI SUMMARY] Starting generation for task {task_id}")
            logger.info(f"[AI SUMMARY] OpenAI module version: {openai.__version__ if hasattr(openai, '__version__') else 'Unknown'}")
            
            # Check if OpenAI API key is configured
            if not openai.api_key:
                logger.error("[AI SUMMARY] OpenAI API key not configured")
                raise Exception("OpenAI API key not configured")
            
            logger.info(f"[AI SUMMARY] API key present: {openai.api_key[:10]}...{openai.api_key[-10:]}")
            
            # Detect OpenAI version and use appropriate syntax
            ai_summary = None
            model_used = None
            
            # Properly detect OpenAI version
            use_old_syntax = False
            if hasattr(openai, '__version__'):
                version = openai.__version__
                major_version = int(version.split('.')[0])
                use_old_syntax = major_version < 1
                logger.info(f"[AI SUMMARY] Detected OpenAI v{version}, major version: {major_version}")
            else:
                # If we can't determine version, try old syntax first
                use_old_syntax = True
                logger.warning("[AI SUMMARY] Cannot detect OpenAI version, trying old syntax first")
            
            if use_old_syntax:
                # Old version (0.28.x)
                logger.info("[AI SUMMARY] Using OpenAI v0.28.x syntax")
                
                try:
                    logger.info("[AI SUMMARY] Attempting GPT-4 with old syntax")
                    response = openai.ChatCompletion.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "You are a professional project manager creating escalation summaries."},
                            {"role": "user", "content": ai_prompt}
                        ],
                        max_tokens=400,
                        temperature=0.7
                    )
                    ai_summary = response.choices[0].message.content.strip()
                    model_used = "gpt-4"
                    logger.info("[AI SUMMARY] GPT-4 succeeded with old syntax")
                    
                except Exception as e:
                    logger.warning(f"[AI SUMMARY] GPT-4 failed with old syntax: {e}")
                    logger.info("[AI SUMMARY] Attempting GPT-4-turbo-preview with old syntax")
                    response = openai.ChatCompletion.create(
                        model="gpt-4-turbo-preview",
                        messages=[
                            {"role": "system", "content": "You are a professional project manager creating escalation summaries."},
                            {"role": "user", "content": ai_prompt}
                        ],
                        max_tokens=400,
                        temperature=0.7
                    )
                    ai_summary = response.choices[0].message.content.strip()
                    model_used = "gpt-4-turbo-preview"
                    logger.info("[AI SUMMARY] GPT-4-turbo-preview succeeded with old syntax")
                    
            else:
                # New version (1.0+)
                logger.info("[AI SUMMARY] Using OpenAI v1.0+ syntax")
                try:
                    from openai import OpenAI
                    # Try to create client - this might fail with httpx version issues
                    try:
                        client = OpenAI(api_key=openai.api_key)
                    except TypeError as te:
                        if 'proxies' in str(te):
                            logger.error("[AI SUMMARY] httpx version incompatibility detected")
                            logger.error("[AI SUMMARY] This usually means httpx is too old for openai v1.0+")
                            logger.error("[AI SUMMARY] Falling back to old syntax despite v1.0+ being installed")
                            # Force old syntax as fallback
                            raise Exception("httpx incompatibility - forcing old syntax")
                        else:
                            raise
                    
                    try:
                        logger.info("[AI SUMMARY] Attempting GPT-4 with new syntax")
                        response = client.chat.completions.create(
                            model="gpt-4",
                            messages=[
                                {"role": "system", "content": "You are a professional project manager creating escalation summaries."},
                                {"role": "user", "content": ai_prompt}
                            ],
                            max_tokens=400,
                            temperature=0.7
                        )
                        ai_summary = response.choices[0].message.content.strip()
                        model_used = "gpt-4"
                        logger.info("[AI SUMMARY] GPT-4 succeeded with new syntax")
                        
                    except Exception as e:
                        logger.warning(f"[AI SUMMARY] GPT-4 failed with new syntax: {e}")
                        logger.info("[AI SUMMARY] Attempting GPT-4-turbo-preview with new syntax")
                        response = client.chat.completions.create(
                            model="gpt-4-turbo-preview",
                            messages=[
                                {"role": "system", "content": "You are a professional project manager creating escalation summaries."},
                                {"role": "user", "content": ai_prompt}
                            ],
                            max_tokens=400,
                            temperature=0.7
                        )
                        ai_summary = response.choices[0].message.content.strip()
                        model_used = "gpt-4-turbo-preview"
                        logger.info("[AI SUMMARY] GPT-4-turbo-preview succeeded with new syntax")
                        
                except Exception as new_syntax_error:
                    logger.error(f"[AI SUMMARY] New syntax completely failed: {new_syntax_error}")
                    logger.info("[AI SUMMARY] Attempting old syntax as emergency fallback")
                    
                    # Emergency fallback to old syntax even though we detected v1.0+
                    try:
                        response = openai.ChatCompletion.create(
                            model="gpt-4",
                            messages=[
                                {"role": "system", "content": "You are a professional project manager creating escalation summaries."},
                                {"role": "user", "content": ai_prompt}
                            ],
                            max_tokens=400,
                            temperature=0.7
                        )
                        ai_summary = response.choices[0].message.content.strip()
                        model_used = "gpt-4-emergency"
                        logger.info("[AI SUMMARY] Emergency old syntax succeeded")
                    except:
                        # Re-raise the original error
                        raise new_syntax_error
            
            return jsonify({
                "success": True,
                "summary": ai_summary,
                "generated_at": datetime.now().isoformat(),
                "task_id": task_id,
                "model_used": model_used
            })
            
        except Exception as openai_error:
            logger.error(f"[AI SUMMARY] Complete OpenAI failure: {openai_error}")
            logger.error(f"[AI SUMMARY] Error type: {type(openai_error).__name__}")
            logger.error(f"[AI SUMMARY] Error details: {str(openai_error)}")
            
            # Return error - no mock data
            return jsonify({
                "success": False,
                "error": "AI service temporarily unavailable. Please try again later.",
                "technical_error": str(openai_error),
                "task_id": task_id,
                "openai_version": openai.__version__ if hasattr(openai, '__version__') else 'Unknown'
            }), 503
        
    except Exception as e:
        logger.error(f"Error generating AI summary: {e}")
        
        # Return error - no mock data
        return jsonify({
            "success": False,
            "error": "Failed to generate AI summary. Please try again later.",
            "technical_error": str(e)
        }), 500


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
    logger.info(f"Secure page access: wait-node-v2 by {session.get('user', {}).get('email', 'Unknown')}")
    
    # Render the template - query parameters are automatically available in the template
    return render_template('secured/wait-node-v2.html')


@app.route('/pages/wait-node-editable')
@login_required
@rate_limiter.rate_limit(limit='100 per hour')
def serve_wait_node_editable():
    """
    Serve wait-node-editable page with edit capabilities
    OAuth protected page for editing Process Library steps
    """
    # Log page access for security audit
    logger.info(f"Secure page access: wait-node-editable by {session.get('user', {}).get('email', 'Unknown')}")
    
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
    logger.info(f"Secure page access: task-helper by {session.get('user', {}).get('email', 'Unknown')}")
    
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
    logger.info(f"Secure page access: wait-node by {session.get('user', {}).get('email', 'Unknown')}")
    
    return render_template('secured/wait-node.html')


@app.route('/pages/health')
def pages_health():
    """Health check for secure pages - no auth required"""
    return jsonify({
        'status': 'healthy',
        'pages_available': True,
        'pages': ['wait-node', 'wait-node-v2', 'wait-node-editable', 'task-helper']
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