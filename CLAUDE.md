# Claude Agent Instructions

## Global Resources Available
This project has access to company-wide resources via symbolic links:

### Implementation Guides: `./global-guides/`
- List guides: `ls ./global-guides/`
- Search guides: `grep -r "pattern" ./global-guides/`
- Read guide: `cat ./global-guides/[guide-name].md`

### Sub-Agents: `./claude-agents/`
- List agents: `ls ./claude-agents/`
- Search agents: `grep -r "description" ./claude-agents/`
- Read agent spec: `cat ./claude-agents/[agent-name].md`

### Slash Commands: `./claude-commands/`
- List commands: `ls ./claude-commands/`
- Search commands: `grep -r "description" ./claude-commands/`
- Read command help: `cat ./claude-commands/[command-name].md`

### CLAUDE Rule Hierarchy: `./CLAUDE-*.md`
- List rules: `ls ./CLAUDE-*.md`
- Read workspace rules: `cat ./CLAUDE-workspace.md`
- Read user rules: `cat ./CLAUDE-user.md`

### Priority Guides for This Web/Python Project:
1. **Application Architecture Patterns** - Core patterns for web application structure
2. **Component Library Usage Guide** - UI component standards and patterns
3. **ClickUp Integration Manual** - API integration patterns and workflows
4. **AI-Assisted Development Workflow Guide** - Best practices for AI-driven development
5. **Workflow Execution + Custom Apps** - Custom workflow implementation patterns

### Before implementing:
1. Check for existing patterns in guides
2. Browse available agents for task automation
3. Use established slash commands for common workflows
4. Review CLAUDE rule hierarchy for context-specific instructions
5. Follow company standards

### Resource Categories:
- **Guides**: API Integration, Architecture, AI Development, UI Components, Workflows
- **Agents**: Specialized automation for debugging, testing, documentation, architecture
- **Commands**: Project setup, analysis, enhancement, debugging workflows
- **CLAUDE Rules**: Workspace-level and User-level instructions

## Quick Access Examples

```bash
# Browse implementation guides
ls ./global-guides/ | grep -i "clickup\|api\|architecture"

# Find relevant sub-agents
grep -r "frontend\|debug\|test" ./claude-agents/ | head -5

# Find useful slash commands
grep -r "description.*debug\|analysis\|screenshot" ./claude-commands/

# Browse rule hierarchy
ls ./CLAUDE-*.md

# Read specific resources
cat ./global-guides/ClickUp*.md
cat ./claude-agents/frontend-debugger.md
cat ./claude-commands/import-guides.md
```

## Sprint Management
CURRENT_SPRINT: 002-task-helper-foundation
SPRINT_COUNT: 2
STARTED: 2025-09-24
TODO_COUNT: 10
COMPLETED: 0

### Sprint History
- 001-oauth-authentication-debugging (completed 2025-09-15)
- 002-task-helper-foundation (current)
- These are the escalation tool custom field ids and names and uuids for dropdown fields: 
  | Field ID                             | Field Name                     | Type      | Dropdown Options with UUIDs
                                                                                                                                   |
  |--------------------------------------|--------------------------------|-----------|--------------------------------------------------------------------------------------------------------------------
  ---------------------------------------------------------------------------------------------------------------------------------|
  | 629ca244-a6d3-46dd-9f1e-6a0ded40f519 | Escalation_AI_Grade            | text      | N/A (text field)
                                                                                                                                   |
  | bc5e9359-01cd-408f-adb9-c7bdf1f2dd29 | Escalation_AI_Suggestion       | text      | N/A (text field)
                                                                                                                                   |
  | 94790367-5d1f-4300-8f79-e13819f910d4 | Escalation_History             | text      | N/A (text field)
                                                                                                                                   |
  | 0e7dd6f8-3167-4df5-964e-574734ffd4ed | Escalation_RFI_Request         | text      | N/A (text field)
                                                                                                                                   |
  | b5c52661-8142-45e0-bec5-14f3c135edbc | Escalation_RFI_Response        | text      | N/A (text field)
                                                                                                                                   |
  | f94c0b4b-0c70-4c23-9633-07af2fa6ddc6 | Escalation_RFI_Status          | drop_down | RFI Requested (UUID: 9b404ea6-efb7-40d1-9820-75ed5f5f47ff, Order: 0, Color: #FF4081)RFI Completed (UUID:
  3e28b07a-361a-4fc8-bc78-0d8774167939, Order: 1, Color: #7C4DFF)                                                                            |
  | e9e831f2-b439-4067-8e88-6b715f4263b2 | Escalation_Reason_AI           | text      | N/A (text field)
                                                                                                                                   |
  | c6e0281e-9001-42d7-a265-8f5da6b71132 | Escalation_Reason_Text         | text      | N/A (text field)
                                                                                                                                   |
  | c40bf1c4-7d33-4b2b-8765-0784cd88591a | Escalation_Resolved_Date_Time  | date      | N/A (date field)
                                                                                                                                   |
  | a077ecc9-1a59-48af-b2cd-42a63f5a7f86 | Escalation_Response_Text       | text      | N/A (text field)
                                                                                                                                   |
  | 8d784bd0-18e5-4db3-b45e-9a2900262e04 | Escalation_Status              | drop_down | Not Escalated (UUID: bf10e6ce-bef9-4105-aa2c-913049e2d4ed, Order: 0, Color: #FF4081)Escalated (UUID:
  8dc15846-e8c7-43a8-b7b2-1e1a0e1d6497, Order: 1, Color: #7C4DFF)Resolved (UUID: cbf82936-5488-4612-93a7-f8161071b0eb, Order: 2, Color: #f9d900) |
  | 5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f | Escalation_Submitted_Date_Time | date      | N/A (date field)
                                                                                                                                   |
  | 90d2fec8-7474-4221-84c0-b8c7fb5e4385 | Esclation_Level                | drop_down | Shirley (UUID: cfd3a04c-5b0c-4ddd-b65e-df65bd662ef5, Order: 0, Color: #FF4081)Christian (UUID:
  841566bc-4076-433e-af7b-9b5214bdc991, Order: 1, Color: #7C4DFF)                                                                                      |
- "See /Local/SHARE_THIS.md, /Local/test_property_link_propagation.py, and /Local/README_property_link_propagation.md for complete property_link propagation logic: detects missing property_link on 
  subtasks → fetches from parent → sets using {"add": [ids]} format. Handles custom task IDs (TICKET-xxx) correctly."