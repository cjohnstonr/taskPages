/**
 * EventDetailPanel - Modular side panel for displaying event details
 * Uses Strategy Pattern with event type renderers for extensibility
 */

class EventDetailPanel {
    constructor() {
        this.panel = null;
        this.overlay = null;
        this.currentEvent = null;
        this.renderers = new Map();

        this.initializeDOM();
        this.registerDefaultRenderers();
    }

    /**
     * Initialize the panel and overlay DOM elements
     */
    initializeDOM() {
        // Create overlay
        this.overlay = document.createElement('div');
        this.overlay.className = 'panel-overlay hidden';
        this.overlay.addEventListener('click', () => this.close());

        // Create panel
        this.panel = document.createElement('div');
        this.panel.className = 'event-detail-panel';
        this.panel.innerHTML = `
            <div class="panel-header">
                <h3>Event Details</h3>
                <button class="close-panel-btn" aria-label="Close panel">×</button>
            </div>
            <div class="panel-content">
                <!-- Content will be dynamically rendered here -->
            </div>
        `;

        // Add close button handler
        const closeBtn = this.panel.querySelector('.close-panel-btn');
        closeBtn.addEventListener('click', () => this.close());

        // Append to body
        document.body.appendChild(this.overlay);
        document.body.appendChild(this.panel);
    }

    /**
     * Register default event type renderers
     */
    registerDefaultRenderers() {
        this.registerRenderer('reservation', new ReservationDetailRenderer());
        // Future renderers will be registered here:
        // this.registerRenderer('cleaning', new CleaningDetailRenderer());
        // this.registerRenderer('field_op', new FieldOpDetailRenderer());
        // this.registerRenderer('calendar_block', new CalendarBlockDetailRenderer());
    }

    /**
     * Register a renderer for a specific event type
     * @param {string} eventType - The event type identifier
     * @param {object} renderer - Renderer instance with render() method
     */
    registerRenderer(eventType, renderer) {
        this.renderers.set(eventType, renderer);
    }

    /**
     * Open the panel with event data
     * @param {object} eventData - Event data object
     */
    open(eventData) {
        console.log('[EventDetailPanel] Opening panel with event:', eventData);

        this.currentEvent = eventData;

        // Render content using appropriate renderer
        const content = this.render(eventData);

        // Update panel content
        const panelContent = this.panel.querySelector('.panel-content');
        panelContent.innerHTML = content;

        // Show panel with animation
        this.overlay.classList.remove('hidden');
        setTimeout(() => {
            this.panel.classList.add('active');
        }, 10);
    }

    /**
     * Close the panel
     */
    close() {
        console.log('[EventDetailPanel] Closing panel');

        this.panel.classList.remove('active');

        setTimeout(() => {
            this.overlay.classList.add('hidden');
            this.currentEvent = null;
        }, 300); // Match CSS transition duration
    }

    /**
     * Render event content using appropriate renderer
     * @param {object} eventData - Event data object
     * @returns {string} HTML string for panel content
     */
    render(eventData) {
        const eventType = eventData.type || 'unknown';
        const renderer = this.renderers.get(eventType);

        if (renderer) {
            return renderer.render(eventData);
        }

        // Fallback to generic renderer
        console.warn(`[EventDetailPanel] No renderer found for event type: ${eventType}`);
        return this.renderGeneric(eventData);
    }

    /**
     * Generic fallback renderer for unknown event types
     * @param {object} eventData - Event data object
     * @returns {string} HTML string
     */
    renderGeneric(eventData) {
        return `
            <div class="detail-section">
                <h4>Event Information</h4>
                <div class="detail-row">
                    <span class="detail-label">Name:</span>
                    <span class="detail-value">${eventData.name || 'Unnamed Event'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Type:</span>
                    <span class="detail-value">${eventData.type || 'Unknown'}</span>
                </div>
                ${eventData.clickupUrl ? `
                    <div class="detail-row">
                        <span class="detail-label">ClickUp Task:</span>
                        <span class="detail-value">
                            <a href="${eventData.clickupUrl}" target="_blank" rel="noopener noreferrer">
                                View Task ↗
                            </a>
                        </span>
                    </div>
                ` : ''}
            </div>
            <div class="detail-section">
                <h4>Raw Data (Debug)</h4>
                <pre style="background: #111827; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 11px; color: #9CA3AF;">${JSON.stringify(eventData, null, 2)}</pre>
            </div>
        `;
    }
}

/**
 * ReservationDetailRenderer - Renders reservation event details
 */
class ReservationDetailRenderer {
    /**
     * Render reservation details
     * @param {object} eventData - Reservation event data
     * @returns {string} HTML string
     */
    render(eventData) {
        console.log('[ReservationDetailRenderer] Rendering reservation:', eventData);

        const checkInDate = this.formatDate(eventData.checkIn);
        const checkOutDate = this.formatDate(eventData.checkOut);
        const duration = this.calculateDuration(eventData.checkIn, eventData.checkOut);
        const status = eventData.status || 'unknown';

        return `
            <div class="detail-section">
                <h4>Reservation Details</h4>

                <div class="detail-row">
                    <span class="detail-label">Guest Name:</span>
                    <span class="detail-value">${eventData.name || 'Unknown Guest'}</span>
                </div>

                <div class="detail-row">
                    <span class="detail-label">Status:</span>
                    <span class="detail-value">
                        <span class="status-badge status-${status}">${this.formatStatus(status)}</span>
                    </span>
                </div>

                <div class="detail-row">
                    <span class="detail-label">Check-In:</span>
                    <span class="detail-value">${checkInDate}</span>
                </div>

                <div class="detail-row">
                    <span class="detail-label">Check-Out:</span>
                    <span class="detail-value">${checkOutDate}</span>
                </div>

                <div class="detail-row">
                    <span class="detail-label">Duration:</span>
                    <span class="detail-value">${duration} ${duration === 1 ? 'night' : 'nights'}</span>
                </div>

                ${eventData.customFields ? this.renderCustomFields(eventData.customFields) : ''}
            </div>

            <div class="detail-actions">
                <a href="${eventData.clickupUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary">
                    <span>View in ClickUp</span>
                    <span class="external-icon">↗</span>
                </a>
            </div>
        `;
    }

    /**
     * Format Unix timestamp to readable date
     * @param {number} timestamp - Unix timestamp in milliseconds
     * @returns {string} Formatted date string
     */
    formatDate(timestamp) {
        if (!timestamp) return 'Not set';

        const date = new Date(timestamp);
        const options = {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        return date.toLocaleDateString('en-US', options);
    }

    /**
     * Calculate duration in nights between check-in and check-out
     * @param {number} checkIn - Check-in timestamp
     * @param {number} checkOut - Check-out timestamp
     * @returns {number} Number of nights
     */
    calculateDuration(checkIn, checkOut) {
        if (!checkIn || !checkOut) return 0;

        const msPerDay = 1000 * 60 * 60 * 24;
        return Math.round((checkOut - checkIn) / msPerDay);
    }

    /**
     * Format status string for display
     * @param {string} status - Status identifier
     * @returns {string} Formatted status
     */
    formatStatus(status) {
        const statusMap = {
            'pre-stay': 'Pre-Stay',
            'check-in-today': 'Check-In Today',
            'on-stay': 'On Stay',
            'check-out-today': 'Check-Out Today',
            'post-stay': 'Post-Stay',
            'completed': 'Completed',
            'unknown': 'Unknown'
        };
        return statusMap[status] || status;
    }

    /**
     * Render custom fields section
     * @param {object} customFields - Custom fields data
     * @returns {string} HTML string
     */
    renderCustomFields(customFields) {
        if (!customFields || Object.keys(customFields).length === 0) {
            return '';
        }

        const fields = Object.entries(customFields)
            .filter(([key, value]) => value !== null && value !== undefined)
            .map(([key, value]) => `
                <div class="detail-row">
                    <span class="detail-label">${this.formatFieldName(key)}:</span>
                    <span class="detail-value">${this.formatFieldValue(value)}</span>
                </div>
            `).join('');

        if (!fields) return '';

        return `
            <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #374151;">
                <h4 style="margin: 0 0 12px 0; font-size: 14px; font-weight: 600; color: #9CA3AF;">Additional Information</h4>
                ${fields}
            </div>
        `;
    }

    /**
     * Format field name for display
     * @param {string} fieldName - Field name
     * @returns {string} Formatted field name
     */
    formatFieldName(fieldName) {
        return fieldName
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase());
    }

    /**
     * Format field value for display
     * @param {*} value - Field value
     * @returns {string} Formatted value
     */
    formatFieldValue(value) {
        if (typeof value === 'object') {
            return JSON.stringify(value);
        }
        return String(value);
    }
}
