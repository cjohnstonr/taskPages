# Task Helper - Escalation System Custom Fields

## Required ClickUp Custom Fields

### 1. ESCALATION_STATUS (Dropdown)
- **Purpose**: Track current escalation state
- **Options**:
  - Not Escalated (default)
  - Pending Summary
  - Ready to Escalate
  - Escalated
  - In Progress
  - Resolved
  - Cancelled

### 2. ESCALATION_REASON (Long Text)
- **Purpose**: Store the original escalation reason
- **Format**: Plain text, max 2000 characters

### 3. ESCALATION_SUMMARY (Long Text)  
- **Purpose**: AI-generated summary of the issue
- **Format**: Markdown supported

### 4. ESCALATED_TO (Relationship)
- **Purpose**: Link to user who receives escalation
- **Type**: User relationship field

### 5. ESCALATED_BY (Text)
- **Purpose**: Track who initiated escalation
- **Format**: Email or username

### 6. ESCALATION_DATE (Date)
- **Purpose**: When escalation occurred
- **Format**: ISO timestamp

### 7. RESOLUTION_TEXT (Long Text)
- **Purpose**: Instructions/resolution from recipient
- **Format**: Markdown supported

### 8. RESOLUTION_DATE (Date)
- **Purpose**: When resolution was provided
- **Format**: ISO timestamp

### 9. ESCALATION_PRIORITY (Dropdown)
- **Purpose**: Urgency level
- **Options**:
  - Low
  - Medium
  - High
  - Critical

### 10. ESCALATION_ID (Text)
- **Purpose**: Unique identifier for escalation instance
- **Format**: UUID or timestamp-based ID

## Tag Management

### Tags to be Added:
- `escalated` - Added when task is escalated
- `escalated-resolved` - Added when resolved
- `escalated-{priority}` - Dynamic based on priority
- `needs-attention` - For urgent escalations

## Comment Templates

### Escalation Initiated Comment:
```
🚨 **ESCALATION INITIATED**
**By**: {user}
**To**: @{recipient}
**Priority**: {priority}
**Reason**: {reason}
**AI Summary**: {summary}
```

### Resolution Comment:
```
✅ **ESCALATION RESOLVED**
**By**: @{resolver}
**Resolution**: {resolution_text}
**Time to Resolve**: {duration}
```

