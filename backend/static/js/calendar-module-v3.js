/**
 * Calendar Module V3 - Minimal Clean Implementation
 * Renders an empty calendar grid with 42 day cells
 */

const CalendarState = {
    masterCalendar: null,
    currentMonthIndex: 3, // Index in months array (0-6, center is 3)
    eventDetailPanel: null // EventDetailPanel instance
};

/**
 * Initialize calendar in the given container
 */
async function initializeCalendar(containerId, propertyId) {
    console.log('[Calendar] Initializing for property:', propertyId);

    const container = document.getElementById(containerId);
    if (!container) {
        console.error('[Calendar] Container not found:', containerId);
        return;
    }

    // Initialize EventDetailPanel
    if (!CalendarState.eventDetailPanel) {
        CalendarState.eventDetailPanel = new EventDetailPanel();
        console.log('[Calendar] EventDetailPanel initialized');
    }

    // Build master calendar data structure
    CalendarState.masterCalendar = window.CalendarDataModel.buildMasterCalendar(new Date());
    console.log('[Calendar] Master calendar built:', CalendarState.masterCalendar);

    // Fetch events from API
    try {
        console.log('[Calendar] Fetching events from API...');
        const response = await fetch(`/api/property/${propertyId}/calendar`);
        const result = await response.json();

        if (result.success && result.data.events) {
            console.log('[Calendar] Fetched', result.data.events.length, 'events');

            // Distribute events to calendar days
            window.CalendarDataModel.distributeEventsToCalendar(
                CalendarState.masterCalendar,
                result.data.events
            );

            console.log('[Calendar] Events distributed to calendar');
        } else {
            console.warn('[Calendar] No events returned from API');
        }
    } catch (error) {
        console.error('[Calendar] Failed to fetch events:', error);
    }

    // Render calendar UI
    renderCalendarUI(container);
    renderMonth();
}

/**
 * Render the calendar UI structure (header and grid)
 */
function renderCalendarUI(container) {
    container.innerHTML = `
        <div class="calendar-header">
            <button id="prevMonth" class="calendar-nav-btn">&lt;</button>
            <h2 id="currentMonth" class="calendar-month-title"></h2>
            <button id="nextMonth" class="calendar-nav-btn">&gt;</button>
        </div>
        <div id="calendarGrid" class="calendar-grid-v3"></div>
    `;

    // Attach navigation listeners
    document.getElementById('prevMonth').addEventListener('click', () => navigateMonth(-1));
    document.getElementById('nextMonth').addEventListener('click', () => navigateMonth(1));
}

/**
 * Navigate to previous/next month
 */
function navigateMonth(direction) {
    CalendarState.currentMonthIndex += direction;

    // Clamp to available months (0-6)
    if (CalendarState.currentMonthIndex < 0) CalendarState.currentMonthIndex = 0;
    if (CalendarState.currentMonthIndex > 6) CalendarState.currentMonthIndex = 6;

    renderMonth();
}

/**
 * Render the current month's grid
 */
function renderMonth() {
    const monthData = CalendarState.masterCalendar.months[CalendarState.currentMonthIndex];
    console.log('[Calendar] Rendering month:', monthData.monthName, 'Days:', monthData.days.length);

    // Update header
    document.getElementById('currentMonth').textContent = monthData.monthName;

    // Render grid
    const grid = document.getElementById('calendarGrid');
    grid.innerHTML = '';

    // Render all 42 days (no more null checks - all are actual date objects)
    monthData.days.forEach(day => {
        const cell = createDayCell(day);
        grid.appendChild(cell);
    });

    console.log('[Calendar] Rendered', monthData.days.length, 'day cells');
}

/**
 * Create a single day cell with event indicators
 */
function createDayCell(day) {
    const cell = document.createElement('div');
    cell.className = 'calendar-day-v3';

    // Add state classes
    if (!day.isCurrentMonth) cell.classList.add('other-month');
    if (day.isToday) cell.classList.add('today');
    if (day.isPast) cell.classList.add('past-date');

    // Highlight weekends (0 = Sunday, 6 = Saturday)
    if (day.dayOfWeek === 0 || day.dayOfWeek === 6) {
        cell.classList.add('weekend');
    }

    // Day header with day of week and date
    const dayHeader = document.createElement('div');
    dayHeader.className = 'day-header';

    const dayOfWeekNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const dayOfWeekLabel = document.createElement('span');
    dayOfWeekLabel.className = 'day-of-week';
    dayOfWeekLabel.textContent = dayOfWeekNames[day.dayOfWeek];

    const dayNumber = document.createElement('span');
    dayNumber.className = 'day-number';
    dayNumber.textContent = day.dayOfMonth;

    dayHeader.appendChild(dayOfWeekLabel);
    dayHeader.appendChild(dayNumber);
    cell.appendChild(dayHeader);

    // Render events
    if (day.events && day.events.length > 0) {
        const eventsContainer = document.createElement('div');
        eventsContainer.className = 'day-events';

        // Show first 3 events
        const eventsToShow = day.events.slice(0, 3);
        eventsToShow.forEach(event => {
            const eventBar = createEventBar(event);
            eventsContainer.appendChild(eventBar);
        });

        // Add "more" indicator if there are more than 3 events
        if (day.events.length > 3) {
            const moreIndicator = document.createElement('div');
            moreIndicator.className = 'event-more-indicator';
            moreIndicator.textContent = `+${day.events.length - 3} more`;
            moreIndicator.addEventListener('click', (e) => {
                e.stopPropagation();
                console.log('[Calendar] Show all events for day:', day.dateKey, day.events);
                // TODO V2: Open modal with all events
                alert(`${day.events.length} events on ${day.dateKey}\n\n${day.events.map(e => `• ${e.title}`).join('\n')}`);
            });
            eventsContainer.appendChild(moreIndicator);
        }

        cell.appendChild(eventsContainer);
    }

    return cell;
}

/**
 * Create an event bar for display on calendar
 */
function createEventBar(event) {
    const bar = document.createElement('div');
    bar.className = `event-bar event-${event.type}`;

    // Add position classes for multi-day spans
    if (event.isStart) bar.classList.add('event-start');
    if (event.isEnd) bar.classList.add('event-end');
    if (event.isContinuation) bar.classList.add('event-continuation');

    // Event title (only show on first day to avoid repetition)
    if (event.isStart) {
        const title = document.createElement('span');
        title.className = 'event-title';
        title.textContent = event.title;
        bar.appendChild(title);
    }

    // Click handler for event details
    bar.addEventListener('click', (e) => {
        e.stopPropagation();
        showEventDetails(event.fullEvent);
    });

    return bar;
}

/**
 * Show event details in side panel
 */
function showEventDetails(event) {
    console.log('[Calendar] Show event details:', event);

    // Transform event data to match EventDetailPanel expected format
    const eventData = {
        id: event.id,
        name: event.title,
        type: event.type,
        clickupUrl: event.url,
        checkIn: event.check_in_timestamp,
        checkOut: event.check_out_timestamp,
        status: event.status,
        customFields: event.custom_fields || {}
    };

    // Open the panel
    CalendarState.eventDetailPanel.open(eventData);
}

// Public API
window.CalendarModuleV3 = {
    initialize: initializeCalendar
};

console.log('[Calendar Module V3] Loaded');
