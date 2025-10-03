/**
 * Custom Fields Sidebar Component
 *
 * Reusable component that displays filled and empty custom fields for any ClickUp task
 *
 * Features:
 * - Shows field name, UUID (if applicable), field type, and value
 * - Handles dropdowns (order_index + UUID), task relationships, arrays, and simple fields
 * - Separates filled vs empty fields
 * - Fully reusable - just pass a task ID
 *
 * Usage:
 *   const sidebar = new CustomFieldsSidebar('sidebar-container-id');
 *   sidebar.render(taskId);
 */

class CustomFieldsSidebar {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);

        if (!this.container) {
            console.error(`CustomFieldsSidebar: Container #${containerId} not found`);
        }
    }

    /**
     * Detect the type and structure of a custom field value
     */
    detectFieldType(value) {
        if (value === null || value === undefined) {
            return { type: 'null', isEmpty: true };
        }

        if (value === '' || (Array.isArray(value) && value.length === 0)) {
            return { type: typeof value === 'string' ? 'string' : 'array', isEmpty: true };
        }

        // Dropdown field: {id: "uuid", name: "display", order_index: number}
        if (typeof value === 'object' && !Array.isArray(value) && value.order_index !== undefined) {
            return {
                type: 'dropdown',
                isEmpty: false,
                uuid: value.id,
                displayValue: value.name,
                orderIndex: value.order_index
            };
        }

        // Array field (could be task relationships or multi-select)
        if (Array.isArray(value) && value.length > 0) {
            const firstItem = value[0];

            // Task relationship: [{id: "task_id", name: "Task Name"}, ...]
            if (firstItem && typeof firstItem === 'object' && firstItem.id && firstItem.name) {
                return {
                    type: 'task_relationship',
                    isEmpty: false,
                    items: value,
                    count: value.length
                };
            }

            // Simple array (strings, numbers, etc.)
            return {
                type: 'array',
                isEmpty: false,
                items: value,
                count: value.length
            };
        }

        // Object (not dropdown, not array)
        if (typeof value === 'object') {
            return {
                type: 'object',
                isEmpty: false,
                value: value
            };
        }

        // Simple types: string, number, boolean
        return {
            type: typeof value,
            isEmpty: false,
            value: value
        };
    }

    /**
     * Format a field value for display based on its type
     */
    formatFieldValue(fieldAnalysis) {
        switch (fieldAnalysis.type) {
            case 'dropdown':
                return `
                    <div class="field-value dropdown-value">
                        <div class="value-main">${this.escapeHtml(fieldAnalysis.displayValue)}</div>
                        <div class="value-meta">UUID: ${this.escapeHtml(fieldAnalysis.uuid)}</div>
                        <div class="value-meta">Order: ${fieldAnalysis.orderIndex}</div>
                    </div>
                `;

            case 'task_relationship':
                const taskList = fieldAnalysis.items.map(task =>
                    `<li>${this.escapeHtml(task.name)} <span class="uuid-badge">${this.escapeHtml(task.id)}</span></li>`
                ).join('');
                return `
                    <div class="field-value relationship-value">
                        <div class="value-main">${fieldAnalysis.count} linked task(s)</div>
                        <ul class="task-list">${taskList}</ul>
                    </div>
                `;

            case 'array':
                const arrayItems = fieldAnalysis.items.slice(0, 5).map(item =>
                    `<li>${this.escapeHtml(String(item))}</li>`
                ).join('');
                const more = fieldAnalysis.count > 5 ? `<li class="more">... and ${fieldAnalysis.count - 5} more</li>` : '';
                return `
                    <div class="field-value array-value">
                        <div class="value-main">${fieldAnalysis.count} items</div>
                        <ul class="array-list">${arrayItems}${more}</ul>
                    </div>
                `;

            case 'object':
                return `
                    <div class="field-value object-value">
                        <pre>${this.escapeHtml(JSON.stringify(fieldAnalysis.value, null, 2))}</pre>
                    </div>
                `;

            case 'string':
                // Truncate long strings
                const text = fieldAnalysis.value;
                const truncated = text.length > 100 ? text.substring(0, 100) + '...' : text;
                return `
                    <div class="field-value text-value">
                        ${this.escapeHtml(truncated)}
                    </div>
                `;

            case 'number':
                return `
                    <div class="field-value number-value">
                        ${fieldAnalysis.value}
                    </div>
                `;

            case 'boolean':
                return `
                    <div class="field-value boolean-value">
                        ${fieldAnalysis.value ? '✓ True' : '✗ False'}
                    </div>
                `;

            default:
                return `
                    <div class="field-value unknown-value">
                        ${this.escapeHtml(String(fieldAnalysis.value))}
                    </div>
                `;
        }
    }

    /**
     * Render a single field row
     */
    renderFieldRow(fieldName, fieldAnalysis) {
        const typeClass = fieldAnalysis.isEmpty ? 'empty' : fieldAnalysis.type;
        const typeBadge = `<span class="type-badge ${typeClass}">${fieldAnalysis.type}</span>`;

        return `
            <div class="field-row ${fieldAnalysis.isEmpty ? 'empty-field' : 'filled-field'}">
                <div class="field-header">
                    <div class="field-name">${this.escapeHtml(fieldName)}</div>
                    ${typeBadge}
                </div>
                ${fieldAnalysis.isEmpty ? '' : this.formatFieldValue(fieldAnalysis)}
            </div>
        `;
    }

    /**
     * Fetch task data and render the sidebar
     */
    async render(taskId) {
        if (!this.container) {
            console.error('CustomFieldsSidebar: Container not found, cannot render');
            return;
        }

        // Show loading state
        this.container.innerHTML = '<div class="sidebar-loading">Loading custom fields...</div>';

        try {
            // Fetch task data from backend
            const BACKEND_URL = 'https://taskpages-backend.onrender.com';
            const response = await fetch(`${BACKEND_URL}/api/task/${taskId}`, {
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch task ${taskId}: ${response.status}`);
            }

            const data = await response.json();

            // Convert ClickUp custom_fields array to object format
            const customFieldsArray = data.custom_fields || [];

            // Escalation field IDs to exclude (from task-helper.html)
            const ESCALATION_FIELD_IDS = [
                'c6e0281e-9001-42d7-a265-8f5da6b71132', // ESCALATION_REASON
                'e9e831f2-b439-4067-8e88-6b715f4263b2', // ESCALATION_AI_SUMMARY
                '8d784bd0-18e5-4db3-b45e-9a2900262e04', // ESCALATION_STATUS
                '934811f1-239f-4d53-880c-3655571fd02e', // ESCALATED_TO
                '5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f', // ESCALATION_TIMESTAMP
                'a077ecc9-1a59-48af-b2cd-42a63f5a7f86', // SUPERVISOR_RESPONSE
                'c40bf1c4-7d33-4b2b-8765-0784cd88591a'  // ESCALATION_RESOLVED_TIMESTAMP
            ];

            const customFields = {};
            customFieldsArray.forEach(field => {
                // Skip escalation fields
                if (!ESCALATION_FIELD_IDS.includes(field.id)) {
                    customFields[field.name] = field.value;
                }
            });

            // Analyze all fields
            const filledFields = [];
            const emptyFields = [];

            Object.entries(customFields).forEach(([fieldName, fieldValue]) => {
                const analysis = this.detectFieldType(fieldValue);

                if (analysis.isEmpty) {
                    emptyFields.push({ name: fieldName, analysis });
                } else {
                    filledFields.push({ name: fieldName, analysis });
                }
            });

            // Sort alphabetically
            filledFields.sort((a, b) => a.name.localeCompare(b.name));
            emptyFields.sort((a, b) => a.name.localeCompare(b.name));

            // Render sidebar
            const filledHtml = filledFields.map(field =>
                this.renderFieldRow(field.name, field.analysis)
            ).join('');

            const emptyHtml = emptyFields.map(field =>
                this.renderFieldRow(field.name, field.analysis)
            ).join('');

            this.container.innerHTML = `
                <div class="custom-fields-sidebar">
                    <div class="sidebar-section filled-section">
                        <h3>Filled Custom Fields <span class="count-badge">${filledFields.length}</span></h3>
                        <div class="fields-container">
                            ${filledHtml || '<div class="no-fields">No filled custom fields</div>'}
                        </div>
                    </div>

                    <div class="sidebar-section empty-section">
                        <h3>Empty Custom Fields <span class="count-badge">${emptyFields.length}</span></h3>
                        <div class="fields-container">
                            ${emptyHtml || '<div class="no-fields">No empty custom fields</div>'}
                        </div>
                    </div>
                </div>
            `;

            // Log summary
            console.log(`CustomFieldsSidebar: Rendered ${filledFields.length} filled and ${emptyFields.length} empty fields`);

        } catch (error) {
            console.error('CustomFieldsSidebar: Error rendering sidebar:', error);
            this.container.innerHTML = `
                <div class="sidebar-error">
                    <strong>Error loading custom fields</strong>
                    <p>${this.escapeHtml(error.message)}</p>
                </div>
            `;
        }
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CustomFieldsSidebar;
}
