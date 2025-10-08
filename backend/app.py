"""
SECURITY NOTICE: This file imports app_secure.py
The actual application logic is in app_secure.py for security.
This file exists only for backward compatibility with deployment configs.
"""

# Import the secure app
from app_secure import app

# This allows Render.com to run: gunicorn app:app
# But actually uses the secure implementation

if __name__ == '__main__':
    print("⚠️  WARNING: Running through app.py wrapper")
    print("✅ Using secure implementation from app_secure.py")
    app.run(debug=False, host='0.0.0.0', port=5678)