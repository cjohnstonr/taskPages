#!/usr/bin/env python3
"""
Find ALL code related to the right panel editing functionality
"""

import re

def find_all_editing_code():
    with open('backend/templates/secured/wait-node-editable.html', 'r') as f:
        lines = f.readlines()
    
    print("=" * 80)
    print("COMPLETE ANALYSIS OF RIGHT PANEL EDITING CODE")
    print("=" * 80)
    
    findings = {
        "RightPanel Component": [],
        "selectedStepForEdit State": [],
        "Edit Button": [],
        "Panel Rendering": [],
        "Conditional Logic": [],
        "onEditStep Handler": [],
        "Panel Props": [],
        "Width Management": []
    }
    
    for i, line in enumerate(lines, 1):
        # RightPanel component definition
        if 'function RightPanel' in line:
            findings["RightPanel Component"].append(f"Line {i}: RightPanel function definition")
        
        # selectedStepForEdit state
        if 'selectedStepForEdit' in line:
            findings["selectedStepForEdit State"].append(f"Line {i}: {line.strip()[:100]}")
        
        # Edit button
        if 'Edit' in line and ('button' in line or 'onClick' in line):
            findings["Edit Button"].append(f"Line {i}: {line.strip()[:100]}")
        
        # Panel rendering (the conditional part)
        if 'RightPanel' in line and '<' in line:
            findings["Panel Rendering"].append(f"Line {i}: {line.strip()[:100]}")
        
        # Conditional rendering
        if ('selectedStepForEdit &&' in line or 
            'selectedStepForEdit ?' in line or
            '!step) return null' in line):
            findings["Conditional Logic"].append(f"Line {i}: {line.strip()[:100]}")
        
        # onEditStep handler
        if 'onEditStep' in line:
            findings["onEditStep Handler"].append(f"Line {i}: {line.strip()[:100]}")
        
        # Width management
        if 'rightPanelWidth' in line or 'panelWidth' in line:
            findings["Width Management"].append(f"Line {i}: {line.strip()[:100]}")
    
    # Print findings
    for category, items in findings.items():
        if items:
            print(f"\n{category}:")
            print("-" * 40)
            for item in items[:10]:  # Show first 10 of each
                print(f"  {item}")
            if len(items) > 10:
                print(f"  ... and {len(items) - 10} more")
    
    # Find the specific problem areas
    print("\n" + "=" * 80)
    print("CRITICAL ISSUES TO FIX:")
    print("=" * 80)
    
    # Find the conditional rendering
    for i, line in enumerate(lines, 1):
        if '{selectedStepForEdit &&' in line:
            print(f"\n❌ Line {i}: CONDITIONAL RENDERING OF PANEL")
            print(f"   Current: {line.strip()}")
            print(f"   Should be: Always render the panel, handle empty state inside")
        
        if '!step) return null' in line:
            print(f"\n❌ Line {i}: RETURNING NULL IN RIGHTPANEL")
            print(f"   Current: {line.strip()}")
            print(f"   Should be: Show empty state instead of returning null")
    
    print("\n" + "=" * 80)
    print("RECOMMENDED CHANGES:")
    print("=" * 80)
    print("""
1. Line 2897: Remove conditional rendering
   FROM: {selectedStepForEdit && (
   TO:   Always render <RightPanel step={selectedStepForEdit} ...

2. Line 2216: Remove return null in RightPanel
   FROM: if (!step) return null;
   TO:   Show empty state when !step

3. Line 2862-2866: Simplify onEditStep
   FROM: Toggle logic
   TO:   Simple setSelectedStepForEdit(step)

4. Make panel structure:
   - Always visible third column
   - Fixed width (resizable)
   - Empty state when no step selected
   - Content when step selected
""")

if __name__ == "__main__":
    find_all_editing_code()