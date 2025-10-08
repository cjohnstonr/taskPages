#!/usr/bin/env python3
"""
Demonstrate the EXACT behavior of dict.get() with None values
This shows why context.get('task', {}) returns None instead of {}
"""

print("=" * 60)
print("PYTHON dict.get() BEHAVIOR DEMONSTRATION")
print("=" * 60)

# Scenario 1: Key doesn't exist
print("\nScenario 1: Key doesn't exist")
context1 = {'other_key': 'value'}
result1 = context1.get('task', {})
print(f"context = {context1}")
print(f"context.get('task', {{}}) = {result1}")
print(f"Result type: {type(result1)}")
print("✅ Default {} is used because 'task' key doesn't exist")

# Scenario 2: Key exists with value None (THE PROBLEM!)
print("\nScenario 2: Key exists with value None (THIS IS THE BUG!)")
context2 = {'task': None}  # This is what happens when frontend sends {task: null}
result2 = context2.get('task', {})
print(f"context = {context2}")
print(f"context.get('task', {{}}) = {result2}")
print(f"Result type: {type(result2)}")
print("❌ Default {} is NOT used because 'task' key EXISTS (even though its value is None)")

# Scenario 3: Key exists with empty dict value
print("\nScenario 3: Key exists with empty dict value")
context3 = {'task': {}}
result3 = context3.get('task', {'default': 'value'})
print(f"context = {context3}")
print(f"context.get('task', {{'default': 'value'}}) = {result3}")
print(f"Result type: {type(result3)}")
print("✅ Original {} is returned, default is not used")

print("\n" + "=" * 60)
print("KEY INSIGHT:")
print("=" * 60)
print("dict.get(key, default) returns the default ONLY when the key is MISSING")
print("If the key EXISTS with value None, it returns None!")
print()
print("When JavaScript sends: {task: null}")
print("Python receives: {'task': None}")
print("context.get('task', {}) returns: None (not {})")
print()
print("SOLUTION: Use 'or' operator instead:")
print("context.get('task') or {} <- This returns {} when task is None")
print("=" * 60)

# Demonstrate the fix
print("\nTHE FIX:")
print("-" * 40)
context_with_null = {'task': None}
print(f"Context: {context_with_null}")
print()
print("❌ WRONG: context.get('task', {})")
wrong_way = context_with_null.get('task', {})
print(f"   Result: {wrong_way} (type: {type(wrong_way).__name__})")
print()
print("✅ RIGHT: context.get('task') or {}")  
right_way = context_with_null.get('task') or {}
print(f"   Result: {right_way} (type: {type(right_way).__name__})")