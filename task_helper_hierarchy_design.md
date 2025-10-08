# Task Helper - Hierarchy & Context Management

## Data Collection Strategy

### 1. Complete Hierarchy Fetching
```javascript
// On page load, fetch complete context
const fetchTaskHierarchy = async (taskId) => {
  const hierarchy = {
    // Main task being escalated
    currentTask: await fetchTask(taskId),
    
    // Parent chain (all the way to root)
    parentChain: await fetchParentChain(taskId),
    
    // Sibling tasks (same parent)
    siblings: await fetchSiblings(taskId),
    
    // All subtasks of current task
    subtasks: await fetchSubtasks(taskId),
    
    // Comments for current task + parents
    allComments: await fetchHierarchyComments(taskId),
    
    // All filled custom fields in hierarchy
    allCustomFields: await extractAllCustomFields(hierarchy)
  };
  
  return hierarchy;
};
```

### 2. Smart Context Extraction for AI
```javascript
// What the AI sees
const aiContext = {
  // Main task details
  task: {
    id, name, description, status, priority,
    customFields: filledFieldsOnly,
    comments: lastN(10),
    assignees, tags, dates
  },
  
  // Parent context (why this task exists)
  parentContext: {
    rootTask: parentChain[0],
    immediateParent: parentChain[parentChain.length - 1],
    customFields: filledFieldsOnly,
    relevantComments: lastN(3)
  },
  
  // Related work context
  relatedContext: {
    siblingTasks: siblings.filter(hasActivity),
    subtaskProgress: {
      total: subtasks.length,
      completed: subtasks.filter(isComplete).length,
      blocked: subtasks.filter(isBlocked)
    }
  },
  
  // Activity timeline (recent relevant activity)
  recentActivity: mergeAndSort([
    task.comments,
    parentChain.flatMap(t => t.comments),
    siblings.flatMap(t => t.recentComments)
  ]).slice(0, 20)
};
```

## Mobile-First UI Design

### 3. Progressive Disclosure Strategy

#### Mobile Layout (Stacked Cards)
```
┌─────────────────────┐
│   CURRENT TASK      │ ← Always visible, expandable
│   📋 "Fix login bug"│
│   🏷️ bug, urgent     │
│   👤 @john @sarah    │
└─────────────────────┘
┌─────────────────────┐
│   CONTEXT           │ ← Collapsible sections
│   📈 Parent Task    │ → Tap to expand
│   📊 Progress (3/5) │
│   💬 Recent (5)     │
└─────────────────────┘
┌─────────────────────┐
│   ESCALATION        │ ← Action module
│   ✏️  Type reason... │
│   🤖 Generate AI    │
│   📤 Escalate       │
└─────────────────────┘
```

#### Desktop Layout (3-Column)
```
┌─────────┬─────────────┬─────────────┐
│ TASK    │ CONTEXT     │ ACTION      │
│ INFO    │ HIERARCHY   │ MODULE      │
│         │             │             │
│ Current │ 📈 Parents  │ 🚨 Escalate │
│ Details │ 📊 Progress │             │
│ Fields  │ 💬 Comments │ AI Summary  │
│ Status  │ 🔗 Related  │ Recipient   │
│         │             │ Send        │
└─────────┴─────────────┴─────────────┘
```

### 4. Collapsible Context Sections (Mobile)

```jsx
<ContextPanel>
  {/* Always visible summary */}
  <ContextSummary>
    <TaskBreadcrumb parentChain={hierarchy.parentChain} />
    <ProgressIndicator 
      completed={completedSubtasks} 
      total={totalSubtasks} 
      blocked={blockedCount}
    />
  </ContextSummary>
  
  {/* Collapsible sections */}
  <CollapsibleSection 
    title="Parent Context" 
    badge={hierarchy.parentChain.length}
    defaultOpen={false}
  >
    <ParentTaskCard task={immediateParent} />
    <CustomFieldsPreview fields={parentCustomFields} />
  </CollapsibleSection>
  
  <CollapsibleSection 
    title="Recent Activity" 
    badge={recentComments.length}
    defaultOpen={true}
  >
    <ActivityTimeline items={recentActivity.slice(0, 5)} />
    <ShowMoreButton onClick={() => loadMore()} />
  </CollapsibleSection>
  
  <CollapsibleSection 
    title="Related Tasks" 
    badge={siblings.length}
    defaultOpen={false}
  >
    <SiblingsList tasks={activeSiblings} />
    <SubtasksProgress subtasks={subtasks} />
  </CollapsibleSection>
  
  <CollapsibleSection 
    title="Full Details" 
    badge="Advanced"
    defaultOpen={false}
  >
    <AllCustomFields fields={allFilledFields} />
    <CompleteCommentHistory comments={allComments} />
  </CollapsibleSection>
</ContextPanel>
```

### 5. Smart Context Condensing

#### Breadcrumb with Context
```jsx
<TaskBreadcrumb>
  <BreadcrumbItem>
    📁 Project Alpha
    <ContextPreview>3/8 features complete</ContextPreview>
  </BreadcrumbItem>
  <BreadcrumbItem>
    🎯 User Authentication
    <ContextPreview>2 blockers, 1 in review</ContextPreview>
  </BreadcrumbItem>
  <BreadcrumbItem current>
    🐛 Fix login validation
    <ContextPreview>Assigned: @john, Due: Tomorrow</ContextPreview>
  </BreadcrumbItem>
</TaskBreadcrumb>
```

#### Progress Cards
```jsx
<ProgressCard>
  <Icon>📊</Icon>
  <Title>Subtask Progress</Title>
  <Metrics>
    <Metric value={3} label="Done" color="green" />
    <Metric value={2} label="Active" color="blue" />
    <Metric value={1} label="Blocked" color="red" />
  </Metrics>
  <TapToExpand>Tap for details</TapToExpand>
</ProgressCard>
```

### 6. Context-Aware AI Prompting

```javascript
// AI gets structured context
const buildAIContext = (hierarchy, currentTask) => {
  return {
    // Core task info
    taskSummary: {
      id: currentTask.custom_id || currentTask.id,
      name: currentTask.name,
      description: currentTask.description,
      status: currentTask.status.status,
      priority: currentTask.priority?.priority,
      assignees: currentTask.assignees.map(a => a.username),
      tags: currentTask.tags.map(t => t.name)
    },
    
    // Parent context for "why"
    parentContext: hierarchy.parentChain.length > 0 ? {
      rootProject: hierarchy.parentChain[0].name,
      immediateParent: hierarchy.parentChain[hierarchy.parentChain.length - 1].name,
      projectPhase: getCustomField(hierarchy.parentChain[0], 'PROJECT_PHASE'),
      parentPriority: hierarchy.parentChain[hierarchy.parentChain.length - 1].priority
    } : null,
    
    // Work progress context
    workContext: {
      subtasksTotal: hierarchy.subtasks.length,
      subtasksComplete: hierarchy.subtasks.filter(isComplete).length,
      recentActivity: hierarchy.allComments.slice(0, 10).map(c => ({
        author: c.user.username,
        text: c.comment_text.slice(0, 200),
        date: c.date
      })),
      blockingIssues: hierarchy.subtasks.filter(isBlocked).map(t => ({
        name: t.name,
        blocker: getCustomField(t, 'BLOCKER_REASON')
      }))
    },
    
    // All relevant custom field data
    customFieldContext: extractRelevantCustomFields(hierarchy),
    
    // Timeline context
    timeContext: {
      created: currentTask.date_created,
      lastActivity: getLastActivityDate(hierarchy.allComments),
      dueDate: currentTask.due_date,
      isOverdue: currentTask.due_date && new Date() > new Date(currentTask.due_date)
    }
  };
};
```

### 7. Mobile Optimization Techniques

#### Lazy Loading Strategy
```javascript
// Load in priority order
const loadHierarchy = async (taskId) => {
  // 1. Current task (immediate)
  setCurrentTask(await fetchTask(taskId));
  
  // 2. Essential context (fast)
  const [parent, comments] = await Promise.all([
    fetchImmediateParent(taskId),
    fetchRecentComments(taskId, 5)
  ]);
  setEssentialContext({ parent, comments });
  
  // 3. Extended context (background)
  setTimeout(async () => {
    const [siblings, subtasks, fullParentChain] = await Promise.all([
      fetchSiblings(taskId),
      fetchSubtasks(taskId),
      fetchFullParentChain(taskId)
    ]);
    setExtendedContext({ siblings, subtasks, fullParentChain });
  }, 500);
  
  // 4. Complete context (when needed)
  // Loaded only when user expands sections
};
```

#### Touch-Friendly Interactions
```jsx
// Swipe gestures for context navigation
<SwipeableContextPanel>
  <SwipeView id="current">
    <CurrentTaskView />
  </SwipeView>
  <SwipeView id="parent">
    <ParentContextView />
  </SwipeView>
  <SwipeView id="activity">
    <ActivityTimelineView />
  </SwipeView>
  <SwipeView id="related">
    <RelatedTasksView />
  </SwipeView>
</SwipeableContextPanel>

// Tab indicators
<ContextTabs>
  <Tab active>Current</Tab>
  <Tab badge={parentCount}>Parents</Tab>
  <Tab badge={commentCount}>Activity</Tab>
  <Tab badge={siblingCount}>Related</Tab>
</ContextTabs>
```

### 8. Data Structure for AI Context

```javascript
// Comprehensive context object sent to AI
const escalationContext = {
  // Current task being escalated
  primary: {
    task: currentTask,
    customFields: getFilledCustomFields(currentTask),
    recentComments: currentTask.comments.slice(-5),
    assignmentHistory: getAssignmentHistory(currentTask)
  },
  
  // Parent hierarchy (for understanding purpose)
  hierarchy: {
    depth: parentChain.length,
    root: parentChain[0],
    chain: parentChain.map(simplifyForAI),
    contextualFields: getRelevantParentFields(parentChain)
  },
  
  // Work progress (for understanding status)
  progress: {
    subtasksSummary: summarizeSubtasks(subtasks),
    blockers: identifyBlockers(subtasks),
    completionRate: calculateCompletionRate(subtasks),
    timeline: buildTimeline(allComments)
  },
  
  // Related work (for understanding scope)
  scope: {
    siblingTasks: siblings.filter(isRelevant),
    dependentTasks: findDependencies(currentTask),
    affectedStakeholders: extractStakeholders(hierarchy)
  }
};
```

### 9. Performance Considerations

- **Initial Load**: Current task + immediate parent only (~200ms)
- **Progressive Enhancement**: Load additional context in background
- **Caching**: Cache hierarchy data for 5 minutes
- **Debounced Loading**: Don't fetch until user actually expands sections
- **Compression**: Send minimal data to AI (summaries, not full objects)
- **Offline Support**: Cache last viewed hierarchy for offline access

### 10. Mobile UX Patterns

```jsx
// Bottom sheet for detailed context
<BottomSheet snapPoints={['25%', '50%', '90%']}>
  <SheetContent>
    <ContextDetails hierarchy={hierarchy} />
  </SheetContent>
</BottomSheet>

// Floating action button for quick access
<FloatingActionButton 
  actions={[
    { icon: '🚨', label: 'Escalate', action: 'escalate' },
    { icon: '📊', label: 'View Context', action: 'context' },
    { icon: '💬', label: 'Add Comment', action: 'comment' }
  ]}
/>

// Pull-to-refresh for latest data
<PullToRefresh onRefresh={reloadHierarchy}>
  <TaskContent />
</PullToRefresh>
```

