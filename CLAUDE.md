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