/**
 * Calendar Module V2 - Continuous Event Bars
 * Renders reservation events as continuous bars spanning multiple days
 */

// ============================================================================
// CALENDAR STATE
// ============================================================================

const CalendarState = {
    currentMonth: new Date(),
    events: [],
    selectedEvent: null
};

// ============================================================================
// DATE UTILITIES
// ============================================================================

function getMonthName(date) {
    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
}

function getDaysInMonth(year, month) {
    return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfMonth(year, month) {
    return new Date(year, month, 1).getDay();
}

function isSameDay(date1, date2) {
    return date1.toDateString() === date2.toDateString();
}

// ============================================================================
// EVENT RENDERING HELPERS
// ============================================================================

/**
 * Get status-based CSS class for event styling
 */
function getStatusClass(status) {
    if (!status) return 'status-unknown';

    // Normalize: replace hyphens with spaces, convert to lowercase
    const normalized = status.toLowerCase().replace(/-/g, ' ');

    const statusMap = {
        'pre stay': 'status-pre-stay',
        'check in today': 'status-check-in-today',
        'on stay': 'status-on-stay',
        'check out today': 'status-check-out-today',
        'post stay': 'status-post-stay',
        'completed': 'status-completed'
    };
    return statusMap[normalized] || 'status-unknown';
}

/**
 * Calculate which row to place an event in to avoid overlaps
 */
function calculateEventRows(events, year, month) {
    const rows = [];

    // Sort events by start date, then by duration (longer first)
    const sortedEvents = [...events].sort((a, b) => {
        const startDiff = new Date(a.check_in) - new Date(b.check_in);
        if (startDiff !== 0) return startDiff;

        // If same start date, put longer events first
        const durationA = new Date(a.check_out) - new Date(a.check_in);
        const durationB = new Date(b.check_out) - new Date(b.check_in);
        return durationB - durationA;
    });

    // Assign each event to first available row
    sortedEvents.forEach(event => {
        const eventStart = new Date(event.check_in);
        const eventEnd = new Date(event.check_out);

        // Find first row where this event doesn't overlap
        let rowIndex = 0;
        while (rowIndex < rows.length) {
            const rowHasOverlap = rows[rowIndex].some(existingEvent => {
                const existingStart = new Date(existingEvent.check_in);
                const existingEnd = new Date(existingEvent.check_out);

                // Check if events overlap
                return eventStart <= existingEnd && eventEnd >= existingStart;
            });

            if (!rowHasOverlap) {
                break;
            }
            rowIndex++;
        }

        // Create new row if needed
        if (rowIndex >= rows.length) {
            rows.push([]);
        }

        rows[rowIndex].push(event);
    });

    return rows;
}

/**
 * Calculate event positioning within the calendar grid
 * Returns: { startCol, span, leftOffset, rightOffset }
 */
function calculateEventPosition(event, year, month, firstDayOfWeek) {
    const checkIn = new Date(event.check_in);
    const checkOut = new Date(event.check_out);

    const monthStart = new Date(year, month, 1);
    const monthEnd = new Date(year, month + 1, 0);

    // Clamp dates to current month view
    const displayStart = checkIn < monthStart ? monthStart : checkIn;
    const displayEnd = checkOut > monthEnd ? monthEnd : checkOut;

    // Calculate day of month
    const startDay = displayStart.getDate();
    const endDay = displayEnd.getDate();

    // Calculate grid column (1-based, accounting for empty days at start)
    const startCol = firstDayOfWeek + startDay;
    const endCol = firstDayOfWeek + endDay;
    const span = endCol - startCol + 1;

    // Calculate left/right offset for check-in/check-out visual
    const isCheckInInMonth = isSameDay(checkIn, displayStart);
    const isCheckOutInMonth = isSameDay(checkOut, displayEnd);

    const leftOffset = isCheckInInMonth ? 50 : 0; // Start at 50% on check-in day
    const rightOffset = isCheckOutInMonth ? 50 : 0; // End at 50% on check-out day

    return { startCol, span, leftOffset, rightOffset };
}

// ============================================================================
// CALENDAR RENDERING
// ============================================================================

/**
 * Render month view calendar with continuous event bars
 */
function renderMonthCalendar(calendarData) {
    const { events } = calendarData;

    const year = CalendarState.currentMonth.getFullYear();
    const month = CalendarState.currentMonth.getMonth();

    // Filter events to only include those that overlap with this month
    const monthStart = new Date(year, month, 1);
    const monthEnd = new Date(year, month + 1, 0, 23, 59, 59);

    const filteredEvents = (events || []).filter(event => {
        const checkIn = new Date(event.check_in);
        const checkOut = new Date(event.check_out);
        return checkOut >= monthStart && checkIn <= monthEnd;
    });

    CalendarState.events = filteredEvents;
    console.log(`[DEBUG] Filtered ${filteredEvents.length} events for ${getMonthName(CalendarState.currentMonth)} (from ${events?.length || 0} total)`);

    const firstDay = getFirstDayOfMonth(year, month);
    const daysInMonth = getDaysInMonth(year, month);

    // Calculate event rows to avoid overlaps
    const eventRows = calculateEventRows(filteredEvents, year, month);

    let html = `
        <div class="calendar-month">
            <div class="calendar-header">
                <button class="calendar-nav-btn" onclick="previousMonth()">&larr;</button>
                <h3 class="calendar-month-title">${getMonthName(CalendarState.currentMonth)}</h3>
                <button class="calendar-nav-btn" onclick="nextMonth()">&rarr;</button>
            </div>
            <div class="calendar-grid-container">
                ${renderDayHeaders()}
                ${renderCalendarGrid(year, month, firstDay, daysInMonth, eventRows)}
            </div>
        </div>
    `;

    console.log('[DEBUG] renderMonthCalendar - Generated HTML length:', html.length);

    return html;
}

function renderDayHeaders() {
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    return `
        <div class="calendar-grid calendar-grid-header">
            ${days.map(day => `<div class="calendar-day-header">${day}</div>`).join('')}
        </div>
    `;
}

function renderCalendarGrid(year, month, firstDay, daysInMonth, eventRows) {
    // Calculate total weeks needed
    const totalDays = firstDay + daysInMonth;
    const weeks = Math.ceil(totalDays / 7);

    let html = `<div class="calendar-grid-body">`;

    // Render day numbers grid
    html += `<div class="calendar-grid calendar-grid-days">`;

    // Empty cells for days before first day of month
    for (let i = 0; i < firstDay; i++) {
        html += '<div class="calendar-day calendar-day-empty"></div>';
    }

    // Render each day of the month
    for (let day = 1; day <= daysInMonth; day++) {
        const currentDate = new Date(year, month, day);
        html += `
            <div class="calendar-day" data-date="${currentDate.toISOString()}">
                <div class="calendar-day-number">${day}</div>
            </div>
        `;
    }

    html += `</div>`; // Close calendar-grid-days

    // Render event bars overlaying the calendar grid
    html += renderEventBars(eventRows, year, month, firstDay);

    html += `</div>`; // Close calendar-grid-body

    return html;
}

/**
 * Render event bars as continuous overlays across calendar days
 * Each row represents a non-overlapping layer of events
 */
function renderEventBars(eventRows, year, month, firstDay) {
    if (!eventRows || eventRows.length === 0) {
        return '<div class="calendar-events-overlay"></div>';
    }

    let html = '<div class="calendar-events-overlay">';

    // Render each row of events
    eventRows.forEach((row, rowIndex) => {
        row.forEach(event => {
            html += renderEventBar(event, year, month, firstDay, rowIndex);
        });
    });

    html += '</div>';
    return html;
}

/**
 * Render a single event bar using CSS Grid positioning
 * Much simpler and more reliable than percentage-based positioning
 */
function renderEventBar(event, year, month, firstDay, rowIndex) {
    const checkIn = new Date(event.check_in);
    const checkOut = new Date(event.check_out);

    const monthStart = new Date(year, month, 1);
    const monthEnd = new Date(year, month + 1, 0, 23, 59, 59);

    // Clamp to current month view
    const displayStart = checkIn < monthStart ? monthStart : checkIn;
    const displayEnd = checkOut > monthEnd ? monthEnd : checkOut;

    // Check if event spans into current month
    if (displayEnd < monthStart || displayStart > monthEnd) {
        return '';
    }

    // Get day of month for start and end
    const startDay = displayStart.getDate();
    const endDay = displayEnd.getDate();

    // CSS GRID POSITIONING
    // The overlay grid has 42 columns (6 weeks × 7 days) to accommodate any month layout
    // Grid position = firstDay offset (0-6 for Sun-Sat) + day of month (1-31)
    // Example: November 2025 starts Saturday (firstDay=6), day 14 → position 20 (6+14)
    // CSS Grid is 1-based, and grid-column-end is exclusive (hence the +1)
    const gridColumnStart = firstDay + startDay;
    const gridColumnEnd = firstDay + endDay + 1; // +1 because grid-column-end is exclusive

    // Check if check-in/check-out are in this month (for visual styling)
    const isCheckInInMonth = isSameDay(checkIn, displayStart);
    const isCheckOutInMonth = isSameDay(checkOut, displayEnd);

    // Determine border radius and margin classes for 50% offset
    let borderClass = '';
    let offsetClass = '';

    if (isCheckInInMonth && isCheckOutInMonth) {
        borderClass = 'event-bar-both-ends';
        offsetClass = 'event-offset-both';
    } else if (isCheckInInMonth) {
        borderClass = 'event-bar-start';
        offsetClass = 'event-offset-start';
    } else if (isCheckOutInMonth) {
        borderClass = 'event-bar-end';
        offsetClass = 'event-offset-end';
    } else {
        borderClass = 'event-bar-continues';
        offsetClass = '';
    }

    // Get status-based color class
    const statusClass = getStatusClass(event.status);

    return `
        <div class="calendar-event-bar ${statusClass} ${borderClass} ${offsetClass}"
             style="grid-column: ${gridColumnStart} / ${gridColumnEnd}; grid-row: ${rowIndex + 1};"
             onclick="openEventDetail('${event.id}')"
             data-event-id="${event.id}"
             title="${escapeHtml(event.title)} - ${formatDateShort(event.check_in)} to ${formatDateShort(event.check_out)}">
            <span class="event-title">${escapeHtml(event.title)}</span>
        </div>
    `;
}

/**
 * Format date for short display (MMM D)
 */
function formatDateShort(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ============================================================================
// DETAIL PANEL
// ============================================================================

/**
 * Open event detail panel
 */
function openEventDetail(eventId) {
    const event = CalendarState.events.find(e => e.id === eventId);
    if (!event) {
        console.error('Event not found:', eventId);
        return;
    }

    CalendarState.selectedEvent = event;

    const panelHTML = `
        <div class="event-detail-panel active" id="eventDetailPanel">
            <div class="panel-header">
                <h3>Reservation Details</h3>
                <button class="close-panel-btn" onclick="closeEventDetail()">&times;</button>
            </div>
            <div class="panel-content">
                <!-- Guest Information -->
                <section class="detail-section">
                    <h4>Guest Information</h4>
                    <div class="detail-row">
                        <span class="detail-label">Guest Name:</span>
                        <span class="detail-value">${escapeHtml(event.details.guest_name || 'N/A')}</span>
                    </div>
                </section>

                <!-- Reservation Dates -->
                <section class="detail-section">
                    <h4>Stay Dates</h4>
                    <div class="detail-row">
                        <span class="detail-label">Check-In:</span>
                        <span class="detail-value">${formatDateTime(event.check_in)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Check-Out:</span>
                        <span class="detail-value">${formatDateTime(event.check_out)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Nights:</span>
                        <span class="detail-value">${calculateNights(event.check_in, event.check_out)}</span>
                    </div>
                </section>

                <!-- Status -->
                <section class="detail-section">
                    <h4>Booking Status</h4>
                    <div class="status-badge ${getStatusClass(event.status)}">
                        ${escapeHtml(event.status)}
                    </div>
                </section>

                <!-- Task Information -->
                <section class="detail-section">
                    <h4>Task Information</h4>
                    <div class="detail-row">
                        <span class="detail-label">Task Name:</span>
                        <span class="detail-value">${escapeHtml(event.task_name)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Task ID:</span>
                        <span class="detail-value"><code>${event.id}</code></span>
                    </div>
                    ${event.details.property_link ? `
                        <div class="detail-row">
                            <span class="detail-label">Property Link:</span>
                            <span class="detail-value"><code>${event.details.property_link}</code></span>
                        </div>
                    ` : ''}
                    ${event.details.cleaning_link ? `
                        <div class="detail-row">
                            <span class="detail-label">Cleaning Link:</span>
                            <span class="detail-value"><code>${event.details.cleaning_link}</code></span>
                        </div>
                    ` : ''}
                </section>

                <!-- Actions -->
                <section class="detail-actions">
                    <a href="${event.clickup_url}"
                       target="_blank"
                       class="btn-primary">
                        Open in ClickUp
                        <span class="external-icon">↗</span>
                    </a>
                    <button class="btn-secondary" onclick="closeEventDetail()">
                        Close
                    </button>
                </section>
            </div>
        </div>
        <div class="panel-overlay" onclick="closeEventDetail()"></div>
    `;

    // Remove existing panel if any
    const existingPanel = document.getElementById('eventDetailPanel');
    if (existingPanel) {
        existingPanel.remove();
    }
    const existingOverlay = document.querySelector('.panel-overlay');
    if (existingOverlay) {
        existingOverlay.remove();
    }

    // Append to body
    document.body.insertAdjacentHTML('beforeend', panelHTML);
}

/**
 * Close event detail panel
 */
function closeEventDetail() {
    const panel = document.getElementById('eventDetailPanel');
    const overlay = document.querySelector('.panel-overlay');

    if (panel) panel.remove();
    if (overlay) overlay.remove();

    CalendarState.selectedEvent = null;
}

// ============================================================================
// NAVIGATION
// ============================================================================

function previousMonth() {
    CalendarState.currentMonth = new Date(
        CalendarState.currentMonth.getFullYear(),
        CalendarState.currentMonth.getMonth() - 1,
        1
    );
    refreshCalendar();
}

function nextMonth() {
    CalendarState.currentMonth = new Date(
        CalendarState.currentMonth.getFullYear(),
        CalendarState.currentMonth.getMonth() + 1,
        1
    );
    refreshCalendar();
}

async function refreshCalendar() {
    if (!window.AppState || !window.AppState.selectedProperty) {
        console.error('No property selected');
        return;
    }

    try {
        const calendarData = await fetchCalendar(window.AppState.selectedProperty.id);
        renderCalendar(calendarData);
    } catch (error) {
        console.error('Error refreshing calendar:', error);
        alert('Failed to refresh calendar: ' + error.message);
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function calculateNights(checkIn, checkOut) {
    const start = new Date(checkIn);
    const end = new Date(checkOut);
    const diffTime = Math.abs(end - start);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
}
