# Plan to Integrate Right Panel into Left Panel

## Current Implementation Analysis

### Left Panel Structure (MainTaskPanel):
- Container: `<div className="h-full bg-gray-50 border-r border-gray-200 overflow-y-auto">`
- Sections:
  1. Task Overview (name, status, dates)
  2. Comments Section (expandable)
- Already has scrolling capability

### Right Panel Structure (StepDetailsPanel):
- Container: `<div className="w-96 bg-gray-50 shadow-xl h-full overflow-y-auto border-l border-gray-200">`
- Sections:
  1. Header with Step Selector dropdown
  2. Step details (conditional sections)
  3. Step comments

## Implementation Steps

### Step 1: Create Combined Left Panel Component
```jsx
function EnhancedLeftPanel({ mainTask, subtasks, selectedStepId, onStepSelect }) {
    // Combine MainTaskPanel logic
    // Add StepDetailsPanel logic
    
    return (
        <div className="h-full bg-gray-50 border-r border-gray-200 overflow-y-auto">
            {/* Section 1: Main Task Info */}
            <div className="p-4 bg-white border-b border-gray-200">
                // Existing main task content
            </div>
            
            {/* Section 2: Comments */}
            <CommentsSection task={mainTask} />
            
            {/* Section 3: Step Details (NEW) */}
            <div className="border-t-4 border-gray-300"> {/* Visual separator */}
                <StepDetailsSection 
                    subtasks={subtasks}
                    selectedStepId={selectedStepId}
                    onStepSelect={onStepSelect}
                />
            </div>
        </div>
    );
}
```

### Step 2: Modify StepDetailsSection for Left Panel
- Remove container div with shadow and border
- Adjust width from `w-96` to full width of parent
- Keep all internal functionality intact
- Adjust padding/margins for narrower space

### Step 3: Update Main Layout
```jsx
<div className="flex h-screen">
    {/* Enhanced Left Panel */}
    <div className="w-80 flex-shrink-0">
        <EnhancedLeftPanel 
            mainTask={mainTask}
            subtasks={subtasks}
            selectedStepId={selectedStepId}
            onStepSelect={setSelectedStepId}
        />
    </div>
    
    {/* Middle Panel - Now has more space */}
    <div className="flex-1 overflow-y-auto">
        // Existing middle panel content
    </div>
    
    {/* Right Panel - REMOVED */}
</div>
```

## Key Considerations

### 1. Scroll Behavior
- ✅ Parent container already has `overflow-y-auto`
- ✅ All sections will scroll together
- ✅ Comments expand/collapse will push step details down naturally

### 2. Visual Hierarchy
- Add strong visual separator between main task and step details
- Consider using:
  - `border-t-4 border-gray-300` for thick separator
  - Different background color for step details section
  - Clear section headers

### 3. Responsive Design
- Step selector dropdown will be narrower (w-80 vs w-96)
- May need to adjust font sizes or padding
- Consider abbreviated labels if needed

### 4. State Management
- No changes needed - same props passed down
- `selectedStepId` state remains in parent
- All existing functionality preserved

## Testing Checklist
- [ ] Comments expand/collapse still works
- [ ] Step details section moves down when comments expand
- [ ] Scroll works for entire left panel
- [ ] Step selector dropdown fits in narrower width
- [ ] All step detail sections display correctly
- [ ] No horizontal overflow in left panel
- [ ] Visual separation is clear between sections

## Rollback Strategy
- Keep original components unchanged initially
- Create new combined component
- Easy to revert by swapping component usage