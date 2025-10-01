// Entry point – wire everything
import "./api.js"; // just to ensure early fetch helpers in cache
import "./auth.js"; // auth system
import { initSettings } from "./settings.js";
import {wireSearchBox, applyLayout, search, loadWatchlist, selectTab} from "./ui.js";
import { initNotifications, loadNotifications } from "./notifications-ui.js";
import { state, MIN_QUERY_LEN } from "./state.js";
import { $ } from "./ui.js";
import { auth } from "./auth.js";
import { initializeQuickActions } from "./quick-actions.js";

// console.log("[MN] main.js loaded", import.meta.url);

// Pull-to-refresh functionality
let pullToRefresh = {
  startY: 0,
  currentY: 0,
  isPulling: false,
  threshold: 60,
  maxPull: 120,
  
  init() {
    // Only enable on mobile devices
    if (!this.isMobile()) return;
    
    document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
    document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
    document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: false });
    
    this.createRefreshIndicator();
  },
  
  isMobile() {
    return window.innerWidth <= 768 || /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  },
  
  createRefreshIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'pull-refresh-indicator';
    indicator.innerHTML = `
      <div class="pull-refresh-content">
        <div class="pull-refresh-icon">↓</div>
        <div class="pull-refresh-text">Pull to refresh</div>
      </div>
    `;
    document.body.insertBefore(indicator, document.body.firstChild);
  },
  
  handleTouchStart(e) {
    // Only trigger when at the top of the page
    if (window.scrollY > 0) return;
    
    this.startY = e.touches[0].clientY;
    this.isPulling = false;
  },
  
  handleTouchMove(e) {
    if (window.scrollY > 0) return;
    
    this.currentY = e.touches[0].clientY;
    const deltaY = this.currentY - this.startY;
    
    if (deltaY > 0 && !this.isPulling) {
      this.isPulling = true;
      e.preventDefault();
    }
    
    if (this.isPulling) {
      e.preventDefault();
      this.updatePullIndicator(deltaY);
    }
  },
  
  handleTouchEnd(e) {
    if (!this.isPulling) return;
    
    const deltaY = this.currentY - this.startY;
    
    if (deltaY > this.threshold) {
      this.triggerRefresh();
    } else {
      this.resetPullIndicator();
    }
    
    this.isPulling = false;
  },
  
  updatePullIndicator(deltaY) {
    const indicator = document.getElementById('pull-refresh-indicator');
    const progress = Math.min(deltaY / this.maxPull, 1);
    const opacity = Math.min(deltaY / this.threshold, 1);
    
    indicator.style.transform = `translateY(${Math.min(deltaY, this.maxPull)}px)`;
    indicator.style.opacity = opacity;
    
    const icon = indicator.querySelector('.pull-refresh-icon');
    const text = indicator.querySelector('.pull-refresh-text');
    
    if (deltaY > this.threshold) {
      icon.textContent = '↑';
      text.textContent = 'Release to refresh';
      icon.style.transform = 'rotate(180deg)';
    } else {
      icon.textContent = '↓';
      text.textContent = 'Pull to refresh';
      icon.style.transform = 'rotate(0deg)';
    }
  },
  
  resetPullIndicator() {
    const indicator = document.getElementById('pull-refresh-indicator');
    indicator.style.transform = 'translateY(-100%)';
    indicator.style.opacity = '0';
  },
  
  triggerRefresh() {
    const indicator = document.getElementById('pull-refresh-indicator');
    const icon = indicator.querySelector('.pull-refresh-icon');
    const text = indicator.querySelector('.pull-refresh-text');
    
    icon.textContent = '⟳';
    text.textContent = 'Refreshing...';
    icon.style.transform = 'rotate(0deg)';
    icon.style.animation = 'spin 1s linear infinite';
    
    // Trigger refresh based on current tab
    if (state.layout === 'tabs') {
      const activeTab = document.querySelector('.tab.active');
      if (activeTab) {
        const tabId = activeTab.id.replace('tab-', '');
        if (tabId === 'search') {
          search();
        } else if (tabId === 'watchlist') {
          loadWatchlist();
        } else if (tabId === 'notifications') {
          loadNotifications();
        }
      }
    } else {
      // Single page mode - refresh current content
      if (state.q) {
        search();
      } else {
        loadWatchlist();
      }
    }
    
    // Reset after a delay
    setTimeout(() => {
      this.resetPullIndicator();
    }, 1000);
  }
};

queueMicrotask(async () => {
  try{
    // Initialize auth first
    await auth.init();
    
    initSettings();
    wireSearchBox();
    applyLayout(state.layout);
    initNotifications();
    
    // Initialize pull-to-refresh
    pullToRefresh.init();
    
    // Initialize quick actions toolbar
    initializeQuickActions();
    
            // Wire auth UI
            $("#login-btn")?.addEventListener("click", () => $("#login-modal")?.showModal());
            $("#logout-btn")?.addEventListener("click", () => auth.logout());
            $("#login-close")?.addEventListener("click", () => $("#login-modal")?.close());
            $("#login-cancel")?.addEventListener("click", () => $("#login-modal")?.close());
            $("#create-login-btn")?.addEventListener("click", () => {
              $("#login-modal")?.close();
              window.location.href = '/setup';
            });
    
    $("#login-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const username = $("#login-username")?.value?.trim();
      const password = $("#login-password")?.value;
      const loginBtn = $("#login-form button[type='submit']");
      
      // Basic validation
      if (!username) {
        toast("Please enter a username", 2000, "error");
        $("#login-username")?.focus();
        return;
      }
      
      if (!password) {
        toast("Please enter a password", 2000, "error");
        $("#login-password")?.focus();
        return;
      }
      
      // Show loading state
      const originalText = loginBtn.innerHTML;
      loginBtn.disabled = true;
      loginBtn.innerHTML = '<span class="btn-icon">⏳</span>Logging in...';
      
      try {
        const success = await auth.login(username, password);
        if (!success) {
          // Reset button state on failure
          loginBtn.disabled = false;
          loginBtn.innerHTML = originalText;
          // Clear password field for security
          $("#login-password").value = "";
          $("#login-password").focus();
        }
      } catch (error) {
        // Reset button state on error
        loginBtn.disabled = false;
        loginBtn.innerHTML = originalText;
        // Clear password field for security
        $("#login-password").value = "";
        $("#login-password").focus();
        toast("Login failed: " + (error.message || "Unknown error"), 3000, "error");
      }
    });
    
    // Keyboard shortcuts have been removed - feature scrapped

    // initial data (only if authenticated)
    if (auth.requireAuth()) {
      await loadWatchlist();
      await loadNotifications();

      // if there is a query in URL, run a search immediately
      const qinit = $("#q")?.value.trim() || "";
      if(qinit.length >= MIN_QUERY_LEN){ state.q = qinit; state.page = 1; search(); }
    }

    // console.log("[MN] bootstrap complete");
  }catch(e){
    // console.error("[MN] bootstrap failed:", e);
  }
});
