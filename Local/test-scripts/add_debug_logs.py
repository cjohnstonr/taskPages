#!/usr/bin/env python3
"""
Add debug console.log statements to trace the right panel issue
"""

def add_debug_logs():
    with open('backend/templates/secured/wait-node-editable.html', 'r') as f:
        content = f.read()
    
    # Add console.log to onEditStep handler
    content = content.replace(
        'onEditStep={(step) => {',
        '''onEditStep={(step) => {
                                    console.log('Edit button clicked for step:', step);'''
    )
    
    # Add console.log to the toggle logic
    content = content.replace(
        'if (selectedStepForEdit && selectedStepForEdit.id === step.id) {',
        '''console.log('Current selectedStepForEdit:', selectedStepForEdit);
                                    if (selectedStepForEdit && selectedStepForEdit.id === step.id) {
                                        console.log('Closing panel - same step clicked');'''
    )
    
    content = content.replace(
        'setSelectedStepForEdit(null);',
        '''setSelectedStepForEdit(null);'''
    )
    
    content = content.replace(
        '} else {\n                                        setSelectedStepForEdit(step);',
        '''} else {
                                        console.log('Opening panel for step:', step);
                                        setSelectedStepForEdit(step);'''
    )
    
    # Add console.log to ProcessStepsAccordion
    content = content.replace(
        'function ProcessStepsAccordion({ subtasks, onEditStep, selectedStepId }) {',
        '''function ProcessStepsAccordion({ subtasks, onEditStep, selectedStepId }) {
        console.log('ProcessStepsAccordion rendered with:', { subtasksCount: subtasks?.length, selectedStepId, hasOnEditStep: !!onEditStep });'''
    )
    
    # Add console.log to Edit button render
    content = content.replace(
        '{libraryLevel !== \'Wait\' && onEditStep && !isDeleted && (',
        '''{(() => {
                                                console.log('Edit button check for step:', subtask.id, { libraryLevel, hasOnEditStep: !!onEditStep, isDeleted });
                                                return libraryLevel !== 'Wait' && onEditStep && !isDeleted;
                                            })() && ('''
    )
    
    # Add console.log to RightPanel component
    content = content.replace(
        'function RightPanel({ step, onClose, width, onResize, onStepDeleted }) {',
        '''function RightPanel({ step, onClose, width, onResize, onStepDeleted }) {
        console.log('RightPanel rendered with step:', step);'''
    )
    
    # Add console.log before the panel render condition
    old_text = '{/* Right Panel for Editing Steps */}\n                {selectedStepForEdit && ('
    new_text = '''{/* Right Panel for Editing Steps */}
                {(() => {
                    console.log('Right panel check - selectedStepForEdit:', selectedStepForEdit);
                    return selectedStepForEdit;
                })() && ('''
    
    content = content.replace(old_text, new_text)
    
    # Write the debug version
    with open('backend/templates/secured/wait-node-editable-debug.html', 'w') as f:
        f.write(content)
    
    print("Debug version created: wait-node-editable-debug.html")
    print("\nAdded console.log statements at:")
    print("1. Edit button click handler")
    print("2. Toggle logic in onEditStep")
    print("3. ProcessStepsAccordion render")
    print("4. Edit button visibility check")
    print("5. RightPanel component render")
    print("6. Right panel conditional render check")
    print("\nTo use: Replace wait-node-editable.html with this debug version and check browser console")

if __name__ == "__main__":
    add_debug_logs()