/**
 * Debug Overlay for Property Dashboard Calendar V3
 *
 * Features:
 * - Intercepts all fetch API calls
 * - Captures calendar data transformations
 * - Monitors rendering state
 * - Provides detailed debug information
 *
 * Usage: Add ?debug=true to URL to activate
 * Integration: Single script tag in property-dashboard.html
 * Removal: Remove script tag or set debug=false
 */

(function() {
    'use strict';

    // Check if debug mode is enabled (URL param or localStorage)
    const urlParams = new URLSearchParams(window.location.search);
    const urlDebug = urlParams.get('debug') === 'true';
    const localStorageDebug = localStorage.getItem('debugMode') === 'true';
    const debugEnabled = urlDebug || localStorageDebug;

    // If URL has ?debug=true, save to localStorage so it persists through hash navigation
    if (urlDebug) {
        localStorage.setItem('debugMode', 'true');
    }

    if (!debugEnabled) {
        console.log('Debug overlay disabled. To enable:');
        console.log('  1. Add ?debug=true to URL, OR');
        console.log('  2. Run: localStorage.setItem("debugMode", "true") and reload');
        console.log('To disable: localStorage.removeItem("debugMode")');
        return;
    }

    console.log('🔍 Debug Overlay Initializing...');

    // Debug state management
    const DebugState = {
        apiCalls: [],
        calendarTransformations: [],
        renderEvents: [],
        errors: [],
        isMinimized: false,
        isPanelOpen: true,
        selectedTab: 'api',
        dragState: null
    };

    // Create debug overlay UI
    function createDebugOverlay() {
        // Remove existing overlay if present
        const existing = document.getElementById('debug-overlay-container');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.id = 'debug-overlay-container';
        overlay.innerHTML = `
            <!-- Debug Trigger Button -->
            <div id="debug-trigger" class="debug-trigger">
                <span class="debug-icon">🐛</span>
                <span class="debug-counter">0</span>
            </div>

            <!-- Debug Panel -->
            <div id="debug-panel" class="debug-panel">
                <div class="debug-header">
                    <span class="debug-title">Calendar Debug Overlay</span>
                    <div class="debug-controls">
                        <button class="debug-btn" id="debug-clear" title="Clear logs">🗑️</button>
                        <button class="debug-btn" id="debug-export" title="Export logs">💾</button>
                        <button class="debug-btn" id="debug-minimize" title="Minimize">_</button>
                        <button class="debug-btn" id="debug-close" title="Close">×</button>
                    </div>
                </div>

                <div class="debug-tabs">
                    <button class="debug-tab active" data-tab="api">API Calls</button>
                    <button class="debug-tab" data-tab="transform">Data Transform</button>
                    <button class="debug-tab" data-tab="render">Rendering</button>
                    <button class="debug-tab" data-tab="errors">Errors</button>
                    <button class="debug-tab" data-tab="state">State</button>
                </div>

                <div class="debug-content">
                    <!-- API Calls Tab -->
                    <div id="debug-api" class="debug-tab-content active">
                        <div class="debug-section-header">
                            <h3>API Calls</h3>
                            <span class="debug-count" id="api-count">0 calls</span>
                        </div>
                        <div class="debug-log" id="api-log"></div>
                    </div>

                    <!-- Data Transform Tab -->
                    <div id="debug-transform" class="debug-tab-content">
                        <div class="debug-section-header">
                            <h3>Data Transformations</h3>
                            <span class="debug-count" id="transform-count">0 transforms</span>
                        </div>
                        <div class="debug-log" id="transform-log"></div>
                    </div>

                    <!-- Rendering Tab -->
                    <div id="debug-render" class="debug-tab-content">
                        <div class="debug-section-header">
                            <h3>Render Events</h3>
                            <span class="debug-count" id="render-count">0 events</span>
                        </div>
                        <div class="debug-log" id="render-log"></div>
                    </div>

                    <!-- Errors Tab -->
                    <div id="debug-errors" class="debug-tab-content">
                        <div class="debug-section-header">
                            <h3>Errors & Warnings</h3>
                            <span class="debug-count" id="error-count">0 errors</span>
                        </div>
                        <div class="debug-log" id="error-log"></div>
                    </div>

                    <!-- State Tab -->
                    <div id="debug-state" class="debug-tab-content">
                        <div class="debug-section-header">
                            <h3>Current State</h3>
                            <button class="debug-btn-small" id="refresh-state">Refresh</button>
                        </div>
                        <div class="debug-log" id="state-log"></div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
        attachDebugStyles();
        attachEventListeners();
    }

    // Attach debug overlay styles
    function attachDebugStyles() {
        const style = document.createElement('style');
        style.id = 'debug-overlay-styles';
        style.textContent = `
            /* Debug Overlay Styles - Isolated to prevent conflicts */
            #debug-overlay-container {
                position: fixed;
                z-index: 999999;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                pointer-events: none;
            }

            #debug-overlay-container * {
                pointer-events: auto;
                box-sizing: border-box;
            }

            /* Trigger Button */
            .debug-trigger {
                position: fixed;
                bottom: 20px;
                right: 20px;
                width: 50px;
                height: 50px;
                border-radius: 50%;
                background: #1a1a1a;
                border: 2px solid #00ff00;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 12px rgba(0, 255, 0, 0.3);
            }

            .debug-trigger:hover {
                transform: scale(1.1);
                box-shadow: 0 6px 20px rgba(0, 255, 0, 0.5);
            }

            .debug-icon {
                font-size: 24px;
            }

            .debug-counter {
                position: absolute;
                top: -5px;
                right: -5px;
                background: #ff0000;
                color: white;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 10px;
                font-weight: bold;
            }

            /* Debug Panel */
            .debug-panel {
                position: fixed;
                top: 20px;
                right: 20px;
                width: 600px;
                max-width: 90vw;
                max-height: 80vh;
                background: #1a1a1a;
                border: 2px solid #00ff00;
                border-radius: 8px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8);
                display: none;
                flex-direction: column;
            }

            .debug-panel.active {
                display: flex;
            }

            .debug-panel.minimized {
                height: auto;
                max-height: none;
            }

            .debug-panel.minimized .debug-tabs,
            .debug-panel.minimized .debug-content {
                display: none;
            }

            /* Header */
            .debug-header {
                background: #0a0a0a;
                padding: 10px 15px;
                border-bottom: 1px solid #00ff00;
                display: flex;
                justify-content: space-between;
                align-items: center;
                cursor: move;
                border-radius: 6px 6px 0 0;
            }

            .debug-title {
                color: #00ff00;
                font-weight: bold;
                font-size: 14px;
            }

            .debug-controls {
                display: flex;
                gap: 5px;
            }

            .debug-btn {
                background: transparent;
                border: 1px solid #00ff00;
                color: #00ff00;
                padding: 4px 8px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
                transition: all 0.2s;
            }

            .debug-btn:hover {
                background: #00ff00;
                color: #0a0a0a;
            }

            .debug-btn-small {
                background: transparent;
                border: 1px solid #00ff00;
                color: #00ff00;
                padding: 2px 6px;
                border-radius: 3px;
                cursor: pointer;
                font-size: 10px;
            }

            /* Tabs */
            .debug-tabs {
                display: flex;
                background: #0a0a0a;
                border-bottom: 1px solid #333;
            }

            .debug-tab {
                flex: 1;
                background: transparent;
                border: none;
                color: #888;
                padding: 8px;
                cursor: pointer;
                transition: all 0.2s;
                font-size: 11px;
            }

            .debug-tab:hover {
                background: #1a1a1a;
                color: #00ff00;
            }

            .debug-tab.active {
                background: #1a1a1a;
                color: #00ff00;
                border-bottom: 2px solid #00ff00;
            }

            /* Content */
            .debug-content {
                flex: 1;
                overflow: hidden;
                position: relative;
            }

            .debug-tab-content {
                display: none;
                height: 100%;
                flex-direction: column;
            }

            .debug-tab-content.active {
                display: flex;
            }

            .debug-section-header {
                padding: 10px;
                background: #0a0a0a;
                border-bottom: 1px solid #333;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .debug-section-header h3 {
                margin: 0;
                color: #00ff00;
                font-size: 12px;
            }

            .debug-count {
                color: #888;
                font-size: 10px;
            }

            .debug-log {
                flex: 1;
                overflow-y: auto;
                padding: 10px;
                color: #ddd;
            }

            /* Log Entries */
            .debug-entry {
                margin-bottom: 15px;
                padding: 10px;
                background: #0a0a0a;
                border-radius: 4px;
                border-left: 3px solid #333;
            }

            .debug-entry.api-call {
                border-left-color: #00aaff;
            }

            .debug-entry.transform {
                border-left-color: #ffaa00;
            }

            .debug-entry.render {
                border-left-color: #00ff00;
            }

            .debug-entry.error {
                border-left-color: #ff0000;
            }

            .debug-entry-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 5px;
                cursor: pointer;
            }

            .debug-entry-title {
                font-weight: bold;
                color: #fff;
            }

            .debug-entry-time {
                color: #666;
                font-size: 10px;
            }

            .debug-entry-status {
                display: inline-block;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 10px;
                margin-left: 10px;
            }

            .status-success {
                background: #00ff00;
                color: #0a0a0a;
            }

            .status-error {
                background: #ff0000;
                color: #fff;
            }

            .status-pending {
                background: #ffaa00;
                color: #0a0a0a;
            }

            .debug-entry-details {
                margin-top: 10px;
                display: none;
            }

            .debug-entry.expanded .debug-entry-details {
                display: block;
            }

            .debug-json {
                background: #000;
                padding: 8px;
                border-radius: 4px;
                overflow-x: auto;
                font-size: 11px;
                line-height: 1.4;
                max-height: 300px;
                overflow-y: auto;
            }

            .debug-json-key {
                color: #00aaff;
            }

            .debug-json-string {
                color: #00ff00;
            }

            .debug-json-number {
                color: #ffaa00;
            }

            .debug-json-boolean {
                color: #ff00ff;
            }

            .debug-json-null {
                color: #888;
            }

            /* Scrollbar */
            .debug-log::-webkit-scrollbar,
            .debug-json::-webkit-scrollbar {
                width: 8px;
                height: 8px;
            }

            .debug-log::-webkit-scrollbar-track,
            .debug-json::-webkit-scrollbar-track {
                background: #0a0a0a;
            }

            .debug-log::-webkit-scrollbar-thumb,
            .debug-json::-webkit-scrollbar-thumb {
                background: #333;
                border-radius: 4px;
            }

            .debug-log::-webkit-scrollbar-thumb:hover,
            .debug-json::-webkit-scrollbar-thumb:hover {
                background: #555;
            }

            /* Animations */
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.5; }
                100% { opacity: 1; }
            }

            .debug-entry.new {
                animation: pulse 0.5s ease-in-out;
            }
        `;
        document.head.appendChild(style);
    }

    // Format JSON for display
    function formatJSON(obj) {
        if (!obj) return '<span class="debug-json-null">null</span>';

        try {
            return JSON.stringify(obj, null, 2)
                .replace(/("(?:[^"\\]|\\.)*")/g, '<span class="debug-json-key">$1</span>')
                .replace(/: ("(?:[^"\\]|\\.)*")/g, ': <span class="debug-json-string">$1</span>')
                .replace(/: (\d+)/g, ': <span class="debug-json-number">$1</span>')
                .replace(/: (true|false)/g, ': <span class="debug-json-boolean">$1</span>')
                .replace(/: (null)/g, ': <span class="debug-json-null">$1</span>');
        } catch (e) {
            return `<span class="debug-json-string">${String(obj)}</span>`;
        }
    }

    // Log API call
    function logAPICall(method, url, options, response, timing) {
        const entry = {
            id: Date.now(),
            type: 'api',
            method,
            url,
            options,
            response,
            timing,
            timestamp: new Date().toISOString()
        };

        DebugState.apiCalls.push(entry);
        updateAPIDisplay(entry);
        updateCounter();
    }

    // Log data transformation
    function logTransformation(stage, data, metadata = {}) {
        const entry = {
            id: Date.now(),
            type: 'transform',
            stage,
            data: JSON.parse(JSON.stringify(data)), // Deep clone
            metadata,
            timestamp: new Date().toISOString()
        };

        DebugState.calendarTransformations.push(entry);
        updateTransformDisplay(entry);
        updateCounter();
    }

    // Log render event
    function logRenderEvent(event, details) {
        const entry = {
            id: Date.now(),
            type: 'render',
            event,
            details,
            timestamp: new Date().toISOString()
        };

        DebugState.renderEvents.push(entry);
        updateRenderDisplay(entry);
        updateCounter();
    }

    // Log error
    function logError(error, context) {
        const entry = {
            id: Date.now(),
            type: 'error',
            error: {
                message: error.message,
                stack: error.stack,
                name: error.name
            },
            context,
            timestamp: new Date().toISOString()
        };

        DebugState.errors.push(entry);
        updateErrorDisplay(entry);
        updateCounter();
    }

    // Update API display
    function updateAPIDisplay(entry) {
        const log = document.getElementById('api-log');
        if (!log) return;

        const entryEl = document.createElement('div');
        entryEl.className = 'debug-entry api-call new';
        entryEl.innerHTML = `
            <div class="debug-entry-header">
                <div>
                    <span class="debug-entry-title">${entry.method} ${entry.url}</span>
                    <span class="debug-entry-status ${entry.response?.ok ? 'status-success' : 'status-error'}">
                        ${entry.response?.status || 'pending'}
                    </span>
                </div>
                <span class="debug-entry-time">${entry.timing}ms</span>
            </div>
            <div class="debug-entry-details">
                <div style="margin-bottom: 10px;">
                    <strong>Request:</strong>
                    <div class="debug-json">${formatJSON(entry.options)}</div>
                </div>
                <div>
                    <strong>Response:</strong>
                    <div class="debug-json">${formatJSON(entry.response?.data)}</div>
                </div>
            </div>
        `;

        entryEl.querySelector('.debug-entry-header').addEventListener('click', () => {
            entryEl.classList.toggle('expanded');
        });

        log.insertBefore(entryEl, log.firstChild);
        document.getElementById('api-count').textContent = `${DebugState.apiCalls.length} calls`;
    }

    // Update transformation display
    function updateTransformDisplay(entry) {
        const log = document.getElementById('transform-log');
        if (!log) return;

        const entryEl = document.createElement('div');
        entryEl.className = 'debug-entry transform new';
        entryEl.innerHTML = `
            <div class="debug-entry-header">
                <div>
                    <span class="debug-entry-title">${entry.stage}</span>
                </div>
                <span class="debug-entry-time">${new Date(entry.timestamp).toLocaleTimeString()}</span>
            </div>
            <div class="debug-entry-details">
                <div style="margin-bottom: 10px;">
                    <strong>Data:</strong>
                    <div class="debug-json">${formatJSON(entry.data)}</div>
                </div>
                ${entry.metadata ? `
                    <div>
                        <strong>Metadata:</strong>
                        <div class="debug-json">${formatJSON(entry.metadata)}</div>
                    </div>
                ` : ''}
            </div>
        `;

        entryEl.querySelector('.debug-entry-header').addEventListener('click', () => {
            entryEl.classList.toggle('expanded');
        });

        log.insertBefore(entryEl, log.firstChild);
        document.getElementById('transform-count').textContent = `${DebugState.calendarTransformations.length} transforms`;
    }

    // Update render display
    function updateRenderDisplay(entry) {
        const log = document.getElementById('render-log');
        if (!log) return;

        const entryEl = document.createElement('div');
        entryEl.className = 'debug-entry render new';
        entryEl.innerHTML = `
            <div class="debug-entry-header">
                <div>
                    <span class="debug-entry-title">${entry.event}</span>
                </div>
                <span class="debug-entry-time">${new Date(entry.timestamp).toLocaleTimeString()}</span>
            </div>
            <div class="debug-entry-details">
                <div class="debug-json">${formatJSON(entry.details)}</div>
            </div>
        `;

        entryEl.querySelector('.debug-entry-header').addEventListener('click', () => {
            entryEl.classList.toggle('expanded');
        });

        log.insertBefore(entryEl, log.firstChild);
        document.getElementById('render-count').textContent = `${DebugState.renderEvents.length} events`;
    }

    // Update error display
    function updateErrorDisplay(entry) {
        const log = document.getElementById('error-log');
        if (!log) return;

        const entryEl = document.createElement('div');
        entryEl.className = 'debug-entry error new';
        entryEl.innerHTML = `
            <div class="debug-entry-header">
                <div>
                    <span class="debug-entry-title">${entry.error.name}: ${entry.error.message}</span>
                </div>
                <span class="debug-entry-time">${new Date(entry.timestamp).toLocaleTimeString()}</span>
            </div>
            <div class="debug-entry-details">
                <div style="margin-bottom: 10px;">
                    <strong>Context:</strong>
                    <div class="debug-json">${formatJSON(entry.context)}</div>
                </div>
                <div>
                    <strong>Stack:</strong>
                    <pre style="color: #ff6666; font-size: 10px;">${entry.error.stack}</pre>
                </div>
            </div>
        `;

        entryEl.querySelector('.debug-entry-header').addEventListener('click', () => {
            entryEl.classList.toggle('expanded');
        });

        log.insertBefore(entryEl, log.firstChild);
        document.getElementById('error-count').textContent = `${DebugState.errors.length} errors`;
    }

    // Update counter
    function updateCounter() {
        const counter = document.querySelector('.debug-counter');
        if (counter) {
            const total = DebugState.apiCalls.length +
                         DebugState.calendarTransformations.length +
                         DebugState.renderEvents.length +
                         DebugState.errors.length;
            counter.textContent = total;
        }
    }

    // Attach event listeners
    function attachEventListeners() {
        // Trigger button
        const trigger = document.getElementById('debug-trigger');
        trigger.addEventListener('click', () => {
            const panel = document.getElementById('debug-panel');
            panel.classList.toggle('active');
            DebugState.isPanelOpen = panel.classList.contains('active');
        });

        // Panel controls
        document.getElementById('debug-close').addEventListener('click', () => {
            document.getElementById('debug-panel').classList.remove('active');
            DebugState.isPanelOpen = false;
        });

        document.getElementById('debug-minimize').addEventListener('click', () => {
            const panel = document.getElementById('debug-panel');
            panel.classList.toggle('minimized');
            DebugState.isMinimized = panel.classList.contains('minimized');
        });

        document.getElementById('debug-clear').addEventListener('click', () => {
            DebugState.apiCalls = [];
            DebugState.calendarTransformations = [];
            DebugState.renderEvents = [];
            DebugState.errors = [];
            document.querySelectorAll('.debug-log').forEach(log => log.innerHTML = '');
            document.querySelectorAll('.debug-count').forEach(count => {
                if (count.id !== 'api-count' && count.id !== 'transform-count' &&
                    count.id !== 'render-count' && count.id !== 'error-count') return;
                count.textContent = '0';
            });
            updateCounter();
        });

        document.getElementById('debug-export').addEventListener('click', () => {
            const exportData = {
                timestamp: new Date().toISOString(),
                apiCalls: DebugState.apiCalls,
                transformations: DebugState.calendarTransformations,
                renderEvents: DebugState.renderEvents,
                errors: DebugState.errors
            };

            const blob = new Blob([JSON.stringify(exportData, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `calendar-debug-${Date.now()}.json`;
            a.click();
            URL.revokeObjectURL(url);
        });

        // Tab switching
        document.querySelectorAll('.debug-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.dataset.tab;

                // Update tabs
                document.querySelectorAll('.debug-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                // Update content
                document.querySelectorAll('.debug-tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                document.getElementById(`debug-${tabName}`).classList.add('active');

                DebugState.selectedTab = tabName;
            });
        });

        // State refresh
        document.getElementById('refresh-state').addEventListener('click', () => {
            updateStateDisplay();
        });

        // Make panel draggable
        makeDraggable(document.getElementById('debug-panel'), document.querySelector('.debug-header'));
    }

    // Make element draggable
    function makeDraggable(element, handle) {
        let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;

        handle.onmousedown = dragMouseDown;

        function dragMouseDown(e) {
            e = e || window.event;
            e.preventDefault();
            pos3 = e.clientX;
            pos4 = e.clientY;
            document.onmouseup = closeDragElement;
            document.onmousemove = elementDrag;
        }

        function elementDrag(e) {
            e = e || window.event;
            e.preventDefault();
            pos1 = pos3 - e.clientX;
            pos2 = pos4 - e.clientY;
            pos3 = e.clientX;
            pos4 = e.clientY;
            element.style.top = (element.offsetTop - pos2) + "px";
            element.style.left = (element.offsetLeft - pos1) + "px";
            element.style.right = 'auto';
        }

        function closeDragElement() {
            document.onmouseup = null;
            document.onmousemove = null;
        }
    }

    // Update state display
    function updateStateDisplay() {
        const log = document.getElementById('state-log');
        if (!log) return;

        const state = {
            CalendarState: window.CalendarState || 'Not found',
            CalendarModuleV3: window.CalendarModuleV3 ? 'Loaded' : 'Not loaded',
            CalendarDataModel: window.CalendarDataModel ? 'Loaded' : 'Not loaded',
            currentProperty: window.currentPropertyId || 'None',
            apiCalls: DebugState.apiCalls.length,
            transformations: DebugState.calendarTransformations.length,
            renderEvents: DebugState.renderEvents.length,
            errors: DebugState.errors.length
        };

        log.innerHTML = `
            <div class="debug-json">${formatJSON(state)}</div>
            ${window.CalendarState ? `
                <div style="margin-top: 15px;">
                    <strong>CalendarState Details:</strong>
                    <div class="debug-json">${formatJSON(window.CalendarState)}</div>
                </div>
            ` : ''}
        `;
    }

    // Intercept fetch API
    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
        const [url, options = {}] = args;
        const startTime = performance.now();

        console.log(`🔍 [Debug] Fetch intercepted: ${options.method || 'GET'} ${url}`);

        try {
            const response = await originalFetch.apply(this, args);
            const endTime = performance.now();
            const timing = Math.round(endTime - startTime);

            // Clone response to read body
            const clonedResponse = response.clone();
            const responseData = await clonedResponse.json().catch(() => null);

            logAPICall(
                options.method || 'GET',
                url,
                options,
                {
                    ok: response.ok,
                    status: response.status,
                    statusText: response.statusText,
                    headers: Object.fromEntries(response.headers.entries()),
                    data: responseData
                },
                timing
            );

            return response;
        } catch (error) {
            const endTime = performance.now();
            const timing = Math.round(endTime - startTime);

            logAPICall(
                options.method || 'GET',
                url,
                options,
                {
                    ok: false,
                    error: error.message
                },
                timing
            );

            logError(error, { url, options });
            throw error;
        }
    };

    // Hook into CalendarModuleV3
    function hookCalendarModule() {
        if (!window.CalendarModuleV3) {
            console.warn('CalendarModuleV3 not found, retrying...');
            setTimeout(hookCalendarModule, 500);
            return;
        }

        console.log('🔍 Hooking into CalendarModuleV3...');

        // Hook initializeCalendar
        const originalInitialize = window.CalendarModuleV3.initializeCalendar;
        window.CalendarModuleV3.initializeCalendar = function(propertyId) {
            console.log('🔍 [Debug] initializeCalendar called with:', propertyId);
            logRenderEvent('initializeCalendar', { propertyId });
            return originalInitialize.call(this, propertyId);
        };

        // Hook loadCalendar
        const originalLoadCalendar = window.CalendarModuleV3.loadCalendar;
        window.CalendarModuleV3.loadCalendar = async function() {
            console.log('🔍 [Debug] loadCalendar called');
            logRenderEvent('loadCalendar:start', { state: window.CalendarState });

            try {
                const result = await originalLoadCalendar.call(this);
                logRenderEvent('loadCalendar:complete', {
                    success: true,
                    state: window.CalendarState
                });
                return result;
            } catch (error) {
                logError(error, { function: 'loadCalendar' });
                throw error;
            }
        };

        // Hook fetchCalendarEvents
        const originalFetchEvents = window.CalendarModuleV3.fetchCalendarEvents;
        window.CalendarModuleV3.fetchCalendarEvents = async function(propertyId) {
            console.log('🔍 [Debug] fetchCalendarEvents called with:', propertyId);
            logRenderEvent('fetchCalendarEvents:start', { propertyId });

            try {
                const events = await originalFetchEvents.call(this, propertyId);
                logTransformation('fetchCalendarEvents:result', events, {
                    count: events?.length || 0,
                    propertyId
                });
                return events;
            } catch (error) {
                logError(error, { function: 'fetchCalendarEvents', propertyId });
                throw error;
            }
        };

        // Hook renderCalendar
        const originalRenderCalendar = window.CalendarModuleV3.renderCalendar;
        window.CalendarModuleV3.renderCalendar = function() {
            console.log('🔍 [Debug] renderCalendar called');
            const calendarState = window.CalendarState;

            logRenderEvent('renderCalendar:start', {
                hasCalendarData: !!calendarState?.calendarData,
                monthsCount: calendarState?.calendarData ? Object.keys(calendarState.calendarData).length : 0,
                currentView: calendarState?.currentView
            });

            try {
                const result = originalRenderCalendar.call(this);

                // Check DOM after render
                const calendarContent = document.getElementById('calendarContent');
                const dayElements = calendarContent ? calendarContent.querySelectorAll('.calendar-day') : [];
                const eventElements = calendarContent ? calendarContent.querySelectorAll('.calendar-event') : [];

                logRenderEvent('renderCalendar:complete', {
                    success: true,
                    domElements: {
                        calendarContent: !!calendarContent,
                        dayElements: dayElements.length,
                        eventElements: eventElements.length
                    }
                });

                return result;
            } catch (error) {
                logError(error, { function: 'renderCalendar' });
                throw error;
            }
        };
    }

    // Hook into CalendarDataModel
    function hookCalendarDataModel() {
        if (!window.CalendarDataModel) {
            console.warn('CalendarDataModel not found, retrying...');
            setTimeout(hookCalendarDataModel, 500);
            return;
        }

        console.log('🔍 Hooking into CalendarDataModel...');

        // Hook buildCalendarData
        const originalBuildCalendarData = window.CalendarDataModel.buildCalendarData;
        window.CalendarDataModel.buildCalendarData = function(eventsData, monthsToShow = 1) {
            console.log('🔍 [Debug] buildCalendarData called with:', {
                eventsCount: eventsData?.length || 0,
                monthsToShow
            });

            logTransformation('buildCalendarData:input', eventsData, {
                count: eventsData?.length || 0,
                monthsToShow
            });

            try {
                const result = originalBuildCalendarData.call(this, eventsData, monthsToShow);

                logTransformation('buildCalendarData:output', result, {
                    monthKeys: Object.keys(result || {}),
                    totalDays: Object.values(result || {}).reduce((sum, month) =>
                        sum + (month.days ? month.days.length : 0), 0)
                });

                return result;
            } catch (error) {
                logError(error, { function: 'buildCalendarData', eventsData, monthsToShow });
                throw error;
            }
        };

        // Hook createEventObject if it exists
        if (window.CalendarDataModel.createEventObject) {
            const originalCreateEvent = window.CalendarDataModel.createEventObject;
            window.CalendarDataModel.createEventObject = function(task) {
                try {
                    const result = originalCreateEvent.call(this, task);
                    logTransformation('createEventObject', result, {
                        taskId: task?.id,
                        taskName: task?.name
                    });
                    return result;
                } catch (error) {
                    logError(error, { function: 'createEventObject', task });
                    throw error;
                }
            };
        }
    }

    // Override console methods to capture logs
    const originalConsoleError = console.error;
    console.error = function(...args) {
        logError(new Error(args.join(' ')), { source: 'console.error', args });
        originalConsoleError.apply(console, args);
    };

    const originalConsoleWarn = console.warn;
    console.warn = function(...args) {
        if (args[0] && args[0].includes('[Debug]')) {
            // Don't log our own debug messages
            originalConsoleWarn.apply(console, args);
            return;
        }
        logError(new Error(args.join(' ')), { source: 'console.warn', args });
        originalConsoleWarn.apply(console, args);
    };

    // Initialize debug overlay
    function initialize() {
        createDebugOverlay();
        hookCalendarModule();
        hookCalendarDataModel();

        // Initial state capture
        setTimeout(() => {
            updateStateDisplay();
            logRenderEvent('DebugOverlay:initialized', {
                url: window.location.href,
                userAgent: navigator.userAgent,
                timestamp: new Date().toISOString()
            });
        }, 1000);

        console.log('✅ Debug Overlay Ready - Click the bug icon in the bottom-right corner');
    }

    // Start initialization
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }

    // Expose debug functions globally
    window.DebugOverlay = {
        state: DebugState,
        logAPICall,
        logTransformation,
        logRenderEvent,
        logError,
        exportLogs: () => {
            document.getElementById('debug-export').click();
        },
        clearLogs: () => {
            document.getElementById('debug-clear').click();
        }
    };

})();