#!/usr/bin/env python3
import http.server
import socketserver
import os
from urllib.parse import urlparse, parse_qs

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Parse the URL
        parsed_path = urlparse(self.path)
        
        # If requesting root or the HTML file directly
        if parsed_path.path == '/' or parsed_path.path == '/waitNodeSep14.html':
            # Serve the HTML file
            self.path = '/waitNodeSep14.html'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        else:
            # Serve other files normally
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
    
    def end_headers(self):
        # Add CORS headers to allow cross-origin requests
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        http.server.SimpleHTTPRequestHandler.end_headers(self)

# Change to the directory containing the HTML file
os.chdir('/Users/AIRBNB/Task-Specific-Pages')

PORT = 8080
Handler = MyHTTPRequestHandler

print("\n" + "="*60)
print("Simple HTTP Server Starting...")
print("="*60)
print("\nServer running on port", PORT)
print("\nAccess the wait node page at:")
print(f"  → http://localhost:{PORT}/?task_id=868fjk6e5")
print(f"  → http://127.0.0.1:{PORT}/?task_id=868fjk6e5")
print("\nOr use any task_id:")
print(f"  → http://localhost:{PORT}/?task_id=YOUR_TASK_ID")
print("\nPress Ctrl+C to stop the server")
print("="*60 + "\n")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()