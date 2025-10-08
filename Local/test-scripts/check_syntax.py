#!/usr/bin/env python3
import re

with open('backend/templates/secured/wait-node-editable.html', 'r') as f:
    content = f.read()
    
# Extract the JSX part
match = re.search(r'{% raw %}(.*?){% endraw %}', content, re.DOTALL)
if match:
    jsx = match.group(1)
    print(f'Found JSX content: {len(jsx)} characters')
    
    # Find the RightPanel function
    panel_start = jsx.find('function RightPanel')
    if panel_start != -1:
        # Find the end of RightPanel (next function or end)
        next_func = jsx.find('function ', panel_start + 10)
        panel_code = jsx[panel_start:next_func] if next_func != -1 else jsx[panel_start:]
        
        # Count div tags
        open_divs = panel_code.count('<div')
        close_divs = panel_code.count('</div>')
        
        print(f'RightPanel component:')
        print(f'  Opening <div> tags: {open_divs}')
        print(f'  Closing </div> tags: {close_divs}')
        print(f'  Balance: {open_divs - close_divs}')
        
        if open_divs != close_divs:
            print('  WARNING: UNBALANCED DIVS!')
        else:
            print('  OK: Divs are balanced')