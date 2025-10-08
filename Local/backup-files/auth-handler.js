/**
 * Frontend Authentication Handler for Wait Node Approval System
 * Manages OAuth authentication flow and session status
 */

class AuthHandler {
    constructor(backendUrl) {
        this.backendUrl = backendUrl || this.detectBackendUrl();
        this.isAuthenticated = false;
        this.user = null;
        this.checkInterval = null;
    }

    /**
     * Detect the appropriate backend URL based on environment
     */
    detectBackendUrl() {
        const hostname = window.location.hostname;
        
        if (!hostname || hostname === 'localhost' || window.location.protocol === 'file:') {
            return 'http://localhost:5678';
        }
        
        // Production URL
        return 'https://taskpages-backend.onrender.com';
    }

    /**
     * Initialize authentication check on page load
     */
    async init() {
        console.log('Initializing authentication...');
        
        // Check authentication status
        const isAuth = await this.checkAuthStatus();
        
        if (!isAuth) {
            // Not authenticated - redirect to login
            this.redirectToLogin();
        } else {
            // Authenticated - start session refresh interval
            this.startSessionRefresh();
        }
        
        return isAuth;
    }

    /**
     * Check if user is authenticated
     */
    async checkAuthStatus() {
        try {
            const response = await fetch(`${this.backendUrl}/auth/status`, {
                method: 'GET',
                credentials: 'include',  // Important: include cookies
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.isAuthenticated = data.authenticated;
                this.user = data.user || null;
                
                if (this.isAuthenticated) {
                    console.log('User authenticated:', this.user?.email);
                    this.updateUIForAuthenticatedUser();
                }
                
                return this.isAuthenticated;
            }
            
            return false;
        } catch (error) {
            console.error('Auth check failed:', error);
            return false;
        }
    }

    /**
     * Redirect to OAuth login
     */
    redirectToLogin() {
        // Store current URL to return after auth
        const currentUrl = window.location.href;
        sessionStorage.setItem('auth_return_url', currentUrl);
        
        // Show loading message
        this.showAuthMessage('Redirecting to login...');
        
        // Redirect to backend OAuth endpoint
        setTimeout(() => {
            window.location.href = `${this.backendUrl}/auth/login`;
        }, 1000);
    }

    /**
     * Handle post-authentication redirect
     */
    handleAuthCallback() {
        // Check if we just authenticated
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('auth') === 'success') {
            // Clean up URL
            window.history.replaceState({}, document.title, window.location.pathname);
            
            // Get return URL if exists
            const returnUrl = sessionStorage.getItem('auth_return_url');
            if (returnUrl && returnUrl !== window.location.href) {
                sessionStorage.removeItem('auth_return_url');
                window.location.href = returnUrl;
            } else {
                // Reload to initialize authenticated state
                window.location.reload();
            }
        }
    }

    /**
     * Logout user
     */
    async logout() {
        try {
            const response = await fetch(`${this.backendUrl}/auth/logout`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                this.isAuthenticated = false;
                this.user = null;
                
                // Redirect to login
                this.redirectToLogin();
            }
        } catch (error) {
            console.error('Logout failed:', error);
        }
    }

    /**
     * Logout from all devices
     */
    async logoutAll() {
        try {
            const response = await fetch(`${this.backendUrl}/auth/logout-all`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                this.isAuthenticated = false;
                this.user = null;
                
                // Redirect to login
                this.redirectToLogin();
            }
        } catch (error) {
            console.error('Logout all failed:', error);
        }
    }

    /**
     * Refresh session to keep it alive
     */
    async refreshSession() {
        try {
            const response = await fetch(`${this.backendUrl}/auth/refresh`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                // Session expired - redirect to login
                this.redirectToLogin();
            }
        } catch (error) {
            console.error('Session refresh failed:', error);
        }
    }

    /**
     * Start automatic session refresh
     */
    startSessionRefresh() {
        // Refresh session every 10 minutes
        this.checkInterval = setInterval(() => {
            this.refreshSession();
        }, 10 * 60 * 1000);
    }

    /**
     * Stop session refresh
     */
    stopSessionRefresh() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
    }

    /**
     * Make authenticated API request
     */
    async authenticatedFetch(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            credentials: 'include',  // Always include cookies
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        // Check if authentication failed
        if (response.status === 401) {
            // Session expired - redirect to login
            this.redirectToLogin();
            throw new Error('Authentication required');
        }

        return response;
    }

    /**
     * Update UI for authenticated user
     */
    updateUIForAuthenticatedUser() {
        // Add user info to header if element exists
        const userInfoEl = document.getElementById('user-info');
        if (userInfoEl && this.user) {
            userInfoEl.innerHTML = `
                <div class="flex items-center space-x-3">
                    ${this.user.picture ? `<img src="${this.user.picture}" alt="${this.user.name}" class="w-8 h-8 rounded-full">` : ''}
                    <span class="text-sm text-gray-700">${this.user.email}</span>
                    <button onclick="authHandler.logout()" class="text-sm text-red-600 hover:text-red-800">Logout</button>
                </div>
            `;
        }

        // Remove any auth messages
        const authMessage = document.getElementById('auth-message');
        if (authMessage) {
            authMessage.remove();
        }
    }

    /**
     * Show authentication message
     */
    showAuthMessage(message) {
        // Remove existing message if any
        const existing = document.getElementById('auth-message');
        if (existing) {
            existing.remove();
        }

        // Create message element
        const messageEl = document.createElement('div');
        messageEl.id = 'auth-message';
        messageEl.className = 'fixed inset-0 bg-white flex items-center justify-center z-50';
        messageEl.innerHTML = `
            <div class="text-center">
                <div class="spinner mx-auto mb-4"></div>
                <p class="text-lg text-gray-700">${message}</p>
            </div>
        `;

        document.body.appendChild(messageEl);
    }
}

// Initialize auth handler when DOM is ready
let authHandler;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAuth);
} else {
    initAuth();
}

async function initAuth() {
    // Create global auth handler instance
    window.authHandler = new AuthHandler();
    
    // Handle auth callback if present
    authHandler.handleAuthCallback();
    
    // Initialize authentication
    const isAuthenticated = await authHandler.init();
    
    if (isAuthenticated) {
        console.log('Authentication successful, loading application...');
        
        // Update the backend URL in the React app if it exists
        if (typeof BACKEND_URL !== 'undefined') {
            window.BACKEND_URL = authHandler.backendUrl;
        }
    }
}

// Export for use in React components
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthHandler;
}