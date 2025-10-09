# PHASE 2: Property Link Validation & Propagation

**Status:** 🔲 READY TO START
**Depends On:** Phase 1 (✅ Complete)
**Estimated Duration:** 1 day
**Blocks:** Phase 3 (n8n integration requires property link)

---

## 🎯 Objective

Ensure every escalation has a property link by:
1. Checking if task has property link
2. If missing, checking parent task for property link
3. Auto-copying property link from parent to subtask
4. Blocking escalation if no property link exists anywhere

**Why Critical:** n8n needs property link to fetch property-specific context and vector stores

---

## 📋 Tasks

### STEP 1: Find or Create PROPERTY_LINK Field

#### Option A: Search for Existing Field
```bash
# Check ClickUp for existing property relationship fields
# Common names: "Property", "Property Link", "Related Property"
```

**If Found:**
- [ ] Get field UUID
- [ ] Update `FIELD_IDS.PROPERTY_LINK` in code
- [ ] Verify field type is "tasks" (task relationship)

#### Option B: Create New Field
- [ ] Go to ClickUp → Settings → Custom Fields
- [ ] Create new field:
  - **Name:** "Property Link"
  - **Type:** "Task Relationship"
  - **Location:** Process Library list
- [ ] Copy UUID
- [ ] Update `FIELD_IDS.PROPERTY_LINK` in code

**After completion, update:**
- `escalation-v2.html` line 216
- `app_secure.py` line 746

---

### STEP 2: Create Property Link Helper Functions

**File:** `app_secure.py`

```python
def get_property_link(task_id, clickup_token):
    """
    Get property link from task or parent task.

    Returns:
        property_link_id: str or None
        source: 'task' or 'parent' or None
    """
    headers = {
        "Authorization": clickup_token,
        "Content-Type": "application/json"
    }

    # 1. Get task details
    task_response = requests.get(
        f"https://api.clickup.com/api/v2/task/{task_id}",
        headers=headers
    )

    if not task_response.ok:
        logger.error(f"Failed to fetch task {task_id}")
        return None, None

    task_data = task_response.json()

    # 2. Check if task has property link
    property_link_field = next(
        (f for f in task_data.get('custom_fields', [])
         if f['id'] == PROPERTY_LINK_FIELD_ID),
        None
    )

    if property_link_field and property_link_field.get('value'):
        # Task has property link
        return property_link_field['value'][0], 'task'

    # 3. Check parent task
    parent_id = task_data.get('parent')
    if not parent_id:
        # No parent, no property link
        return None, None

    # 4. Get parent task details
    parent_response = requests.get(
        f"https://api.clickup.com/api/v2/task/{parent_id}",
        headers=headers
    )

    if not parent_response.ok:
        logger.error(f"Failed to fetch parent task {parent_id}")
        return None, None

    parent_data = parent_response.json()

    # 5. Check if parent has property link
    parent_property_field = next(
        (f for f in parent_data.get('custom_fields', [])
         if f['id'] == PROPERTY_LINK_FIELD_ID),
        None
    )

    if parent_property_field and parent_property_field.get('value'):
        return parent_property_field['value'][0], 'parent'

    # No property link found anywhere
    return None, None


def set_property_link(task_id, property_link_id, clickup_token):
    """
    Set property link on a task using {"add": [ids]} format.

    Args:
        task_id: Task to update
        property_link_id: Property task ID to link
        clickup_token: ClickUp API key

    Returns:
        bool: Success/failure
    """
    headers = {
        "Authorization": clickup_token,
        "Content-Type": "application/json"
    }

    # Use "add" format for task relationship fields
    response = requests.post(
        f"https://api.clickup.com/api/v2/task/{task_id}/field/{PROPERTY_LINK_FIELD_ID}",
        headers=headers,
        json={
            "value": {
                "add": [property_link_id]
            }
        }
    )

    if response.ok:
        logger.info(f"Property link set on task {task_id}")
        return True
    else:
        logger.error(f"Failed to set property link: {response.text}")
        return False
```

---

### STEP 3: Create Validation Endpoint

**File:** `app_secure.py`

```python
@app.route('/api/task-helper/validate-property-link/<task_id>', methods=['GET'])
@login_required
@rate_limiter.rate_limit(limit='20 per minute')
def validate_property_link(task_id):
    """
    Validate that task has property link.
    If missing from subtask, auto-copy from parent.

    Returns:
        200: Property link exists or was successfully copied
        400: No property link found (employee must add it)
    """
    try:
        clickup_token = os.getenv('CLICKUP_API_KEY')
        if not clickup_token:
            return jsonify({"error": "ClickUp integration not configured"}), 500

        # Check for property link
        property_link_id, source = get_property_link(task_id, clickup_token)

        if not property_link_id:
            # No property link anywhere
            return jsonify({
                "valid": False,
                "error": "NO_PROPERTY_LINK",
                "message": "This task must have a property link before escalation. Please add a property link to this task or its parent task."
            }), 400

        if source == 'parent':
            # Property link found on parent, copy to subtask
            logger.info(f"Copying property link from parent to task {task_id}")

            success = set_property_link(task_id, property_link_id, clickup_token)

            if not success:
                return jsonify({
                    "valid": False,
                    "error": "COPY_FAILED",
                    "message": "Found property link on parent task, but failed to copy to this task."
                }), 500

            return jsonify({
                "valid": True,
                "property_link_id": property_link_id,
                "source": "parent",
                "action": "copied",
                "message": "Property link copied from parent task"
            }), 200

        # Property link exists on task
        return jsonify({
            "valid": True,
            "property_link_id": property_link_id,
            "source": "task",
            "action": "none",
            "message": "Property link already exists on task"
        }), 200

    except Exception as e:
        logger.error(f"Error validating property link for task {task_id}: {e}")
        return jsonify({"error": f"Failed to validate property link: {str(e)}"}), 500
```

---

### STEP 4: Create Frontend Validator Component

**File:** `escalation-v2.html`

Add before escalation form:

```javascript
function PropertyLinkValidator({ task, onValidated, onError }) {
    const [isValidating, setIsValidating] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        validatePropertyLink();
    }, [task.id]);

    const validatePropertyLink = async () => {
        setIsValidating(true);
        setError(null);

        try {
            const response = await fetch(`${BACKEND_URL}/api/task-helper/validate-property-link/${task.id}`, {
                credentials: 'include'
            });

            const result = await response.json();

            if (response.ok) {
                // Property link valid
                onValidated(result.property_link_id);
            } else {
                // No property link
                setError(result.message);
                onError(result.error);
            }
        } catch (err) {
            setError('Failed to validate property link');
            onError('VALIDATION_ERROR');
        } finally {
            setIsValidating(false);
        }
    };

    if (isValidating) {
        return (
            <div className="bg-blue-50 rounded-lg p-6">
                <div className="flex items-center">
                    <div className="spinner mr-3"></div>
                    <p className="text-blue-700">Validating property link...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-50 rounded-lg p-6 border border-red-200">
                <div className="flex items-center mb-4">
                    <span className="text-2xl mr-3">⚠️</span>
                    <h3 className="text-lg font-semibold text-red-900">Property Link Required</h3>
                </div>
                <p className="text-red-700 mb-4">{error}</p>
                <div className="bg-white p-4 rounded border border-red-200">
                    <p className="text-sm text-gray-700 mb-2"><strong>How to add a property link:</strong></p>
                    <ol className="text-sm text-gray-700 list-decimal ml-5 space-y-1">
                        <li>Go to this task in ClickUp</li>
                        <li>Find the "Property Link" custom field</li>
                        <li>Select the property this task is related to</li>
                        <li>Return here and click "Retry Validation"</li>
                    </ol>
                </div>
                <button
                    onClick={validatePropertyLink}
                    className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                >
                    🔄 Retry Validation
                </button>
            </div>
        );
    }

    // Valid - render nothing (allow escalation form to show)
    return null;
}
```

---

### STEP 5: Update EscalationModule Component

**File:** `escalation-v2.html`

Modify the `EscalationModule` component:

```javascript
function EscalationModule({ task, parentTask, onRefresh }) {
    const [propertyLinkValid, setPropertyLinkValid] = useState(false);
    const [propertyLinkId, setPropertyLinkId] = useState(null);
    const [escalationBlocked, setEscalationBlocked] = useState(true);

    // ... existing state variables ...

    const handlePropertyValidated = (propertyId) => {
        setPropertyLinkValid(true);
        setPropertyLinkId(propertyId);
        setEscalationBlocked(false);
    };

    const handlePropertyError = (errorCode) => {
        setPropertyLinkValid(false);
        setEscalationBlocked(true);
    };

    // Show property link validator FIRST
    if (escalationBlocked) {
        return (
            <PropertyLinkValidator
                task={task}
                onValidated={handlePropertyValidated}
                onError={handlePropertyError}
            />
        );
    }

    // ... rest of existing EscalationModule code ...
    // (escalation form, RFI handling, etc.)
}
```

---

## 🧪 Testing

### Test Case 1: Task Has Property Link
- [ ] Create test task with property link set
- [ ] Load escalation page
- [ ] Verify: Validator passes, escalation form shows

### Test Case 2: Parent Has Property Link
- [ ] Create parent task with property link
- [ ] Create subtask WITHOUT property link
- [ ] Load escalation page on subtask
- [ ] Verify: Property link copied from parent to subtask
- [ ] Verify: Escalation form shows

### Test Case 3: No Property Link Anywhere
- [ ] Create task WITHOUT property link
- [ ] Load escalation page
- [ ] Verify: Error shown, escalation blocked
- [ ] Add property link in ClickUp
- [ ] Click "Retry Validation"
- [ ] Verify: Validator passes, escalation form shows

### Test Case 4: Custom Task IDs
- [ ] Create task with custom ID (e.g., TICKET-123)
- [ ] Test property link validation
- [ ] Verify: Works with custom IDs (see `/Local/test_property_link_propagation.py`)

---

## 📊 Success Criteria

Phase 2 is complete when:
- [ ] PROPERTY_LINK field exists in ClickUp
- [ ] Field UUID updated in code
- [ ] Helper functions implemented and tested
- [ ] Validation endpoint created
- [ ] Frontend validator component added
- [ ] All test cases pass
- [ ] Escalation blocked when no property link
- [ ] Property link auto-copied from parent when missing

---

## 🚀 Next Phase

After Phase 2 completion:
- ✅ Move to **PHASE 3: n8n AI Suggestion Integration**
- n8n can now safely receive property_link with every escalation
- Property-specific vector stores can be queried

---

**Owner:** Christian Johnston
**Created:** 2025-10-08
