from flask import Flask, send_file, request, Response
from flask_cors import CORS
import os

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # Enable CORS for all routes

@app.route('/')
def serve_wait_node():
    # Get the task_id from URL parameters
    task_id = request.args.get('task_id', '868fjk6e5')
    
    # Read the HTML file and serve it with proper headers
    with open('waitNodeSep14.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    return Response(html_content, mimetype='text/html', headers={
        'Content-Type': 'text/html; charset=utf-8',
        'X-Content-Type-Options': 'nosniff',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    })

@app.route('/waitNodeSep14.html')
def serve_wait_node_direct():
    with open('waitNodeSep14.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    return Response(html_content, mimetype='text/html', headers={
        'Content-Type': 'text/html; charset=utf-8',
        'X-Content-Type-Options': 'nosniff',
        'Cache-Control': 'no-cache, no-store, must-revalidate'
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    print("Flask server starting...")
    print("="*50)
    print("\nAccess the page at:")
    print("  → http://127.0.0.1:5000/?task_id=868fjk6e5")
    print("\nOr use any task_id:")
    print("  → http://127.0.0.1:5000/?task_id=YOUR_TASK_ID")
    print("\nPress Ctrl+C to stop the server")
    print("="*50 + "\n")
    
    # Run on 127.0.0.1 instead of localhost to avoid permission issues
    app.run(host='127.0.0.1', port=5000, debug=False)