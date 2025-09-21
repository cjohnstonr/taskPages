#!/usr/bin/env python3
"""
Comprehensive analysis of the right panel functionality
"""

import re

def analyze_right_panel():
    with open('backend/templates/secured/wait-node-editable.html', 'r') as f:
        content = f.read()
    
    print("=" * 60)
    print("RIGHT PANEL ANALYSIS")
    print("=" * 60)
    
    # 1. Check state initialization
    print("\n1. STATE INITIALIZATION:")
    state_pattern = r'const \[selectedStepForEdit.*?\].*?useState\((.*?)\)'
    match = re.search(state_pattern, content)
    if match:
        print(f"   selectedStepForEdit initialized with: {match.group(1)}")
    else:
        print("   ❌ Could not find selectedStepForEdit state")
    
    # 2. Check ProcessStepsAccordion props
    print("\n2. PROCESSSTEPSACCORDION PROPS:")
    accordion_pattern = r'<ProcessStepsAccordion\s+([\s\S]*?)/>'
    match = re.search(accordion_pattern, content)
    if match:
        props = match.group(1)
        if 'onEditStep' in props:
            print("   ✅ onEditStep prop is passed")
            # Extract the function
            edit_func = re.search(r'onEditStep=\{([\s\S]*?)\}\}', props)
            if edit_func:
                print(f"   Function content: {edit_func.group(1)[:100]}...")
        else:
            print("   ❌ onEditStep prop NOT passed")
        
        if 'selectedStepId' in props:
            print("   ✅ selectedStepId prop is passed")
        else:
            print("   ⚠️  selectedStepId prop NOT passed")
    
    # 3. Check Edit button in accordion
    print("\n3. EDIT BUTTON IN ACCORDION:")
    button_pattern = r'libraryLevel.*?onEditStep.*?<button([\s\S]*?)>.*?Edit.*?</button>'
    match = re.search(button_pattern, content)
    if match:
        print("   ✅ Edit button found")
        if 'onClick' in match.group(1):
            print("   ✅ onClick handler present")
            onclick = re.search(r'onClick=\{(.*?)\}', match.group(1))
            if onclick and 'onEditStep' in onclick.group(1):
                print("   ✅ onClick calls onEditStep")
    else:
        print("   ❌ Edit button NOT found or improperly configured")
    
    # 4. Check RightPanel rendering
    print("\n4. RIGHTPANEL RENDERING:")
    panel_pattern = r'\{selectedStepForEdit\s*&&\s*\(([\s\S]*?)<RightPanel'
    match = re.search(panel_pattern, content)
    if match:
        print("   ✅ RightPanel conditional rendering found")
        print("   Condition: {selectedStepForEdit && (")
    else:
        print("   ❌ RightPanel conditional rendering NOT found")
    
    # 5. Check RightPanel props
    print("\n5. RIGHTPANEL PROPS:")
    rightpanel_pattern = r'<RightPanel\s+([\s\S]*?)/>'
    match = re.search(rightpanel_pattern, content)
    if match:
        props = match.group(1)
        required_props = ['step', 'onClose', 'width', 'onResize', 'onStepDeleted']
        for prop in required_props:
            if prop in props:
                print(f"   ✅ {prop} prop is passed")
            else:
                print(f"   ❌ {prop} prop is MISSING")
    
    # 6. Check RightPanel function
    print("\n6. RIGHTPANEL FUNCTION:")
    func_pattern = r'function RightPanel\(\{([^}]*)\}\)'
    match = re.search(func_pattern, content)
    if match:
        params = match.group(1)
        print(f"   Parameters: {params}")
        if 'isOpen' in params:
            print("   ⚠️  WARNING: isOpen parameter still present!")
    
    # 7. Check RightPanel return condition
    print("\n7. RIGHTPANEL RETURN CONDITION:")
    return_pattern = r'function RightPanel[\s\S]*?if\s*\((.*?)\)\s*return\s*null'
    match = re.search(return_pattern, content)
    if match:
        condition = match.group(1)
        print(f"   Return null condition: {condition}")
        if 'isOpen' in condition:
            print("   ❌ ERROR: Still checking isOpen!")
        if '!step' in condition:
            print("   ✅ Checking !step")
    
    # 8. Check for multiple RightPanel definitions
    print("\n8. MULTIPLE DEFINITIONS CHECK:")
    count = content.count('function RightPanel')
    print(f"   Number of RightPanel definitions: {count}")
    if count > 1:
        print("   ⚠️  WARNING: Multiple definitions found!")
    
    # 9. Check getRelevantCustomFields function
    print("\n9. HELPER FUNCTIONS:")
    if 'getRelevantCustomFields' in content:
        print("   ✅ getRelevantCustomFields function exists")
    else:
        print("   ❌ getRelevantCustomFields function missing")
    
    # 10. Check for console errors in the code
    print("\n10. POTENTIAL ISSUES:")
    if 'window.selectedStepForEdit' in content:
        print("   ⚠️  Found window.selectedStepForEdit - should use state/props")
    if content.count('<div') != content.count('</div>'):
        print("   ⚠️  Possible unbalanced div tags")
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    analyze_right_panel()