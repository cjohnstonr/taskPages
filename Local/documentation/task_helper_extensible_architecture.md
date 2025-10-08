# Task Helper - Extensible Architecture for Multiple Actions

## Core Design Principle: Action Modules System

Instead of a single-purpose escalation tool, we'll build a **pluggable action system** where escalation is just the first module.

## Revised Architecture

### 1. URL Structure (Action-Aware)
```
/task-helper/{task_id}                    # Default view
/task-helper/{task_id}?action=escalate    # Escalation module active
/task-helper/{task_id}?action=assign      # Assignment module active
/task-helper/{task_id}?action=analyze     # Analysis module active
/task-helper/{task_id}?action=automate    # Automation module active
```

### 2. Component Structure (Modular Actions)

```
TaskHelperApp
├── TaskDataProvider (shared context)
├── HeaderBar 
│   └── ActionSelector (dropdown/tabs for switching actions)
├── MainLayout
│   ├── TaskInfoPanel (always visible)
│   │   ├── TaskSummary
│   │   ├── CustomFieldsDisplay
│   │   ├── RelationshipsView
│   │   └── QuickStats
│   ├── ContextPanel (changes based on action)
│   │   ├── CommentsView (for escalate/communicate)
│   │   ├── HistoryView (for analyze)
│   │   ├── SubtasksView (for breakdown)
│   │   └── DependenciesView (for planning)
│   └── ActionPanel (swappable modules)
│       ├── EscalationModule
│       ├── QuickEditModule
│       ├── AssignmentModule
│       ├── TemplateModule
│       ├── AutomationModule
│       ├── CommunicationModule
│       └── AnalyticsModule
└── NotificationSystem
```

### 3. Action Modules Registry

```javascript
const ACTION_MODULES = {
  escalate: {
    name: 'Escalate',
    icon: '🚨',
    component: EscalationModule,
    permissions: ['view', 'comment'],
    context: 'comments',  // What to show in context panel
    description: 'Escalate issue to team lead'
  },
  
  quickEdit: {
    name: 'Quick Edit',
    icon: '✏️',
    component: QuickEditModule,
    permissions: ['view', 'edit'],
    context: 'fields',
    description: 'Edit key fields quickly'
  },
  
  assign: {
    name: 'Reassign',
    icon: '👤',
    component: AssignmentModule,
    permissions: ['view', 'edit'],
    context: 'team',
    description: 'Change assignees or watchers'
  },
  
  template: {
    name: 'Apply Template',
    icon: '📋',
    component: TemplateModule,
    permissions: ['view', 'edit'],
    context: 'templates',
    description: 'Apply preset templates'
  },
  
  breakdown: {
    name: 'Break Down',
    icon: '🔨',
    component: BreakdownModule,
    permissions: ['view', 'create'],
    context: 'subtasks',
    description: 'Create subtasks from templates'
  },
  
  communicate: {
    name: 'Send Update',
    icon: '📧',
    component: CommunicationModule,
    permissions: ['view'],
    context: 'comments',
    description: 'Send formatted updates'
  },
  
  analyze: {
    name: 'Analyze',
    icon: '📊',
    component: AnalyticsModule,
    permissions: ['view'],
    context: 'history',
    description: 'View task analytics'
  },
  
  automate: {
    name: 'Automate',
    icon: '⚡',
    component: AutomationModule,
    permissions: ['view', 'edit'],
    context: 'workflows',
    description: 'Trigger automations'
  }
}
```

### 4. Shared Services Layer

```javascript
// Services available to all action modules
const TaskHelperServices = {
  // Data fetching (cached)
  getTask: (taskId) => { /* ... */ },
  getComments: (taskId, options) => { /* ... */ },
  getSubtasks: (taskId) => { /* ... */ },
  getCustomFields: (taskId) => { /* ... */ },
  
  // Actions
  updateField: (taskId, fieldId, value) => { /* ... */ },
  addComment: (taskId, text, options) => { /* ... */ },
  addTag: (taskId, tag) => { /* ... */ },
  createSubtask: (taskId, data) => { /* ... */ },
  
  // AI Services
  generateSummary: (context) => { /* ... */ },
  suggestActions: (task) => { /* ... */ },
  analyzePattern: (data) => { /* ... */ },
  
  // Notifications
  notifyUser: (userId, message) => { /* ... */ },
  sendEmail: (template, data) => { /* ... */ },
  sendSMS: (phone, message) => { /* ... */ },
  
  // Utilities
  formatTask: (task) => { /* ... */ },
  parseCustomFields: (fields) => { /* ... */ },
  validatePermissions: (action) => { /* ... */ }
}
```

### 5. Progressive Enhancement Strategy

#### Phase 1: Foundation + Escalation
```javascript
// Minimal implementation
const ENABLED_MODULES = ['escalate'];
```

#### Phase 2: Quick Actions
```javascript
// Add simple field edits
const ENABLED_MODULES = ['escalate', 'quickEdit', 'assign'];
```

#### Phase 3: Communication
```javascript
// Add team communication features
const ENABLED_MODULES = [
  'escalate', 'quickEdit', 'assign', 
  'communicate', 'template'
];
```

#### Phase 4: Advanced Features
```javascript
// Full suite
const ENABLED_MODULES = Object.keys(ACTION_MODULES);
```

### 6. Module Interface Contract

Each action module must implement:

```javascript
interface ActionModule {
  // Lifecycle
  onMount(task, services) {}
  onUnmount() {}
  
  // State
  getInitialState() {}
  canExecute(task) {}
  
  // Actions
  execute(data) {}
  validate(data) {}
  
  // UI
  render() {}
  getContextRequirements() {}
}
```

### 7. Example Module Implementation

```javascript
class QuickEditModule {
  constructor() {
    this.editableFields = [
      'status', 'priority', 'due_date', 
      'assignees', 'tags', 'time_estimate'
    ];
  }
  
  onMount(task, services) {
    this.task = task;
    this.services = services;
    this.loadFieldDefinitions();
  }
  
  canExecute(task) {
    return task && \!task.archived;
  }
  
  async execute(changes) {
    const results = [];
    for (const [field, value] of Object.entries(changes)) {
      results.push(
        await this.services.updateField(this.task.id, field, value)
      );
    }
    await this.services.addComment(
      this.task.id,
      `Quick edit: Updated ${Object.keys(changes).join(', ')}`
    );
    return results;
  }
  
  render() {
    return (
      <div className="quick-edit-module">
        <h3>Quick Edit Fields</h3>
        {this.editableFields.map(field => (
          <FieldEditor 
            key={field}
            field={field}
            value={this.task[field]}
            onChange={(value) => this.handleChange(field, value)}
          />
        ))}
        <button onClick={() => this.save()}>Save Changes</button>
      </div>
    );
  }
}
```

### 8. Backend API Structure

```python
# Modular endpoint structure
@app.route('/api/task/<task_id>/action/<action_type>', methods=['POST'])
def execute_action(task_id, action_type):
    """Universal action handler"""
    
    # Get action handler
    handler = ACTION_HANDLERS.get(action_type)
    if not handler:
        return {'error': 'Unknown action'}, 400
    
    # Validate permissions
    if not handler.check_permissions(current_user, task_id):
        return {'error': 'Insufficient permissions'}, 403
    
    # Execute action
    result = handler.execute(task_id, request.json)
    
    # Log action
    log_action(task_id, action_type, current_user, result)
    
    return result

# Action handlers registry
ACTION_HANDLERS = {
    'escalate': EscalationHandler(),
    'quick_edit': QuickEditHandler(),
    'assign': AssignmentHandler(),
    'template': TemplateHandler(),
    'communicate': CommunicationHandler(),
    'analyze': AnalyticsHandler(),
    'automate': AutomationHandler()
}
```

### 9. Configuration System

```javascript
// config/task-helper.config.js
export default {
  // Which modules to enable
  enabledModules: process.env.ENABLED_MODULES?.split(',') || ['escalate'],
  
  // Default action when opening task
  defaultAction: 'escalate',
  
  // Module-specific configs
  modules: {
    escalate: {
      defaultRecipient: 'manager',
      requireSummary: true,
      maxReasonLength: 2000
    },
    quickEdit: {
      fields: ['status', 'priority', 'assignees'],
      autoSave: false
    },
    communicate: {
      templates: ['status_update', 'blocker', 'completed'],
      channels: ['email', 'slack', 'sms']
    }
  },
  
  // Feature flags
  features: {
    aiSummaries: true,
    bulkActions: false,
    offlineMode: false,
    realtimeSync: false
  }
}
```

### 10. Benefits of This Architecture

1. **Start Simple**: Launch with just escalation
2. **Add Incrementally**: New modules don't affect existing ones
3. **Consistent UX**: All actions follow same pattern
4. **Shared Code**: Services layer prevents duplication
5. **Configurable**: Enable/disable modules per deployment
6. **Maintainable**: Each module is independent
7. **Testable**: Modules can be tested in isolation
8. **Extensible**: Easy to add new action types
9. **Performant**: Load only active module code
10. **Discoverable**: Users can see available actions

