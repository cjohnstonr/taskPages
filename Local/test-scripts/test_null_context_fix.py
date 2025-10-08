#!/usr/bin/env python3
"""
Test that proves the NoneType error was caused by explicit None values in context
"""

def simulate_old_code():
    """Simulate the OLD code that would fail"""
    # Simulating what happens when frontend sends {context: {task: null}}
    data = {'context': {'task': None, 'parent_task': None}}
    
    # OLD CODE (would fail):
    context = data.get('context', {})  # Returns {'task': None, 'parent_task': None}
    task_info = context.get('task', {})  # Returns None (NOT {} because 'task' exists with value None!)
    
    print(f"OLD CODE - context: {context}")
    print(f"OLD CODE - task_info: {task_info}")
    print(f"OLD CODE - task_info type: {type(task_info)}")
    
    try:
        # This would throw: 'NoneType' object has no attribute 'get'
        status = task_info.get('status')
        print(f"OLD CODE - status: {status}")
    except AttributeError as e:
        print(f"OLD CODE - ERROR: {e}")
        return False
    return True

def simulate_new_code():
    """Simulate the NEW fixed code"""
    # Same data from frontend
    data = {'context': {'task': None, 'parent_task': None}}
    
    # NEW CODE (fixed):
    context = data.get('context') or {}  # Returns {'task': None, 'parent_task': None}
    task_info = context.get('task') or {}  # Returns {} because None is falsy
    
    print(f"\nNEW CODE - context: {context}")
    print(f"NEW CODE - task_info: {task_info}")
    print(f"NEW CODE - task_info type: {type(task_info)}")
    
    try:
        # This now works!
        status = task_info.get('status')
        print(f"NEW CODE - status: {status}")
        return True
    except AttributeError as e:
        print(f"NEW CODE - ERROR: {e}")
        return False

def test_edge_cases():
    """Test various edge cases"""
    print("\n=== TESTING EDGE CASES ===")
    
    test_cases = [
        ("No context key", {}),
        ("Context is None", {'context': None}),
        ("Context with None task", {'context': {'task': None}}),
        ("Context with empty task", {'context': {'task': {}}}),
        ("Valid context", {'context': {'task': {'status': {'status': 'todo'}}}}),
    ]
    
    for name, data in test_cases:
        print(f"\nTest: {name}")
        print(f"Data: {data}")
        
        # Using new approach
        context = data.get('context') or {}
        task_info = context.get('task') or {}
        
        print(f"  task_info: {task_info}")
        print(f"  Can call .get()? {hasattr(task_info, 'get')}")
        
        try:
            status = task_info.get('status')
            print(f"  ✅ Success - status: {status}")
        except AttributeError as e:
            print(f"  ❌ Failed: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("DEMONSTRATING THE NONETYPE BUG AND FIX")
    print("=" * 60)
    
    print("\n1. OLD CODE (with bug):")
    old_success = simulate_old_code()
    
    print("\n2. NEW CODE (fixed):")
    new_success = simulate_new_code()
    
    test_edge_cases()
    
    print("\n" + "=" * 60)
    print("CONCLUSION:")
    print("=" * 60)
    if not old_success and new_success:
        print("✅ The fix works! The problem was:")
        print("   - context.get('task', {}) returns None when task is explicitly None")
        print("   - We needed to use: context.get('task') or {}")
        print("   - This ensures task_info is ALWAYS a dict, never None")
    else:
        print("❌ Something unexpected happened")