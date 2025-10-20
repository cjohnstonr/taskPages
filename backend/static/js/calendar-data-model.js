/**
 * Calendar Data Model - Clean Implementation
 * Creates a master calendar object holding 7 months (3 past + current + 3 future)
 * Each month contains 42 day objects (6 weeks × 7 days) ready to hold events
 */

/**
 * Master Calendar Structure:
 * {
 *   currentMonth: Date,
 *   months: [
 *     {
 *       year: 2025,
 *       month: 7,  // 0-indexed (7 = August)
 *       monthName: "August 2025",
 *       days: [
 *         {
 *           date: Date object,
 *           dateKey: "2025-08-01",
 *           dayOfMonth: 1,
 *           dayOfWeek: 5,  // 0 = Sunday
 *           isCurrentMonth: true,
 *           isToday: false,
 *           isPast: false,
 *           events: []
 *         },
 *         // ... 41 more day objects (42 total for 6-week grid)
 *       ]
 *     }
 *     // ... 6 more month objects
 *   ]
 * }
 */

/**
 * Generate a 42-day grid for a single month (6 weeks × 7 days)
 * Includes padding from previous and next months with actual date objects
 */
function generateMonthGrid(year, month) {
    const days = [];
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startPadding = firstDay.getDay(); // Days from previous month
    const daysInMonth = lastDay.getDate();

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Previous month padding (ACTUAL DATE OBJECTS, not null)
    const prevMonth = new Date(year, month, 0);
    const prevMonthDays = prevMonth.getDate();
    for (let i = startPadding - 1; i >= 0; i--) {
        const day = prevMonthDays - i;
        const date = new Date(year, month - 1, day);
        days.push(createDayObject(date, false, today)); // isCurrentMonth = false
    }

    // Current month days
    for (let day = 1; day <= daysInMonth; day++) {
        const date = new Date(year, month, day);
        days.push(createDayObject(date, true, today)); // isCurrentMonth = true
    }

    // Next month padding to complete 42-day grid
    const remaining = 42 - days.length;
    for (let day = 1; day <= remaining; day++) {
        const date = new Date(year, month + 1, day);
        days.push(createDayObject(date, false, today)); // isCurrentMonth = false
    }

    return days;
}

/**
 * Create a single day object
 */
function createDayObject(date, isCurrentMonth, today) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');

    return {
        date: new Date(date),
        dateKey: `${y}-${m}-${d}`,
        dayOfMonth: date.getDate(),
        dayOfWeek: date.getDay(),
        isCurrentMonth: isCurrentMonth,
        isToday: date.getTime() === today.getTime(),
        isPast: date < today,
        events: []
    };
}

/**
 * Build master calendar: current month + 3 past + 3 future = 7 months
 */
function buildMasterCalendar(centerDate = new Date()) {
    const months = [];

    // Generate 7 months: 3 past, current, 3 future
    for (let offset = -3; offset <= 3; offset++) {
        const date = new Date(centerDate.getFullYear(), centerDate.getMonth() + offset, 1);
        const year = date.getFullYear();
        const month = date.getMonth();

        months.push({
            year: year,
            month: month,
            monthName: date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
            days: generateMonthGrid(year, month)
        });
    }

    return {
        currentMonth: centerDate,
        months: months
    };
}

/**
 * Distribute events to calendar days
 * Each event spans from check_in to check_out (inclusive)
 *
 * @param {Object} masterCalendar - Calendar data structure
 * @param {Array} events - Array of event objects from API
 */
function distributeEventsToCalendar(masterCalendar, events) {
    console.log('[Calendar Data Model] Distributing', events.length, 'events to calendar');

    events.forEach(event => {
        if (!event.check_in || !event.check_out) {
            console.warn('[Calendar Data Model] Event missing dates:', event);
            return;
        }

        // Parse date strings (YYYY-MM-DD format)
        const checkIn = new Date(event.check_in + 'T00:00:00');
        const checkOut = new Date(event.check_out + 'T00:00:00');

        let distributedCount = 0;

        // Iterate through all months in calendar
        masterCalendar.months.forEach(month => {
            month.days.forEach(day => {
                // Check if this day falls within the reservation span
                const dayDate = new Date(day.date);
                dayDate.setHours(0, 0, 0, 0);

                if (dayDate >= checkIn && dayDate <= checkOut) {
                    // Determine if this is the first or last day
                    const isStart = (dayDate.getTime() === checkIn.getTime());
                    const isEnd = (dayDate.getTime() === checkOut.getTime());

                    // Add event to this day's events array
                    day.events.push({
                        id: event.id,
                        type: event.type,
                        title: event.title,
                        isStart: isStart,
                        isEnd: isEnd,
                        isContinuation: !isStart && !isEnd,
                        fullEvent: event  // Reference to complete event data
                    });

                    distributedCount++;
                }
            });
        });

        console.log(`[Calendar Data Model] Event "${event.title}" distributed to ${distributedCount} days`);
    });

    console.log('[Calendar Data Model] Event distribution complete');
}

// Export for use in calendar module
window.CalendarDataModel = {
    buildMasterCalendar,
    generateMonthGrid,
    createDayObject,
    distributeEventsToCalendar
};
