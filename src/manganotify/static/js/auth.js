// src/manganotify/static/js/auth.js
import api from "./api.js";
import { toast, $ } from "./ui.js";

export const auth = {
  isAuthenticated: false,
  user: null,
  authEnabled: false,

  async init() {
    try {
      const status = await api.authStatus();
      this.authEnabled = status.auth_enabled;
      
      if (!this.authEnabled) {
        // Check if setup is needed
        const setupStatus = await this.checkSetupStatus();
        if (setupStatus.needsSetup) {
          this.showSetupPrompt();
          return;
        }
        
        this.isAuthenticated = true; // No auth required
        this.user = { username: "anonymous" };
        this.updateUI();
        return;
      }

      // Check if we have a token and it's valid
      const token = localStorage.getItem('auth_token');
      if (token) {
        try {
          const user = await api.getMe();
          this.isAuthenticated = true;
          this.user = user;
        } catch (e) {
          // Token invalid, clear it
          localStorage.removeItem('auth_token');
          this.isAuthenticated = false;
          this.user = null;
        }
      }
      
      // Always update UI after checking auth status
      this.updateUI();
    } catch (e) {
      // console.error("Auth init failed:", e);
    }
  },

  async checkSetupStatus() {
    try {
      const response = await fetch('/api/setup/status');
      const status = await response.json();
      return {
        needsSetup: !status.is_configured,
        status: status
      };
    } catch (e) {
      // console.error("Failed to check setup status:", e);
      return { needsSetup: false };
    }
  },

  showSetupPrompt() {
    // Create a setup prompt modal
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
      <div class="modal-card setup-prompt">
        <div class="modal-header">
          <h2>🔧 Welcome to MangaNotify!</h2>
          <p>Let's set up your secure configuration</p>
        </div>
        <div class="modal-body">
          <p>MangaNotify needs to be configured before you can start using it. This includes setting up authentication and optionally configuring notifications.</p>
          <div class="setup-options">
            <button class="btn btn-primary setup-wizard-btn">
              🚀 Start Setup Wizard
            </button>
            <button class="btn btn-secondary skip-setup-btn">
              ⏭️ Skip for Now
            </button>
          </div>
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
    
    // Add event listeners
    modal.querySelector('.setup-wizard-btn').addEventListener('click', () => {
      document.body.removeChild(modal);
      window.location.href = '/setup';
    });
    
    modal.querySelector('.skip-setup-btn').addEventListener('click', () => {
      document.body.removeChild(modal);
      this.isAuthenticated = true;
      this.user = { username: "anonymous" };
      this.updateUI();
    });
  },

  async login(username, password) {
    try {
      const response = await api.login(username, password);
      localStorage.setItem('auth_token', response.access_token);
      this.isAuthenticated = true;
      this.user = { username };
      this.updateUI();
      toast("Logged in successfully", 2200, "success");
      
      // Close the login modal
      $("#login-modal")?.close();
      
      // Auto-refresh data after successful login
      await this.refreshData();
      
      return true;
    } catch (e) {
      toast("Login failed: " + (e.message || "Invalid credentials"), 3000, "error");
      return false;
    }
  },

  async logout() {
    try {
      await api.logout();
    } catch (e) {
      // Ignore logout errors
    }
    localStorage.removeItem('auth_token');
    this.isAuthenticated = false;
    this.user = null;
    this.updateUI();
    toast("Logged out", 2200, "success");
  },

  async refreshData() {
    try {
      // Import the functions we need
      const { loadWatchlist, loadNotifications } = await import('./ui.js');
      const { loadNotifications: loadNotificationsUI } = await import('./notifications-ui.js');
      
      // Load watchlist and notifications
      await Promise.all([
        loadWatchlist(),
        loadNotificationsUI()
      ]);
      
      // console.log("Data refreshed after login");
    } catch (e) {
      // console.error("Failed to refresh data after login:", e);
    }
  },

  updateUI() {
    const loginBtn = $("#login-btn");
    const logoutBtn = $("#logout-btn");
    const userInfo = $("#user-info");
    const loginModal = $("#login-modal");

    if (this.authEnabled) {
      if (this.isAuthenticated) {
        if (loginBtn) loginBtn.style.display = "none";
        if (logoutBtn) logoutBtn.style.display = "inline-block";
        if (userInfo) {
          userInfo.textContent = `Logged in as ${this.user.username}`;
          userInfo.style.display = "inline-block";
        }
        if (loginModal) loginModal.close();
      } else {
        if (loginBtn) loginBtn.style.display = "inline-block";
        if (logoutBtn) logoutBtn.style.display = "none";
        if (userInfo) userInfo.style.display = "none";
        if (loginModal) loginModal.showModal();
      }
    } else {
      // Auth disabled, hide all auth UI
      if (loginBtn) loginBtn.style.display = "none";
      if (logoutBtn) logoutBtn.style.display = "none";
      if (userInfo) userInfo.style.display = "none";
    }
  },

  requireAuth() {
    if (this.authEnabled && !this.isAuthenticated) {
      $("#login-modal")?.showModal();
      return false;
    }
    return true;
  }
};

// Auth initialization is handled by main.js
