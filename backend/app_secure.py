"""
Secure Flask backend server with Google OAuth authentication
Handles ClickUp API interactions with authentication and security
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, session
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
redis_client = init_redis(app)

# Configure Flask-Session with Redis
app.config['SESSION_REDIS'] = redis_client
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
    
    def update_custom_field(self, task_id: str, field_id: str, value: Any) -> Dict[str, Any]:
        """Update a custom field on a task"""
        url = f"{CLICKUP_BASE_URL}/task/{task_id}/field/{field_id}"
        data = {"value": value}
        
        response = requests.post(url, headers=self.headers, json=data, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Failed to update field {field_id} on task {task_id}: {response.text}")
            response.raise_for_status()
        
        return response.json()
    
    def find_process_library_root(self, start_task_id: str) -> Optional[Dict[str, Any]]:
        """Find the top-level Process Library parent task"""
        current_task = self.get_task(start_task_id, custom_task_ids=True)
        last_process_library_task = None
        
        # If the starting task is a Process Library task, include it
        if current_task.get('custom_item_id') == PROCESS_LIBRARY_TYPE:
            last_process_library_task = current_task
        
        # Traverse up the parent chain
        while current_task.get('parent'):
            logger.info(f"Checking task {current_task['id']} (type: {current_task.get('custom_item_id')})")
            
            parent_task = self.get_task(current_task['parent'], custom_task_ids=True)
            
            if parent_task.get('custom_item_id') == PROCESS_LIBRARY_TYPE:
                # This parent is still a Process Library task
                last_process_library_task = parent_task
                current_task = parent_task
            else:
                # This parent is NOT a Process Library task, so we stop
                logger.info(f"Found non-Process Library parent: {parent_task['id']}")
                break
        
        logger.info(f"Process Library root found: {last_process_library_task.get('id') if last_process_library_task else None}")
        return last_process_library_task
    
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
        
        # Find process library root
        root_task = clickup_service.find_process_library_root(task_id)
        if not root_task:
            return jsonify({"error": "Could not find Process Library root task"}), 404
        
        # Get wait task details
        wait_task = clickup_service.get_task(task_id, custom_task_ids=True)
        
        # Get all subtasks
        subtasks = clickup_service.fetch_subtasks_with_details(root_task['id'])
        
        return jsonify({
            "root_task": root_task,
            "wait_task": wait_task,
            "subtasks": subtasks
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