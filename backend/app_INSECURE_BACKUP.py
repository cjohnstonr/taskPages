"""
Flask backend server for Wait Node API
Handles all ClickUp API interactions for the wait-node.html frontend
"""

import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_session import Session
from dotenv import load_dotenv
import requests
from typing import Dict, Any, Optional, List
import asyncio
from concurrent.futures import ThreadPoolExecutor
from auth.oauth_handler import auth_bp, init_redis
from config.security import SecureConfig

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app with secure config
app = Flask(__name__)
SecureConfig.init_app(app)

# Initialize Redis for sessions
try:
    redis_client = init_redis(app)
    if redis_client:
        app.config['SESSION_REDIS'] = redis_client
except Exception as e:
    logger.warning(f"Redis initialization failed: {e}")
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = '/tmp/flask_sessions'

# Initialize Flask-Session
Session(app)

# Configure CORS with secure settings
CORS(app, 
    origins=SecureConfig.CORS_ORIGINS,
    supports_credentials=SecureConfig.CORS_SUPPORTS_CREDENTIALS,
    methods=SecureConfig.CORS_METHODS,
    allow_headers=SecureConfig.CORS_ALLOW_HEADERS,
    max_age=SecureConfig.CORS_MAX_AGE
)

# Register auth blueprint
app.register_blueprint(auth_bp)

# Configuration
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
    'LIBRARY_LEVEL': 'e49ccff6-f042-4e47-b452-0812ba128cfb',
    # MCP Fields
    'MCP_NAME': '5e2e416b-7ee8-4984-859b-c70c86c4d042',
    'MCP_EXPECTED_ACTION': '56db1b14-75cb-42d9-bd38-45362d974516',
    'MCP_TEST_TOOL': '9aa9b4c3-379a-44d4-a299-a697ee510287',
    'MCP_TEST_TYPE': 'a8e7648a-19b9-425f-8f88-a65a0fc4c60b',
    'MCP_TEST_RESULT': '1902f823-0326-43fb-bc75-4ceaa562c0cd'
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
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code != 200:
            logger.error(f"Failed to get task {task_id}: {response.text}")
            response.raise_for_status()
        
        return response.json()
    
    def update_custom_field(self, task_id: str, field_id: str, value: Any) -> Dict[str, Any]:
        """Update a custom field on a task"""
        url = f"{CLICKUP_BASE_URL}/task/{task_id}/field/{field_id}"
        data = {"value": value}
        
        response = requests.post(url, headers=self.headers, json=data)
        
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
    
    def find_main_parent_task(self, start_task_id: str) -> Optional[Dict[str, Any]]:
        """Find the ultimate parent task (the main business task)"""
        current_task = self.get_task(start_task_id, custom_task_ids=True)
        
        # Traverse up to find the top-most parent
        while current_task.get('parent'):
            logger.info(f"Traversing up from {current_task['id']} to parent {current_task['parent']}")
            current_task = self.get_task(current_task['parent'], custom_task_ids=True)
        
        logger.info(f"Main parent task found: {current_task['id']} - {current_task.get('name')}")
        return current_task
    
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
    
    def fetch_task_comments(self, task_id: str, start: int = 0, limit: int = 20) -> Dict[str, Any]:
        """Fetch comments for a task with pagination"""
        url = f"{CLICKUP_BASE_URL}/task/{task_id}/comment"
        params = {
            "start": start,
            "limit": limit
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code != 200:
            logger.error(f"Failed to get comments for task {task_id}: {response.text}")
            response.raise_for_status()
        
        data = response.json()
        comments = data.get('comments', [])
        
        # Normalize comments
        normalized_comments = self.normalize_comments(comments)
        
        return {
            "comments": normalized_comments,
            "has_more": len(comments) >= limit
        }
    
    def normalize_comments(self, raw_comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize comment data for consistent format"""
        normalized = []
        
        for comment in raw_comments:
            # Skip bot and system comments by default
            username = comment.get('user', {}).get('username', '')
            if 'bot' in username.lower() or comment.get('type') == 'system':
                continue
                
            normalized.append({
                'id': comment.get('id'),
                'text': comment.get('comment_text', ''),
                'user': {
                    'id': comment.get('user', {}).get('id'),
                    'username': comment.get('user', {}).get('username', 'Unknown'),
                    'email': comment.get('user', {}).get('email', ''),
                    'initials': comment.get('user', {}).get('initials', 
                                          comment.get('user', {}).get('username', 'U')[0:2].upper()),
                    'color': comment.get('user', {}).get('color', '#808080')
                },
                'date': comment.get('date'),
                'date_formatted': self.format_relative_time(comment.get('date')),
                'resolved': comment.get('resolved', False),
                'assignee': comment.get('assignee'),
                'reactions': comment.get('reactions', [])
            })
        
        return normalized
    
    def format_relative_time(self, timestamp: str) -> str:
        """Format timestamp as relative time (e.g., '2 hours ago')"""
        if not timestamp:
            return 'Unknown'
        
        try:
            import time
            from datetime import datetime
            
            # Convert timestamp to datetime
            comment_time = datetime.fromtimestamp(int(timestamp) / 1000)
            now = datetime.now()
            
            diff = now - comment_time
            
            if diff.days > 7:
                return comment_time.strftime('%b %d, %Y')
            elif diff.days > 0:
                return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                return "Just now"
        except Exception as e:
            logger.error(f"Error formatting time: {e}")
            return 'Unknown'


# Initialize service
clickup_service = ClickUpService()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "wait-node-backend"})


@app.route('/api/wait-node/initialize/<task_id>', methods=['GET'])
def initialize_wait_node(task_id):
    """
    Combined endpoint to fetch all necessary data for wait node interface
    Returns root task, wait task, main parent task, and all subtasks in a single response
    """
    try:
        logger.info(f"Initializing wait node for task: {task_id}")
        
        # Check if comments should be included
        include_comments = request.args.get('include_comments', 'true').lower() == 'true'
        
        # Find process library root
        root_task = clickup_service.find_process_library_root(task_id)
        if not root_task:
            return jsonify({"error": "Could not find Process Library root task"}), 404
        
        # Get wait task details
        wait_task = clickup_service.get_task(task_id, custom_task_ids=True)
        
        # Get main parent task (the ultimate business task)
        main_task = clickup_service.find_main_parent_task(task_id)
        
        # Get all subtasks
        subtasks = clickup_service.fetch_subtasks_with_details(root_task['id'])
        
        # Get initial comments for main task if requested
        main_task_comments = None
        if include_comments and main_task:
            try:
                main_task_comments = clickup_service.fetch_task_comments(
                    main_task['id'], 
                    start=0, 
                    limit=10
                )
            except Exception as e:
                logger.error(f"Failed to fetch comments for main task: {e}")
                main_task_comments = {"comments": [], "has_more": False}
        
        return jsonify({
            "root_task": root_task,
            "wait_task": wait_task,
            "main_task": main_task,
            "subtasks": subtasks,
            "main_task_comments": main_task_comments
        })
    
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error in initialize_wait_node: {e}")
        return jsonify({"error": str(e)}), e.response.status_code if e.response else 500
    except Exception as e:
        logger.error(f"Error in initialize_wait_node: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/wait-node/approve/<task_id>', methods=['POST'])
def approve_task(task_id):
    """
    Handle approval submission
    Updates multiple custom fields and returns verified task data
    """
    try:
        approval_data = request.json
        logger.info(f"Processing approval for task {task_id} with data: {approval_data}")
        
        if not approval_data:
            return jsonify({"error": "No approval data provided"}), 400
        
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
        
        return jsonify({
            "success": True,
            "task": verified_task,
            "updates": results
        })
    
    except Exception as e:
        logger.error(f"Error in approve_task: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/task/<task_id>', methods=['GET'])
def get_task(task_id):
    """Get task details"""
    try:
        custom_task_ids = request.args.get('custom_task_ids', 'false').lower() == 'true'
        include_subtasks = request.args.get('include_subtasks', 'false').lower() == 'true'
        
        task = clickup_service.get_task(task_id, custom_task_ids, include_subtasks)
        return jsonify(task)
    
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": str(e)}), e.response.status_code if e.response else 500
    except Exception as e:
        logger.error(f"Error in get_task: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/task/<task_id>/process-root', methods=['GET'])
def get_process_root(task_id):
    """Find process library root for a task"""
    try:
        root_task = clickup_service.find_process_library_root(task_id)
        if not root_task:
            return jsonify({"error": "Process library root not found"}), 404
        return jsonify(root_task)
    
    except Exception as e:
        logger.error(f"Error in get_process_root: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/task/<task_id>/subtasks-detailed', methods=['GET'])
def get_subtasks_detailed(task_id):
    """Get all subtasks with details"""
    try:
        subtasks = clickup_service.fetch_subtasks_with_details(task_id)
        return jsonify({"subtasks": subtasks})
    
    except Exception as e:
        logger.error(f"Error in get_subtasks_detailed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/task/<task_id>/field/<field_id>', methods=['PUT'])
def update_field(task_id, field_id):
    """Update a single custom field"""
    try:
        data = request.json
        if 'value' not in data:
            return jsonify({"error": "Value is required"}), 400
        
        result = clickup_service.update_custom_field(task_id, field_id, data['value'])
        return jsonify(result)
    
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": str(e)}), e.response.status_code if e.response else 500
    except Exception as e:
        logger.error(f"Error in update_field: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/task/<task_id>/comments', methods=['GET'])
def get_task_comments(task_id):
    """Get comments for a task with pagination"""
    try:
        start = int(request.args.get('start', 0))
        limit = int(request.args.get('limit', 20))
        
        comments_data = clickup_service.fetch_task_comments(task_id, start, limit)
        return jsonify(comments_data)
    
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error in get_task_comments: {e}")
        return jsonify({"error": str(e)}), e.response.status_code if e.response else 500
    except Exception as e:
        logger.error(f"Error in get_task_comments: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Check for required environment variables
    if not CLICKUP_API_KEY:
        print("ERROR: CLICKUP_API_KEY environment variable is required!")
        print("Please create a .env file with your ClickUp API key")
        exit(1)
    
    print(f"Starting Flask server...")
    print(f"Team ID: {CLICKUP_TEAM_ID}")
    print(f"Server running at: http://localhost:5678")
    print(f"Health check: http://localhost:5678/health")
    
    app.run(host='0.0.0.0', port=5678, debug=True)