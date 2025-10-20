/**
 * Property Dashboard Application
 * Handles property list view, property detail view, and calendar module
 * Implements URL hash routing, caching, and error handling
 */

// ============================================================================
// ENVIRONMENT DETECTION & API PREFIX
// ============================================================================

// Detect if we're in local dev mode based on URL path
const IS_LOCAL_DEV = window.location.pathname.startsWith('/local/');

// CRITICAL FIX: Use absolute URLs to prevent ERR_ADDRESS_INVALID
// Construct full base URL from window.location.origin to ensure proper URL resolution
const BASE_URL = window.location.origin; // e.g., "http://localhost:5678"
const API_PATH = IS_LOCAL_DEV ? '/api/local' : '/api';
const API_PREFIX = `${BASE_URL}${API_PATH}`; // e.g., "http://localhost:5678/api/local"

// Expose API_PREFIX globally for calendar modules
window.API_PREFIX = API_PREFIX;

console.log(`Property Dashboard - Environment: ${IS_LOCAL_DEV ? 'LOCAL DEV' : 'PRODUCTION'}, API Prefix: ${API_PREFIX}`);

// ============================================================================
// APPLICATION STATE
// ============================================================================

// Expose AppState globally for calendar-module.js access
window.AppState = {
    currentView: 'property-list', // 'property-list' | 'property-detail'
    selectedProperty: null,
    properties: [],
    filteredProperties: [],
    calendarView: localStorage.getItem('calendarView') || 'month',
    lastViewedProperty: localStorage.getItem('lastViewedProperty') || null,
    isLoading: false,
    error: null
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Show/hide loading state
 */
function setLoading(isLoading) {
    window.AppState.isLoading = isLoading;
    const loadingEl = document.getElementById('loading-state');
    const contentEl = document.getElementById('property-list-view');
    const detailEl = document.getElementById('property-detail-view');
    const errorEl = document.getElementById('error-state');

    if (isLoading) {
        loadingEl.style.display = 'flex';
        contentEl.style.display = 'none';
        detailEl.style.display = 'none';
        errorEl.style.display = 'none';
    } else {
        loadingEl.style.display = 'none';
    }
}

/**
 * Show error state
 */
function showError(title, message) {
    window.AppState.error = { title, message };
    const errorEl = document.getElementById('error-state');
    const loadingEl = document.getElementById('loading-state');
    const contentEl = document.getElementById('property-list-view');
    const detailEl = document.getElementById('property-detail-view');

    document.getElementById('errorTitle').textContent = title;
    document.getElementById('errorMessage').textContent = message;

    errorEl.style.display = 'flex';
    loadingEl.style.display = 'none';
    contentEl.style.display = 'none';
    detailEl.style.display = 'none';
}

/**
 * Get custom field value by name
 */
function getCustomField(task, fieldName) {
    if (!task || !task.custom_fields) return null;
    const field = task.custom_fields.find(f => f.name === fieldName);
    return field ? field.value : null;
}

/**
 * Get formatted address from location custom field
 */
function getAddress(task) {
    const addressField = getCustomField(task, 'Property Address');
    if (addressField && addressField.formatted_address) {
        return addressField.formatted_address;
    }
    return 'Address not available';
}

/**
 * Get company name
 */
function getCompany(task) {
    return getCustomField(task, 'Company Name ') || 'Unknown';
}

/**
 * Get property nickname
 */
function getNickname(task) {
    return getCustomField(task, 'nickname') || '';
}

/**
 * Get owner name from Owner_Link relationship field
 */
function getOwnerName(task) {
    const ownerLink = getCustomField(task, 'Owner_Link');
    if (ownerLink && Array.isArray(ownerLink) && ownerLink.length > 0) {
        // ownerLink is an array of task relationship objects
        return ownerLink.map(owner => owner.name || owner.id).join(', ');
    }
    return 'Not Assigned';
}

/**
 * Update URL hash
 */
function updateHash(propertyId, module = 'calendar') {
    if (propertyId) {
        window.location.hash = `#property/${propertyId}/${module}`;
        localStorage.setItem('lastViewedProperty', propertyId);
    } else {
        window.location.hash = '';
        localStorage.removeItem('lastViewedProperty');
    }
}

/**
 * Parse URL hash
 */
function parseHash() {
    const hash = window.location.hash.substring(1); // Remove #
    if (!hash) return null;

    const parts = hash.split('/');
    if (parts[0] === 'property' && parts[1]) {
        return {
            type: 'property',
            propertyId: parts[1],
            module: parts[2] || 'calendar'
        };
    }
    return null;
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

/**
 * Fetch all properties (backend has 5-minute cache)
 */
async function fetchProperties(forceRefresh = false) {
    // Fetch from API (backend caching handles performance)
    const url = forceRefresh ? `${API_PREFIX}/properties?force_refresh=true` : `${API_PREFIX}/properties`;
    console.log('[DEBUG] fetchProperties - Full URL:', url);
    console.log('[DEBUG] fetchProperties - API_PREFIX:', API_PREFIX);
    console.log('[DEBUG] fetchProperties - window.location.origin:', window.location.origin);
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`Failed to fetch properties: ${response.statusText}`);
    }

    const result = await response.json();

    if (!result.success) {
        throw new Error(result.error.message || 'Failed to fetch properties');
    }

    console.log(`Fetched ${result.data.properties.length} properties from backend (OODA: ${result.data.ooda_count}, HELM: ${result.data.helm_count})`);

    return result.data.properties;
}

/**
 * Fetch single property details
 */
async function fetchProperty(propertyId) {
    const response = await fetch(`${API_PREFIX}/property/${propertyId}`);

    if (!response.ok) {
        if (response.status === 404) {
            throw new Error('Property not found or you don\'t have access');
        }
        throw new Error(`Failed to fetch property: ${response.statusText}`);
    }

    const result = await response.json();

    if (!result.success) {
        throw new Error(result.error.message || 'Failed to fetch property');
    }

    return result.data.property;
}

/**
 * Fetch property calendar data
 */
async function fetchCalendar(propertyId, startDate, endDate) {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const url = `${API_PREFIX}/property/${propertyId}/calendar?${params}`;
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`Failed to fetch calendar: ${response.statusText}`);
    }

    const result = await response.json();

    if (!result.success) {
        throw new Error(result.error.message || 'Failed to fetch calendar');
    }

    return result.data;
}

// ============================================================================
// PROPERTY LIST VIEW
// ============================================================================

/**
 * Render property card
 */
function createPropertyCard(property) {
    const card = document.createElement('div');
    card.className = 'property-card';
    card.dataset.propertyId = property.id;

    const address = getAddress(property);
    const owner = getOwnerName(property);
    const nickname = getNickname(property);

    card.innerHTML = `
        <div class="property-card-header">
            <div class="property-name">${property.name}</div>
            <div class="property-address">📍 ${address}</div>
        </div>
        <div class="property-card-meta">
            ${nickname ? `<div class="property-meta-item">
                <span class="meta-label">Nickname:</span>
                <span class="meta-value">${nickname}</span>
            </div>` : ''}
            <div class="property-meta-item">
                <span class="meta-label">Owner:</span>
                <span class="meta-value">${owner}</span>
            </div>
            <div class="property-meta-item">
                <span class="meta-label">Property ID:</span>
                <span class="meta-value">${property.id}</span>
            </div>
        </div>
    `;

    card.addEventListener('click', () => {
        loadPropertyDetail(property.id);
    });

    return card;
}

/**
 * Render property list
 */
function renderPropertyList(properties) {
    const oodaContainer = document.getElementById('oodaProperties');
    const helmContainer = document.getElementById('helmProperties');
    const noResultsEl = document.getElementById('noResults');

    // Clear existing content
    oodaContainer.innerHTML = '';
    helmContainer.innerHTML = '';

    // Separate and sort properties
    const oodaProps = properties
        .filter(p => getCompany(p) === 'Oodahost')
        .sort((a, b) => getAddress(a).localeCompare(getAddress(b)));

    const helmProps = properties
        .filter(p => getCompany(p) !== 'Oodahost')
        .sort((a, b) => getAddress(a).localeCompare(getAddress(b)));

    // Render OODA properties
    if (oodaProps.length > 0) {
        oodaProps.forEach(prop => {
            oodaContainer.appendChild(createPropertyCard(prop));
        });
    } else {
        oodaContainer.innerHTML = '<p class="empty-state-hint">No OODA properties found</p>';
    }

    // Render HELM properties
    if (helmProps.length > 0) {
        helmProps.forEach(prop => {
            helmContainer.appendChild(createPropertyCard(prop));
        });
    } else {
        helmContainer.innerHTML = '<p class="empty-state-hint">No HELM properties found</p>';
    }

    // Update counts
    document.getElementById('oodaDisplayCount').textContent = oodaProps.length;
    document.getElementById('helmDisplayCount').textContent = helmProps.length;

    // Show/hide no results message
    if (properties.length === 0) {
        noResultsEl.style.display = 'flex';
    } else {
        noResultsEl.style.display = 'none';
    }
}

/**
 * Filter properties by search query
 */
function filterProperties(query) {
    if (!query || query.trim() === '') {
        window.AppState.filteredProperties = window.AppState.properties;
    } else {
        const lowercaseQuery = query.toLowerCase();
        window.AppState.filteredProperties = window.AppState.properties.filter(prop => {
            const searchableText = [
                prop.name,
                getNickname(prop),
                getAddress(prop),
                getOwnerName(prop)
            ].join(' ').toLowerCase();

            return searchableText.includes(lowercaseQuery);
        });
    }

    // Update search term in no results message
    document.getElementById('searchTerm').textContent = query;

    renderPropertyList(window.AppState.filteredProperties);
}

/**
 * Load and display property list view
 */
async function loadPropertyListView() {
    try {
        setLoading(true);

        // Fetch properties
        const properties = await fetchProperties();
        window.AppState.properties = properties;
        window.AppState.filteredProperties = properties;
        window.AppState.currentView = 'property-list';

        // Update stats
        const oodaCount = properties.filter(p => getCompany(p) === 'Oodahost').length;
        const helmCount = properties.length - oodaCount;

        document.getElementById('totalCount').textContent = properties.length;
        document.getElementById('oodaCount').textContent = oodaCount;
        document.getElementById('helmCount').textContent = helmCount;

        // Render list
        renderPropertyList(properties);

        // Show view
        setLoading(false);
        document.getElementById('property-list-view').style.display = 'block';
        document.getElementById('property-detail-view').style.display = 'none';

        // Clear hash
        updateHash(null);

    } catch (error) {
        console.error('Error loading properties:', error);
        setLoading(false);
        showError('Unable to load properties', error.message);
    }
}

// ============================================================================
// PROPERTY DETAIL VIEW
// ============================================================================

/**
 * Initialize calendar module - Simple empty calendar
 */
function renderCalendar() {
    const contentEl = document.getElementById('calendarContent');
    const propertyId = window.AppState.selectedProperty?.id;

    if (!propertyId) {
        console.error('[Dashboard] No property selected for calendar');
        return;
    }

    console.log('[Dashboard] Initializing calendar for property:', propertyId);

    // Hide empty state
    const emptyState = document.querySelector('.calendar-empty-state');
    if (emptyState) {
        emptyState.style.display = 'none';
    }

    // Initialize calendar - only once
    if (!contentEl.querySelector('.calendar-header')) {
        console.log('[Dashboard] Calling CalendarModuleV3.initialize');
        CalendarModuleV3.initialize('calendarContent', propertyId);
    } else {
        console.log('[Dashboard] Calendar already initialized');
    }
}

/**
 * Load and display property detail view
 */
async function loadPropertyDetail(propertyId) {
    try {
        setLoading(true);

        // Fetch property data
        const property = await fetchProperty(propertyId);
        window.AppState.selectedProperty = property;
        window.AppState.currentView = 'property-detail';

        // Update property sidebar
        document.getElementById('propertyName').textContent = property.name;
        document.getElementById('propertyAddress').textContent = getAddress(property);
        document.getElementById('propertyOwner').textContent = `Owner: ${getOwnerName(property)}`;

        // Initialize calendar (V3 handles its own data fetching)
        renderCalendar();

        // Show view
        setLoading(false);
        document.getElementById('property-list-view').style.display = 'none';
        document.getElementById('property-detail-view').style.display = 'flex';

        // Update hash
        updateHash(propertyId, 'calendar');

    } catch (error) {
        console.error('Error loading property detail:', error);
        setLoading(false);
        showError('Unable to load property', error.message);
    }
}

// ============================================================================
// EVENT HANDLERS
// ============================================================================

/**
 * Initialize event listeners
 */
function initializeEventListeners() {
    // Search input
    const searchInput = document.getElementById('propertySearch');
    const searchClear = document.getElementById('searchClear');

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value;
        searchClear.style.display = query ? 'block' : 'none';
        filterProperties(query);
    });

    searchClear.addEventListener('click', () => {
        searchInput.value = '';
        searchClear.style.display = 'none';
        filterProperties('');
        searchInput.focus();
    });

    // Refresh button
    document.getElementById('refreshBtn').addEventListener('click', async () => {
        try {
            setLoading(true);
            const properties = await fetchProperties(true);
            window.AppState.properties = properties;
            window.AppState.filteredProperties = properties;

            // Re-apply search filter
            const currentQuery = searchInput.value;
            filterProperties(currentQuery);

            setLoading(false);
            document.getElementById('property-list-view').style.display = 'block';
        } catch (error) {
            console.error('Error refreshing properties:', error);
            setLoading(false);
            showError('Unable to refresh properties', error.message);
        }
    });

    // Back to properties button
    document.getElementById('backToPropertiesBtn').addEventListener('click', () => {
        loadPropertyListView();
    });

    // Calendar view selector
    const viewSelect = document.getElementById('calendarViewSelect');
    viewSelect.value = window.AppState.calendarView;

    viewSelect.addEventListener('change', (e) => {
        window.AppState.calendarView = e.target.value;
        localStorage.setItem('calendarView', e.target.value);

        // Re-render calendar with new view
        if (window.AppState.selectedProperty) {
            fetchCalendar(window.AppState.selectedProperty.id).then(renderCalendar);
        }
    });

    // Calendar refresh button
    document.getElementById('calendarRefreshBtn').addEventListener('click', async () => {
        if (window.AppState.selectedProperty) {
            try {
                const calendarData = await fetchCalendar(window.AppState.selectedProperty.id);
                renderCalendar(calendarData);
            } catch (error) {
                console.error('Error refreshing calendar:', error);
                alert('Failed to refresh calendar: ' + error.message);
            }
        }
    });

    // Retry button (error state)
    document.getElementById('retryBtn').addEventListener('click', () => {
        loadPropertyListView();
    });

    // Hash change (browser back/forward)
    window.addEventListener('hashchange', handleHashChange);
}

/**
 * Handle URL hash changes (browser back/forward)
 */
function handleHashChange() {
    const hashData = parseHash();

    if (hashData && hashData.type === 'property') {
        loadPropertyDetail(hashData.propertyId);
    } else {
        loadPropertyListView();
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

/**
 * Initialize application
 */
async function initApp() {
    console.log('Initializing Property Dashboard...');

    // Set user email
    try {
        const userEmail = await fetch(`${API_PREFIX}/user/role`)
            .then(r => r.json())
            .then(data => data.user_email || 'User');
        document.getElementById('userEmail').textContent = userEmail;
    } catch (e) {
        document.getElementById('userEmail').textContent = 'User';
    }

    // Initialize event listeners
    initializeEventListeners();

    // Check URL hash for deep linking
    const hashData = parseHash();

    if (hashData && hashData.type === 'property') {
        // Deep link to property detail
        loadPropertyDetail(hashData.propertyId);
    } else if (window.AppState.lastViewedProperty) {
        // Restore last viewed property (optional - can remove if unwanted)
        // loadPropertyDetail(window.AppState.lastViewedProperty);
        loadPropertyListView(); // Start with list view instead
    } else {
        // Default: Load property list
        loadPropertyListView();
    }
}

// Start app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
