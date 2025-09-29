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
    $("#theme")?.addEventListener("click", toggle);
    $("#theme-alt")?.addEventListener("click", toggle);
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
  $("#sort-by")?.addEventListener("change", e=>{ state.sortBy = e.target.value; localStorage.setItem("mn-sort-by", state.sortBy); loadWatchlist(); });
  $("#sort-dir")?.addEventListener("click", ()=>{ state.sortDir = state.sortDir==="asc" ? "desc" : "asc"; $("#sort-dir").textContent = state.sortDir==="asc" ? "⬆︎" : "⬇︎"; localStorage.setItem("mn-sort-dir", state.sortDir); loadWatchlist(); });
  $("#unread-only") && ($("#unread-only").checked = state.unreadOnly);
  $("#unread-only")?.addEventListener("change", e=>{ state.unreadOnly = !!e.target.checked; localStorage.setItem("mn-unread-only", String(state.unreadOnly)); loadWatchlist(); });
  $("#show-covers") && ($("#show-covers").checked = state.showCovers);
  $("#show-covers")?.addEventListener("change", e=>{ state.showCovers = !!e.target.checked; localStorage.setItem("mn-show-covers", String(state.showCovers)); loadWatchlist(); });

  // Hide dropped toggle
  $("#hide-dropped") && ($("#hide-dropped").checked = state.hideDropped);
  $("#hide-dropped")?.addEventListener("change", e=>{ state.hideDropped = !!e.target.checked; localStorage.setItem("mn-hide-dropped", String(state.hideDropped)); loadWatchlist(); });

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
    try{ await api.refreshNow(); toast("Server refresh requested"); }catch(e){ toast(`Failed: ${e}`,3000); }
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
    toast(`Marked latest · OK ${ok}${fail?` · Failed ${fail}`:""}`); loadWatchlist();
  });

  /* Notifications controls */
  $("#notif-reload")?.addEventListener("click", loadNotifications);
  $("#notif-clear")?.addEventListener("click", async ()=>{ try{ await api.clearNotifications(); toast("Cleared"); }catch(e){ toast(`Failed: ${e}`,3000);} loadNotifications(); });
  $("#notify-test")?.addEventListener("click", async ()=>{ try{ await api.notifyTest(); toast("Test sent"); }catch(e){ toast(`Failed: ${e}`,3000);} loadNotifications(); });

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
      toast("Discord settings saved");
      setDiscordStatus(enabled && webhook_url ? "Enabled" : "", enabled && webhook_url ? "ok" : "");
    } catch(e) {
      toast("Failed to save Discord settings", 3000);
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
      toast("Discord test sent");
      setDiscordStatus("Test sent!", "ok");
    } catch(e) {
      toast("Failed to send Discord test", 3000);
      setDiscordStatus("Test failed", "error");
    }
  });
  loadDiscordSettings();

  // initial UI reflect
  $("#sort-dir").textContent = state.sortDir==="asc" ? "⬆︎" : "⬇︎";
  $("#sort-by") && ($("#sort-by").value = state.sortBy);
  $("#layout-alt") && ($("#layout-alt").value = state.layout);

  // URL → controls
  restoreFromUrl();
}
