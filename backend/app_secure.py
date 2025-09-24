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

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

# Import security modules
from config.security import SecureConfig
from auth.oauth_handler import auth_bp, init_redis, login_required
from auth.security_middleware import SecurityMiddleware, RateLimiter

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        logger.info(f"Task escalation requested for {task_id} by {request.user.get('email')}")

        # TODO: Add actual escalation logic here
        # 1. Update task custom fields with escalation data
        # 2. Add "escalated" tag to task  
        # 3. Create notification/comment
        # 4. Send notification (SMS/email/Slack)
        
        # For now, return success response
        # In real implementation, you would:
        # - Update ESCALATION_STATUS field to "escalated" 
        # - Set ESCALATION_AI_SUMMARY field to ai_summary
        # - Set ESCALATION_TIMESTAMP to current time
        # - Add escalation comment to task
        
        response_data = {
            "success": True,
            "message": "Task escalated successfully",
            "escalation_id": f"ESC-{task_id}-{int(datetime.now().timestamp())}",
            "task_id": task_id,
            "escalated_by": request.user.get('email'),
            "escalation_data": {
                "reason": escalation_reason,
                "ai_summary": ai_summary,
                "context": task_context,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error escalating task {task_id}: {e}")
        return jsonify({"error": f"Failed to escalate task: {str(e)}"}), 500


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
        logger.info(f"AI summary generation requested for task {task_id} by {request.user.get('email')}")

        # TODO: Implement actual AI integration here
        # This is a placeholder that generates a mock summary
        # In real implementation, you would:
        # 1. Format task context for AI prompt
        # 2. Call OpenAI API with structured prompt
        # 3. Process and validate AI response
        # 4. Return formatted summary
        
        # Mock AI summary for now
        mock_summary = f"""**ESCALATION SUMMARY**

**Task**: {context.get('task', {}).get('name', 'Unknown Task')} ({task_id})
**Escalated by**: {request.user.get('email')}

**Issue Description**: {reason}

**Task Context**:
- Status: {context.get('task', {}).get('status', {}).get('status', 'Unknown')}
- Assignees: {', '.join([a.get('username', 'Unknown') for a in context.get('task', {}).get('assignees', [])])}
- Parent Task: {context.get('parent_task', {}).get('name', 'None')}
- Subtasks: {len(context.get('subtasks', []))} total

**Recommended Action**: Review task context and provide guidance on next steps.

**Priority**: Moderate - Requires attention within 24 hours

*This summary was generated by AI to help prioritize and understand the escalation context.*"""

        return jsonify({
            "success": True,
            "summary": mock_summary,
            "generated_at": datetime.now().isoformat(),
            "task_id": task_id,
            "model_used": "mock-gpt-4" # In real implementation: "gpt-4" or similar
        })
        
    except Exception as e:
        logger.error(f"Error generating AI summary: {e}")
        return jsonify({"error": f"Failed to generate summary: {str(e)}"}), 500


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