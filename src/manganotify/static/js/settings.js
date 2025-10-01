import { state } from "./state.js";
import api from "./api.js";
import { applyLayout, selectTab, restoreFromUrl, syncUrl, toast, $, $$ } from "./ui.js";
import { loadWatchlist } from "./ui.js";
import { loadNotifications } from "./notifications-ui.js";

export function initSettings(){
  /* Theme */
  (function initTheme(){
    const saved = localStorage.getItem("mn-theme");
    if(saved){ document.documentElement.setAttribute("data-theme", saved); }
    const toggle = ()=>{
      const cur = document.documentElement.getAttribute("data-theme");
      const next = cur === "light" ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("mn-theme", next);
    };
    $("#theme-alt")?.addEventListener("click", toggle);
  $("#theme")?.addEventListener("click", toggle);
  })();

  /* Network chip + enable/disable some buttons */
  function updateNet(){
    state.online = navigator.onLine;
    const el=$("#net"); if(el){ el.textContent = state.online ? "Online" : "Offline"; el.style.color = state.online ? "#16a34a" : "#ef4444"; }
    ["go","refresh","refresh-now","notify-test","bulk-mark-latest","export"].forEach(id=>{
      const n=$("#"+id); if(n) n.disabled = !state.online && id!=="export";
    });
  }
  window.addEventListener("online",  updateNet);
  window.addEventListener("offline", updateNet);
  updateNet();

  /* Watchlist status filter */
  const wlFilter = document.getElementById("wl-status-filter");
  if(wlFilter){
    // restore persisted UI selection
    wlFilter.value = localStorage.getItem("mn-wl-status") || "";
    wlFilter.addEventListener("change", ()=>{
      localStorage.setItem("mn-wl-status", wlFilter.value || "");
      // no need to sync to URL; just reload the list
      import("./ui.js").then(m => m.loadWatchlist());
    });
  }

  /* Filters */
  function persistFilters(){
    localStorage.setItem("mn-f-status", state.filters.status || "");
    localStorage.setItem("mn-f-type", state.filters.type || "");
    localStorage.setItem("mn-f-has-anime", String(!!state.filters.has_anime));
    localStorage.setItem("mn-f-cr", state.filters.content_rating || "");
  }
  $("#f-status")?.addEventListener("change", e=>{ state.filters.status = e.target.value || ""; persistFilters(); if(state.q) syncUrl(); });
  $("#f-type")?.addEventListener("change", e=>{ state.filters.type = e.target.value || ""; persistFilters(); if(state.q) syncUrl(); });
  $("#f-has-anime")?.addEventListener("change", e=>{ state.filters.has_anime = !!e.target.checked; persistFilters(); if(state.q) syncUrl(); });
  $("#f-cr")?.addEventListener("change", e=>{ state.filters.content_rating = e.target.value || ""; persistFilters(); if(state.q) syncUrl(); });
  $("#f-clear")?.addEventListener("click", ()=>{
    state.filters = { status:"", type:"", has_anime:false, content_rating:"" };
    $("#f-status").value=""; $("#f-type").value=""; $("#f-has-anime").checked=false; $("#f-cr").value="";
    persistFilters(); if(state.q) syncUrl();
  });

  /* Settings drawer */
  const drawer = $("#settings-drawer");
  const openSettings = ()=>{ drawer.classList.add("open"); drawer.setAttribute("aria-hidden","false"); $("#open-settings")?.setAttribute("aria-expanded","true"); };
  const closeSettings = ()=>{ drawer.classList.remove("open"); drawer.setAttribute("aria-hidden","true"); $("#open-settings")?.setAttribute("aria-expanded","false"); };
  $("#open-settings")?.addEventListener("click", openSettings);
  $("#open-settings-2")?.addEventListener("click", openSettings);
  $("#close-settings")?.addEventListener("click", closeSettings);
  window.addEventListener("keydown",(e)=>{ if(e.key==="Escape") closeSettings(); });

  /* Layout / Tabs */
  $("#layout-alt")?.addEventListener("change", e=>{ applyLayout(e.target.value); });
  $("#tab-watch")?.addEventListener("click", ()=> selectTab("watch"));
  $("#tab-search")?.addEventListener("click", ()=> selectTab("search"));
  $("#tab-notif")?.addEventListener("click", ()=> selectTab("notif"));

  /* Sorting / toggles */
  $("#sort-by")?.addEventListener("change", e=>{ 
    state.sortBy = e.target.value; 
    localStorage.setItem("mn-sort-by", state.sortBy); 
    updateCustomOrderUI();
    loadWatchlist(); 
  });
  $("#sort-dir")?.addEventListener("click", ()=>{ state.sortDir = state.sortDir==="asc" ? "desc" : "asc"; $("#sort-dir").textContent = state.sortDir==="asc" ? "⬆︎" : "⬇︎"; localStorage.setItem("mn-sort-dir", state.sortDir); loadWatchlist(); });
  
  // Clear custom order button
  $("#clear-custom-order")?.addEventListener("click", () => {
    localStorage.removeItem('mn-custom-order');
    state.sortBy = 'title'; // Switch back to title sort
    localStorage.setItem('mn-sort-by', 'title');
    $("#sort-by").value = 'title';
    updateCustomOrderUI();
    loadWatchlist();
    toast('Custom order cleared', 1500, 'success');
  });
  
  // Initialize custom order UI
  updateCustomOrderUI();
  
  // Import button functionality
  $("#import-btn")?.addEventListener("click", () => {
    $("#import-file")?.click();
  });
  
  $("#import-file")?.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      
      // Validate the imported data structure
      if (!Array.isArray(data)) {
        throw new Error("Invalid file format");
      }
      
      // Import the watchlist
      await api.importWatchlist(data);
      await loadWatchlist();
      toast("Watchlist imported successfully", 2000, "success");
      
    } catch (error) {
      console.error("Import failed:", error);
      toast("Import failed: " + error.message, 3000, "error");
    }
    
    // Reset the file input
    e.target.value = "";
  });
  $("#unread-only") && ($("#unread-only").checked = state.unreadOnly);
  $("#unread-only")?.addEventListener("change", e=>{ state.unreadOnly = !!e.target.checked; localStorage.setItem("mn-unread-only", String(state.unreadOnly)); loadWatchlist(); });
  $("#show-covers") && ($("#show-covers").checked = state.showCovers);
  $("#show-covers")?.addEventListener("change", e=>{ state.showCovers = !!e.target.checked; localStorage.setItem("mn-show-covers", String(state.showCovers)); loadWatchlist(); });

  // Hide dropped toggle
  $("#hide-dropped") && ($("#hide-dropped").checked = state.hideDropped);
  $("#hide-dropped-settings") && ($("#hide-dropped-settings").checked = state.hideDropped);
  $("#hide-dropped")?.addEventListener("change", e=>{ state.hideDropped = !!e.target.checked; localStorage.setItem("mn-hide-dropped", String(state.hideDropped)); loadWatchlist(); });
  $("#hide-dropped-settings")?.addEventListener("change", e=>{ state.hideDropped = !!e.target.checked; localStorage.setItem("mn-hide-dropped", String(state.hideDropped)); loadWatchlist(); });

  // Emoji toggle
  $("#use-emojis") && ($("#use-emojis").checked = state.useEmojis);
  $("#use-emojis")?.addEventListener("change", e=>{ 
    state.useEmojis = !!e.target.checked; 
    localStorage.setItem("mn-use-emojis", String(state.useEmojis)); 
    // Update settings button icon
    updateSettingsIcon();
    // Refresh UI to apply emoji changes
    loadWatchlist();
    loadNotifications();
  });
  
  // Update settings button icon based on emoji preference
  function updateSettingsIcon() {
    const icon = $("#settings-icon");
    if (icon) {
      icon.textContent = state.useEmojis ? "⚙️" : "⚙";
    }
  }
  
  // Initialize settings icon
  updateSettingsIcon();

  /* Layout Density */
  $("#layout-density") && ($("#layout-density").value = state.layoutDensity);
  $("#layout-density")?.addEventListener("change", e=>{ 
    state.layoutDensity = e.target.value; 
    localStorage.setItem("mn-layout-density", state.layoutDensity); 
    applyLayoutDensity();
  });

  /* Font Size */
  $("#font-size") && ($("#font-size").value = state.fontSize);
  $("#font-size")?.addEventListener("change", e=>{ 
    state.fontSize = e.target.value; 
    localStorage.setItem("mn-font-size", state.fontSize); 
    applyFontSize();
  });

  /* Custom Accent Color */
  $("#accent-color") && ($("#accent-color").value = state.customAccentColor || "#7c9cff");
  $("#accent-color")?.addEventListener("change", e=>{ 
    state.customAccentColor = e.target.value; 
    localStorage.setItem("mn-custom-accent", state.customAccentColor); 
    applyCustomAccentColor();
  });
  $("#reset-accent")?.addEventListener("click", ()=>{ 
    state.customAccentColor = ""; 
    localStorage.removeItem("mn-custom-accent"); 
    $("#accent-color").value = "#7c9cff";
    applyCustomAccentColor();
  });

  /* Information Display Toggles */
  $("#show-ids") && ($("#show-ids").checked = state.showIds);
  $("#show-ids")?.addEventListener("change", e=>{ 
    state.showIds = !!e.target.checked; 
    localStorage.setItem("mn-show-ids", String(state.showIds)); 
    loadWatchlist();
  });

  $("#show-last-checked") && ($("#show-last-checked").checked = state.showLastChecked);
  $("#show-last-checked")?.addEventListener("change", e=>{ 
    state.showLastChecked = !!e.target.checked; 
    localStorage.setItem("mn-show-last-checked", String(state.showLastChecked)); 
    loadWatchlist();
  });

  $("#show-content-rating") && ($("#show-content-rating").checked = state.showContentRating);
  $("#show-content-rating")?.addEventListener("change", e=>{ 
    state.showContentRating = !!e.target.checked; 
    localStorage.setItem("mn-show-content-rating", String(state.showContentRating)); 
    loadWatchlist();
  });

  $("#show-status") && ($("#show-status").checked = state.showStatus);
  $("#show-status")?.addEventListener("change", e=>{ 
    state.showStatus = !!e.target.checked; 
    localStorage.setItem("mn-show-status", String(state.showStatus)); 
    loadWatchlist();
  });

  /* Quiet Hours */
  $("#quiet-hours-enabled") && ($("#quiet-hours-enabled").checked = state.quietHoursEnabled);
  $("#quiet-hours-enabled")?.addEventListener("change", e=>{ 
    state.quietHoursEnabled = !!e.target.checked; 
    localStorage.setItem("mn-quiet-hours-enabled", String(state.quietHoursEnabled)); 
  });

  $("#quiet-hours-start") && ($("#quiet-hours-start").value = state.quietHoursStart);
  $("#quiet-hours-start")?.addEventListener("change", e=>{ 
    state.quietHoursStart = e.target.value; 
    localStorage.setItem("mn-quiet-hours-start", state.quietHoursStart); 
  });

  $("#quiet-hours-end") && ($("#quiet-hours-end").value = state.quietHoursEnd);
  $("#quiet-hours-end")?.addEventListener("change", e=>{ 
    state.quietHoursEnd = e.target.value; 
    localStorage.setItem("mn-quiet-hours-end", state.quietHoursEnd); 
  });

  /* Notification Batching */
  $("#notification-batching") && ($("#notification-batching").value = state.notificationBatching);
  $("#notification-batching")?.addEventListener("change", e=>{ 
    state.notificationBatching = e.target.value; 
    localStorage.setItem("mn-notification-batching", state.notificationBatching); 
  });

  /* Auto refresh + ticker */
  function refreshTicker(){
    const el=$("#last-refresh");
    if(!state.lastRefreshTs){ el.hidden=true; return; }
    el.hidden=false;
    const s=Math.max(0,Math.floor((Date.now()-state.lastRefreshTs)/1000));
    el.textContent = `Refreshed ${s}s ago`;
  }
  setInterval(refreshTicker, 1000);

  function setAutoRefresh(sec){
    localStorage.setItem("mn-auto-refresh", String(sec));
    state.autoRefresh = +sec;
    if(state.autoTimer){ clearInterval(state.autoTimer); state.autoTimer=null; }
    if(state.autoRefresh>0){ state.autoTimer = setInterval(loadWatchlist, state.autoRefresh*1000); }
  }
  $("#auto-refresh") && ($("#auto-refresh").value = String(state.autoRefresh));
  $("#auto-refresh")?.addEventListener("change", e=> setAutoRefresh(+e.target.value));

  /* Watchlist actions */
  $("#refresh")?.addEventListener("click", ()=> loadWatchlist());
  $("#refresh-now")?.addEventListener("click", async ()=>{
    try{ await api.refreshNow(); toast("Server refresh requested", 2200, "success"); }catch(e){ toast(`Failed: ${e}`,3000, "error"); }
  });
  $("#bulk-mark-latest")?.addEventListener("click", async ()=>{
    const rows = $$("#watchlist .watch-item"); let ok=0, fail=0;
    await Promise.all(rows.map(async row=>{
      const b=row.querySelector("[data-latest]"); if(!b) return;
      const id=b.getAttribute("data-latest");
      const meta = row.querySelector(".subline")?.textContent || "";
      const m = meta.match(/Chapters:\s+(\d+)/i); const total = m?+m[1]:null;
      if(total===null) return;
      try{ await api.setProgress(id,{ last_read: total }); ok++; } catch{ fail++; }
    }));
    toast(`Marked latest · OK ${ok}${fail?` · Failed ${fail}`:""}`, 3000, fail > 0 ? "warning" : "success"); loadWatchlist();
  });

  /* Notifications controls */
  $("#notif-reload")?.addEventListener("click", loadNotifications);
  $("#notif-clear")?.addEventListener("click", async ()=>{ try{ await api.clearNotifications(); toast("Cleared", 2200, "success"); }catch(e){ toast(`Failed: ${e}`,3000, "error");} loadNotifications(); });
  $("#notify-test")?.addEventListener("click", async ()=>{ try{ await api.notifyTest(); toast("Test sent", 2200, "success"); }catch(e){ toast(`Failed: ${e}`,3000, "error");} loadNotifications(); });

  // --- Discord Notifications ---
  function updateDiscordTestBtn() {
    const enabled = $("#discord-enabled").checked;
    const url = $("#discord-webhook").value.trim();
    $("#discord-test").disabled = !(enabled && url.length > 0);
  }
  function setDiscordStatus(text, type="") {
    const el = $("#discord-status");
    el.textContent = text;
    el.style.display = text ? "" : "none";
    el.style.background = "";
    el.style.color = "";
    if (type === "ok") {
      el.style.background = "#5865F2";
      el.style.color = "#fff";
    } else if (type === "error") {
      el.style.background = "#ef4444";
      el.style.color = "#fff";
    } else if (type === "testing") {
      el.style.background = "#fbbf24";
      el.style.color = "#222";
    }
    el.setAttribute("aria-live", "polite");
  }
  async function loadDiscordSettings() {
    try {
      const js = await api.getDiscordSettings();
      $("#discord-webhook").value = js.webhook_url || "";
      $("#discord-enabled").checked = !!js.enabled;
      updateDiscordTestBtn();
      setDiscordStatus(js.enabled && js.webhook_url ? "Enabled" : "", js.enabled && js.webhook_url ? "ok" : "");
    } catch {}
  }
  async function saveDiscordSettings() {
    const webhook_url = $("#discord-webhook").value.trim();
    const enabled = $("#discord-enabled").checked;
    if (enabled && !/^https:\/\/discord\.com\/api\/webhooks\//.test(webhook_url)) {
      toast("Invalid Discord webhook URL", 3000);
      setDiscordStatus("Invalid URL", "error");
      $("#discord-webhook").focus();
      updateDiscordTestBtn();
      return;
    }
    try {
      await api.setDiscordSettings({ webhook_url, enabled });
      toast("Discord settings saved", 2200, "success");
      setDiscordStatus(enabled && webhook_url ? "Enabled" : "", enabled && webhook_url ? "ok" : "");
    } catch(e) {
      toast("Failed to save Discord settings", 3000, "error");
      setDiscordStatus("Save failed", "error");
      $("#discord-webhook").focus();
    }
    updateDiscordTestBtn();
  }
  $("#discord-webhook")?.addEventListener("input", ()=>{ updateDiscordTestBtn(); });
  $("#discord-webhook")?.addEventListener("change", saveDiscordSettings);
  $("#discord-enabled")?.addEventListener("change", ()=>{ saveDiscordSettings(); updateDiscordTestBtn(); });
  $("#discord-test")?.addEventListener("click", async ()=>{
    setDiscordStatus("Testing…", "testing");
    try {
      await api.discordTest();
      toast("Discord test sent", 2200, "success");
      setDiscordStatus("Test sent!", "ok");
    } catch(e) {
      toast("Failed to send Discord test", 3000, "error");
      setDiscordStatus("Test failed", "error");
    }
  });
  loadDiscordSettings();
  
  // Debug toggle button
  $("#debug-toggle")?.addEventListener("click", () => {
    const debugSection = document.getElementById("debug-section");
    const debugToggle = document.getElementById("debug-toggle");
    if (debugSection && debugToggle) {
      const isHidden = debugSection.style.display === "none";
      debugSection.style.display = isHidden ? "block" : "none";
      debugToggle.setAttribute("aria-expanded", isHidden ? "true" : "false");
    }
  });
  
  // Debug clear button
  $("#debug-clear")?.addEventListener("click", () => {
    const debugLog = document.getElementById("debug-log");
    if (debugLog) {
      debugLog.textContent = "";
      toast("Debug log cleared", 2000, "success");
    }
  });
  
  // Debug download button
  $("#debug-download")?.addEventListener("click", () => {
    const debugLog = document.getElementById("debug-log");
    if (debugLog) {
      const logContent = debugLog.textContent;
      if (logContent.trim()) {
        const blob = new Blob([logContent], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `manganotify-debug-${new Date().toISOString().split('T')[0]}.log`;
        a.click();
        URL.revokeObjectURL(url);
        toast("Debug log downloaded", 2000, "success");
      } else {
        toast("Debug log is empty", 2000, "warning");
      }
    }
  });

  // initial UI reflect
  $("#sort-dir").textContent = state.sortDir==="asc" ? "⬆︎" : "⬇︎";
  $("#sort-by") && ($("#sort-by").value = state.sortBy);
  $("#layout-alt") && ($("#layout-alt").value = state.layout);

  // URL → controls
  restoreFromUrl();
  
  // Initialize all custom settings
  applyLayoutDensity();
  applyFontSize();
  applyCustomAccentColor();
  
  // Export button functionality
  const exportBtn = document.getElementById('export');
  if (exportBtn) {
    exportBtn.addEventListener('click', async () => {
      try {
        // Get the full watchlist using the API helper
        const data = await api.watchlist();
        
        // Create export data
        const exportData = data.data.map(item => ({
          title: item.title,
          status: item.status,
          last_read: item.last_read,
          total_chapters: item.total_chapters,
          id: item.id,
          added_at: item.added_at,
          last_checked: item.last_checked,
          cover: item.cover,
          content_rating: item.content_rating,
          authors: item.authors,
          artists: item.artists,
          links: item.links,
          relationships: item.relationships,
          last_chapter_at: item.last_chapter_at
        }));
        
        // Download as JSON file
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `manganotify-watchlist-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
        
        // Show success message
        if (window.toast) {
          window.toast(`Exported ${exportData.length} items`, 2000, 'success');
        }
      } catch (error) {
        console.error('Export failed:', error);
        if (window.toast) {
          window.toast('Export failed', 2000, 'error');
        }
      }
    });
  }
}

// Update UI based on custom order state
export function updateCustomOrderUI() {
  const clearButton = $("#clear-custom-order");
  const sortDirButton = $("#sort-dir");
  
  if (state.sortBy === 'custom') {
    // Show clear button, hide sort direction button
    if (clearButton) clearButton.style.display = 'inline-block';
    if (sortDirButton) sortDirButton.style.display = 'none';
  } else {
    // Hide clear button, show sort direction button
    if (clearButton) clearButton.style.display = 'none';
    if (sortDirButton) sortDirButton.style.display = 'inline-block';
  }
}

/* ===== Customization Helper Functions ===== */

function applyLayoutDensity() {
  const density = state.layoutDensity;
  document.documentElement.setAttribute("data-density", density);
  
  // Apply density-specific styles
  const style = document.getElementById("density-styles") || document.createElement("style");
  style.id = "density-styles";
  
  let css = "";
  if (density === "compact") {
    css = `
      .watch-item-main { padding: 8px 12px; gap: 8px; }
      .watch-item-title { font-size: 14px; margin-bottom: 2px; }
      .watch-item-meta { font-size: 11px; margin-bottom: 4px; }
      .btn-sm { padding: 2px 6px; font-size: 11px; min-height: 24px; }
      .btn-icon { width: 28px; height: 28px; font-size: 12px; }
      .progress-controls { padding: 2px; gap: 2px; }
    `;
  } else if (density === "spacious") {
    css = `
      .watch-item-main { padding: 24px; gap: 20px; }
      .watch-item-title { font-size: 18px; margin-bottom: 8px; }
      .watch-item-meta { font-size: 15px; margin-bottom: 10px; }
      .btn-sm { padding: 8px 12px; font-size: 14px; min-height: 36px; }
      .btn-icon { width: 40px; height: 40px; font-size: 16px; }
      .progress-controls { padding: 8px; gap: 8px; }
    `;
  }
  
  style.textContent = css;
  if (!document.getElementById("density-styles")) {
    document.head.appendChild(style);
  }
}

function applyFontSize() {
  const fontSize = state.fontSize;
  document.documentElement.setAttribute("data-font-size", fontSize);
  
  const style = document.getElementById("font-styles") || document.createElement("style");
  style.id = "font-styles";
  
  let css = "";
  if (fontSize === "small") {
    css = `
      body { font-size: 13px; }
      .watch-item-title { font-size: 14px; }
      .watch-item-meta { font-size: 11px; }
      .btn { font-size: 12px; }
    `;
  } else if (fontSize === "large") {
    css = `
      body { font-size: 16px; }
      .watch-item-title { font-size: 18px; }
      .watch-item-meta { font-size: 15px; }
      .btn { font-size: 15px; }
    `;
  }
  
  style.textContent = css;
  if (!document.getElementById("font-styles")) {
    document.head.appendChild(style);
  }
}

function applyCustomAccentColor() {
  const color = state.customAccentColor;
  if (color) {
    document.documentElement.style.setProperty("--accent", color);
    document.documentElement.style.setProperty("--accent-strong", color);
    
    // Calculate RGB values for rgba usage
    const rgb = hexToRgb(color);
    if (rgb) {
      document.documentElement.style.setProperty("--accent-rgb", `${rgb.r}, ${rgb.g}, ${rgb.b}`);
    }
  } else {
    // Reset to default
    document.documentElement.style.removeProperty("--accent");
    document.documentElement.style.removeProperty("--accent-strong");
    document.documentElement.style.removeProperty("--accent-rgb");
  }
}

function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

function isInQuietHours() {
  if (!state.quietHoursEnabled) return false;
  
  const now = new Date();
  const currentTime = now.getHours() * 60 + now.getMinutes();
  
  const [startHour, startMin] = state.quietHoursStart.split(':').map(Number);
  const [endHour, endMin] = state.quietHoursEnd.split(':').map(Number);
  
  const startTime = startHour * 60 + startMin;
  const endTime = endHour * 60 + endMin;
  
  // Handle overnight quiet hours (e.g., 22:00 to 08:00)
  if (startTime > endTime) {
    return currentTime >= startTime || currentTime <= endTime;
  } else {
    return currentTime >= startTime && currentTime <= endTime;
  }
}

function shouldBatchNotification() {
  return state.notificationBatching !== "off";
}

function addToBatch(notification) {
  if (!shouldBatchNotification()) return false;
  
  state.batchNotifications.push({
    ...notification,
    timestamp: Date.now()
  });
  
  // Schedule batch processing
  if (state.batchNotifications.length === 1) {
    const interval = state.notificationBatching === "hourly" ? 60 * 60 * 1000 : 24 * 60 * 60 * 1000;
    setTimeout(processBatchNotifications, interval);
  }
  
  return true;
}

function processBatchNotifications() {
  if (state.batchNotifications.length === 0) return;
  
  const notifications = [...state.batchNotifications];
  state.batchNotifications = [];
  
  // Create digest message
  const seriesCount = new Set(notifications.map(n => n.series_id)).size;
  const title = `Manga Update Digest (${seriesCount} series)`;
  
  const messages = notifications.map(n => 
    `• ${n.title}: ${n.message}`
  ).join('\n');
  
  const digestMessage = `${seriesCount} manga series have new chapters:\n\n${messages}`;
  
  // Send batched notification
  // This would integrate with the existing notification system
  console.log("Sending batched notification:", title, digestMessage);
}
