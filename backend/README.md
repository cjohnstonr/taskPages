# Wait Node Backend Server

Flask backend server that handles ClickUp API interactions for the wait-node.html frontend.

## Features

- ✅ Secure API key management (backend-only)
- ✅ Parallel API requests for better performance
- ✅ CORS configured for local development
- ✅ Comprehensive error handling
- ✅ Health check endpoint
- ✅ Thread pooling for concurrent operations

## Setup Instructions

### 1. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the backend directory:

```bash
cp .env.example .env
```

Edit `.env` and add your ClickUp API key:
```env
CLICKUP_API_KEY=your_actual_clickup_api_key_here
CLICKUP_TEAM_ID=9011954126
```

To get your ClickUp API key:
1. Go to https://app.clickup.com/settings/apps
2. Click on "Apps" in the left sidebar
3. Generate a personal API token

### 3. Run the Server

```bash
python app.py
```

The server will start on `http://localhost:8000`

### 4. Test the Server

Check if the server is running:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "wait-node-backend"
}
```

## API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/wait-node/initialize/<task_id>` | GET | Initialize wait node with all data |
| `/api/wait-node/approve/<task_id>` | POST | Submit approval and update fields |

### Additional Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/task/<task_id>` | GET | Get task details |
| `/api/task/<task_id>/process-root` | GET | Find process library root |
| `/api/task/<task_id>/subtasks-detailed` | GET | Get all subtasks with details |
| `/api/task/<task_id>/field/<field_id>` | PUT | Update single custom field |

## Testing with the Frontend

1. Open `wait-node copy.html` in your browser
2. Make sure the backend server is running on port 8000
3. The frontend will automatically connect to `http://localhost:8000`
4. Add `?task_id=YOUR_TASK_ID` to the URL to test with a specific task

## Example API Usage

### Initialize Wait Node
```bash
curl http://localhost:8000/api/wait-node/initialize/YOUR_TASK_ID
```

### Submit Approval
```bash
curl -X POST http://localhost:8000/api/wait-node/approve/YOUR_TASK_ID \
  -H "Content-Type: application/json" \
  -d '{
    "field_id_1": "value1",
    "field_id_2": "value2"
  }'
```

## Development

### Debug Mode
The server runs in debug mode by default for development. To disable:
```python
app.run(host='0.0.0.0', port=8000, debug=False)
```

### Logging
Logs are output to console. Check for:
- API request details
- Error messages
- Task processing information

### Performance
- Uses ThreadPoolExecutor for parallel API calls
- Fetches subtasks concurrently (10 workers)
- Updates fields in parallel during approval

## Production Deployment

For production, use a WSGI server like Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## Troubleshooting

### CORS Issues
If you get CORS errors, make sure the frontend URL is included in the CORS origins list in `app.py`:
```python
CORS(app, origins=["http://localhost:*", "http://127.0.0.1:*", "file://*"])
```

### API Key Issues
- Verify your API key is correct in `.env`
- Check ClickUp API key permissions
- Ensure the key has access to the specified team

### Connection Issues
- Verify the server is running on port 8000
- Check firewall settings
- Ensure no other service is using port 8000

## Security Notes

- Never commit `.env` file to version control
- API keys are stored server-side only
- All ClickUp requests go through the backend
- Consider adding authentication for production use