# Task Helper - Mobile Context Display Wireframes

## Progressive Disclosure Mobile UI

### Landing View (Initial Load)
```
╭─────────────────────────────╮
│ ← Task Helper   📋 Menu     │
├─────────────────────────────┤
│                             │
│  🔧 Fix login validation    │
│  ID: DEV-1234              │
│  🔴 High Priority           │
│  👤 @john @sarah           │
│  📅 Due Tomorrow           │
│                             │
│  📋 Description             │
│  User login fails with     │
│  invalid session error...  │
│                             │
├─────────────────────────────┤
│ CONTEXT                     │
│ ┌─────────────────────────┐ │
│ │ 📈 Parent: Auth System  │ │
│ │    Progress: 2/5 done   │ │
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ 💬 Recent Activity (3)  │ │
│ │    @sarah: debugging... │ │ 
│ │    @john: reproduced    │ │
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ 🔗 Related Tasks (2)    │ │
│ │    1 blocked, 1 active  │ │
│ └─────────────────────────┘ │
├─────────────────────────────┤
│ ESCALATE                    │
│ ┌─────────────────────────┐ │
│ │ ✏️ Why escalating?      │ │
│ │                         │ │
│ │ [Type your reason...]   │ │
│ │                         │ │
│ │ 🤖 Generate AI Summary  │ │
│ │ 📤 Escalate to Manager  │ │
│ └─────────────────────────┘ │
╰─────────────────────────────╯
```

### Expanded Parent Context
```
╭─────────────────────────────╮
│ ← Back        Parent Context│
├─────────────────────────────┤
│ 📈 User Authentication      │
│ ID: PROJ-567               │
│ Status: In Progress        │
│ Progress: 2/5 subtasks     │
│                             │
│ 📊 Custom Fields:           │
│ • Project Phase: Testing    │
│ • Priority: Critical       │
│ • Sprint: Sprint 23        │
│ • Tech Lead: @mike         │
│                             │
│ 💬 Parent Comments:         │
│ ┌─────────────────────────┐ │
│ │ @mike 2 hours ago       │ │
│ │ "Authentication module  │ │
│ │  needs to be done by    │ │
│ │  Friday for release"    │ │
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ @sarah 1 day ago        │ │
│ │ "Found session timeout  │ │
│ │  issue affecting login" │ │
│ └─────────────────────────┘ │
│                             │
│ 🔗 Breadcrumb Trail:        │
│ Project Alpha > User Auth > │
│ Login System > Fix Bug      │
╰─────────────────────────────╯
```

### Activity Timeline View
```
╭─────────────────────────────╮
│ ← Back      Activity Timeline│
├─────────────────────────────┤
│ 📅 Last 48 Hours            │
│                             │
│ ⏰ 2 hours ago              │
│ 💬 @sarah on DEV-1234       │
│    "Still debugging the     │
│     session validation"     │
│                             │
│ ⏰ 4 hours ago              │
│ 🔄 @john moved DEV-1234     │
│    From: In Progress        │
│    To: Blocked             │
│                             │
│ ⏰ 6 hours ago              │
│ 💬 @mike on PROJ-567        │
│    "Need status update on   │
│     auth module by EOD"     │
│                             │
│ ⏰ 1 day ago                │
│ ✅ @sarah completed         │
│    DEV-1230 (Password Reset)│
│                             │
│ ⏰ 1 day ago                │
│ 🏷️ @john added tag 'urgent' │
│    to DEV-1234             │
│                             │
│ 📄 Load More Activity...    │
╰─────────────────────────────╯
```

### Related Tasks Expanded
```
╭─────────────────────────────╮
│ ← Back         Related Tasks│
├─────────────────────────────┤
│ 👥 Sibling Tasks (Same Parent)│
│                             │
│ ✅ DEV-1230 Password Reset  │
│    @sarah - Completed       │
│                             │
│ 🟡 DEV-1231 2FA Setup      │
│    @mike - In Review       │
│                             │
│ 🔴 DEV-1232 OAuth Flow     │
│    @john - Blocked         │
│                             │
│ 📊 My Subtasks:            │
│                             │
│ ✅ Research session libs    │
│ ⏳ Implement validation     │
│ ❌ Write unit tests         │
│                             │
│ 🔗 Dependencies:            │
│ Blocked by: DEV-1229        │
│ Blocking: DEV-1235, DEV-1236│
│                             │
│ 📈 Impact Analysis:         │
│ • Affects 3 other features  │
│ • Critical for Sprint 23    │
│ • 2 developers waiting      │
╰─────────────────────────────╯
```

### AI Context Generation View
```
╭─────────────────────────────╮
│ ← Back      🤖 AI Assistant  │
├─────────────────────────────┤
│ ✏️ Your Escalation Reason:  │
│ ┌─────────────────────────┐ │
│ │ I'm stuck debugging the │ │
│ │ session validation bug. │ │
│ │ Tried multiple approaches│ │
│ │ but still getting errors│ │
│ │ when users login. Need  │ │
│ │ senior help to review   │ │
│ │ the authentication flow │ │
│ └─────────────────────────┘ │
│                             │
│ 🤖 AI is analyzing...       │
│ ┌─────────────────────────┐ │
│ │ ⚡ Processing context    │ │
│ │ • Task hierarchy        │ │
│ │ • Custom fields         │ │
│ │ • Comment history       │ │
│ │ • Related work          │ │
│ │ • Timeline data         │ │
│ └─────────────────────────┘ │
│                             │
│ 📋 Generated Summary:       │
│ ┌─────────────────────────┐ │
│ │ 🚨 ESCALATION SUMMARY   │ │
│ │                         │ │
│ │ **Task**: DEV-1234      │ │
│ │ Fix login validation    │ │
│ │                         │ │
│ │ **Context**: Part of    │ │
│ │ critical auth module    │ │
│ │ (PROJ-567) needed for   │ │
│ │ Sprint 23 release       │ │
│ │                         │ │
│ │ **Issue**: Session      │ │
│ │ validation failing,     │ │
│ │ blocking user logins    │ │
│ │                         │ │
│ │ **Impact**: 2 other     │ │
│ │ tasks blocked, affects  │ │
│ │ Friday release timeline │ │
│ │                         │ │
│ │ **Request**: Senior     │ │
│ │ review needed for auth  │ │
│ │ flow debugging          │ │
│ └─────────────────────────┘ │
│                             │
│ ✏️ Edit Summary             │
│ 📤 Send Escalation          │
╰─────────────────────────────╯
```

## Key Mobile UX Principles Applied:

### 1. **Progressive Disclosure**
- Start with essential info only
- Expand sections on demand
- Clear visual hierarchy

### 2. **Touch-First Design**
- Large tap targets (44px minimum)
- Swipe gestures for navigation
- Pull-to-refresh for updates

### 3. **Performance Optimized**
- Load current task immediately
- Background load extended context
- Cache for offline access

### 4. **Context Preservation**
- Breadcrumbs show where you are
- Back buttons maintain state
- Smooth transitions between views

### 5. **Information Density**
- Summarize complex data (3/5 progress)
- Use badges for counts
- Truncate with "..." and expand options

### 6. **Thumb-Friendly Navigation**
- Bottom-accessible primary actions
- Swipeable tabs at top
- FAB for quick actions

This design ensures the AI gets complete context while keeping the mobile experience fast and intuitive. The progressive loading means users see value immediately while comprehensive data loads in the background.
