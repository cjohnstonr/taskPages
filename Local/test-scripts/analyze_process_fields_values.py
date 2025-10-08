#!/usr/bin/env python3
"""
Analyze which custom fields have values and are likely Process Library specific
"""

import json
from pathlib import Path

# Load the saved JSON
with open('zprocesslibrarytask.json', 'r') as f:
    task_data = json.load(f)

custom_fields = task_data.get('custom_fields', [])

# Separate fields with values from empty fields
fields_with_values = []
empty_fields = []

for field in custom_fields:
    value = field.get('value')
    if value is not None and value != "" and value != [] and value != {}:
        fields_with_values.append(field)
    else:
        empty_fields.append(field)

print("=" * 80)
print("CUSTOM FIELDS ANALYSIS FOR PROCESS LIBRARY TASK")
print("=" * 80)
print(f"\nTask: {task_data.get('name')}")
print(f"Custom Item ID (Type): {task_data.get('custom_item_id')} (Process Library = 1018)")
print(f"Total Custom Fields: {len(custom_fields)}")
print(f"Fields with values: {len(fields_with_values)}")
print(f"Empty fields: {len(empty_fields)}")

print("\n" + "=" * 80)
print("FIELDS WITH VALUES (Non-null) - LIKELY PROCESS LIBRARY SPECIFIC")
print("=" * 80)

# Group fields with values by type
fields_by_type = {}
for field in fields_with_values:
    field_type = field.get('type', 'unknown')
    if field_type not in fields_by_type:
        fields_by_type[field_type] = []
    fields_by_type[field_type].append(field)

# Process Library specific keywords to look for
process_keywords = ['process', 'library', 'step', 'execute', 'mcp', 'wait', 'ai_proposed', 'human_approved', 'accumulative']

for field_type in sorted(fields_by_type.keys()):
    fields = fields_by_type[field_type]
    print(f"\n### {field_type.upper()} Fields ({len(fields)}):")
    print("-" * 40)
    
    for field in fields:
        name = field.get('name', 'unnamed')
        field_id = field.get('id')
        value = field.get('value')
        
        # Check if field name suggests it's Process Library specific
        is_likely_process_specific = any(keyword in name.lower() for keyword in process_keywords)
        
        # Format value for display
        if isinstance(value, str):
            value_display = value[:100] + "..." if len(value) > 100 else value
            value_display = value_display.replace('\n', ' ')
        elif isinstance(value, list):
            value_display = f"[{len(value)} items]"
        elif isinstance(value, dict):
            value_display = f"{{dict with {len(value)} keys}}"
        elif isinstance(value, bool):
            value_display = str(value)
        else:
            value_display = str(value)
        
        # Mark likely Process Library fields
        marker = "⭐ " if is_likely_process_specific else "   "
        
        print(f"{marker}{name}")
        print(f"    ID: {field_id}")
        print(f"    Value: {value_display}")
        print()

print("\n" + "=" * 80)
print("LIKELY PROCESS LIBRARY SPECIFIC FIELDS (based on naming)")
print("=" * 80)

process_specific_fields = []
for field in fields_with_values:
    name = field.get('name', 'unnamed')
    if any(keyword in name.lower() for keyword in process_keywords):
        process_specific_fields.append(field)

print(f"\nFound {len(process_specific_fields)} likely Process Library specific fields with values:\n")

for field in process_specific_fields:
    name = field.get('name')
    field_type = field.get('type')
    field_id = field.get('id')
    print(f"- {name} ({field_type})")
    print(f"  ID: {field_id}")

# Save analysis to markdown
with open('process_library_fields_analysis.md', 'w') as f:
    f.write("# Process Library Fields Analysis\n\n")
    f.write(f"## Task Information\n")
    f.write(f"- **Task Name:** {task_data.get('name')}\n")
    f.write(f"- **Custom Item ID:** {task_data.get('custom_item_id')} (Process Library = 1018)\n")
    f.write(f"- **Total Custom Fields:** {len(custom_fields)}\n")
    f.write(f"- **Fields with values:** {len(fields_with_values)}\n")
    f.write(f"- **Empty fields:** {len(empty_fields)}\n\n")
    
    f.write("## Fields with Values (Non-null)\n\n")
    f.write("### Likely Process Library Specific Fields\n")
    f.write("*Fields with process/library/step/execute/mcp/wait keywords*\n\n")
    
    for field in process_specific_fields:
        name = field.get('name')
        field_type = field.get('type')
        field_id = field.get('id')
        value = field.get('value')
        
        f.write(f"#### {name}\n")
        f.write(f"- **Type:** {field_type}\n")
        f.write(f"- **Field ID:** `{field_id}`\n")
        
        if isinstance(value, str) and len(value) > 200:
            f.write(f"- **Value:** (truncated) {value[:200]}...\n\n")
        elif isinstance(value, (list, dict)):
            f.write(f"- **Value:** `{json.dumps(value, indent=2)[:500]}`\n\n")
        else:
            f.write(f"- **Value:** `{value}`\n\n")
    
    f.write("\n### Other Fields with Values\n\n")
    f.write("| Field Name | Type | Value Preview |\n")
    f.write("|------------|------|---------------|\n")
    
    for field in fields_with_values:
        if field not in process_specific_fields:
            name = field.get('name', 'unnamed')
            field_type = field.get('type')
            value = field.get('value')
            
            if isinstance(value, str):
                value_display = value[:50] + "..." if len(value) > 50 else value
                value_display = value_display.replace('\n', ' ').replace('|', '\\|')
            elif isinstance(value, list):
                value_display = f"[{len(value)} items]"
            else:
                value_display = str(value)[:50]
            
            f.write(f"| {name} | {field_type} | {value_display} |\n")

print("\n💾 Detailed analysis saved to process_library_fields_analysis.md")