#!/usr/bin/env python3
"""Fix Jinja2 template syntax conflicts in HTML files.

The issue: React/JSX style={{}} syntax conflicts with Jinja2's {{}} template syntax.
Solution: Wrap JavaScript sections in {% raw %} ... {% endraw %} blocks.
"""

import re
import sys

def fix_template_file(filepath):
    """Fix Jinja2 template syntax conflicts in a single file."""
    print(f"Processing {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find all script tags and wrap their content in raw blocks
    def wrap_script_content(match):
        script_tag = match.group(1)
        script_content = match.group(2)
        closing_tag = match.group(3)
        
        # Don't wrap if already wrapped
        if '{% raw %}' in script_content:
            return match.group(0)
        
        # Wrap the script content in raw blocks
        return f'{script_tag}\n{{% raw %}}\n{script_content}\n{{% endraw %}}\n{closing_tag}'
    
    # Pattern to match script tags with content
    script_pattern = r'(<script[^>]*>)(.*?)(</script>)'
    
    # Replace all script content with wrapped version
    content = re.sub(script_pattern, wrap_script_content, content, flags=re.DOTALL)
    
    # Save the fixed content
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed {filepath}")

def main():
    """Main function to fix both template files."""
    files_to_fix = [
        '/Users/AIRBNB/Task-Specific-Pages/backend/templates/secured/wait-node.html',
        '/Users/AIRBNB/Task-Specific-Pages/backend/templates/secured/wait-node-v2.html'
    ]
    
    for filepath in files_to_fix:
        try:
            fix_template_file(filepath)
        except Exception as e:
            print(f"❌ Error fixing {filepath}: {e}")
            return 1
    
    print("\n✅ All templates fixed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())