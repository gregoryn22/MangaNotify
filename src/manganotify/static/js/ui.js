import { state, MIN_QUERY_LEN, TYPE_DEBOUNCE_MS, searchCache, dtFormatter } from "./state.js";
import api from "./api.js";
import { auth } from "./auth.js";

/* ===== Emoji/Text Helper ===== */
export function getIcon(emoji, text) {
  return state.useEmojis ? emoji : text;
}

/* ===== DOM utils & formatting ===== */
export const $  = (s)=>document.querySelector(s);
export const $$ = (s)=>Array.from(document.querySelectorAll(s));
export function debounce(fn, ms=350){ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), ms); }; }
export function buildQuery(params){
  return Object.entries(params)
    .filter(([,v])=>v!=="" && v!==undefined && v!==null)
    .map(([k,v])=>`${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join("&");
}

export function getCoverUrl(c){ if(!c) return ""; if(typeof c==="string") return c; if(typeof c==="object") return c.small||c.default||c.raw||""; return ""; }
export function toast(msg, ms=2200, type="info"){ 
  const t=$("#toast"); 
  if(!t) return; 
  
  // Clear existing classes
  t.className = "toast";
  
  // Set message and type
  t.textContent=msg; 
  t.classList.add("show", type); 
  
  // Auto-hide
  setTimeout(()=>{
    t.classList.remove("show", type);
    // Reset class after animation
    setTimeout(() => t.className = "toast", 300);
  }, ms); 
}
export function setStatus(text){ const el=document.getElementById("status"); if(el) el.textContent=text||"—"; }
export function parseProgress(v){ const n=parseFloat(String(v??"").replace(",",".")); return Number.isFinite(n)?Math.max(0,n):0; }
export function unreadCount(total,lastRead){ const t=Number(total)||0; const r=parseProgress(lastRead); return Math.max(0,t-Math.floor(r)); }
export function formatLocal(iso){ try{ return dtFormatter.format(new Date(iso)); } catch { return iso||""; } }
export function timeAgo(iso){
  try{
    const then=new Date(iso).getTime(); if(!Number.isFinite(then)) return "";
    const s=Math.max(0,(Date.now()-then)/1000);
    const units=[["yr",31536000],["mo",2592000],["d",86400],["h",3600],["m",60],["s",1]];
    for(const [l,sec] of units){ const v=Math.floor(s/sec); if(v>=1) return `${v}${l} ago`; }
    return "just now";
  }catch{ return ""; }
}

/* ===== URL sync ===== */
export function syncUrl(){
  const p=new URLSearchParams();
  if(state.q) p.set("q", state.q);
  for(const [k,v] of Object.entries(state.filters)){
    if(v && !(k==="has_anime" && v===false)) p.set(k, v===true ? "1" : v);
  }
  history.replaceState(null,"", p.toString()?`?${p}`:location.pathname);
}
export function restoreFromUrl(){
  const p=new URLSearchParams(location.search);
  if(p.get("q")) $("#q").value=p.get("q");
  const remap={status:"f-status", type:"f-type", content_rating:"f-cr", has_anime:"f-has-anime"};
  Object.entries(remap).forEach(([key,id])=>{
    const val=p.get(key);
    if(val!==null){
      if(id==="f-has-anime"){ $("#"+id).checked = (val==="1"||val==="true"); }
      else { $("#"+id).value = val; }
    }
  });
}

/* ===== Modal ===== */
const modal = $("#modal");
$("#modal-close")?.addEventListener("click", ()=> modal?.close?.());

/* ===== Search ===== */
const debouncedSearch = debounce(() => {
  const val = $("#q")?.value.trim() || "";
  if (val.length >= MIN_QUERY_LEN) {
    if (state.layout === "tabs") selectTab("search");
    state.q = val; state.page = 1; syncUrl(); search();
    // Save to search history
    saveSearchHistory(val);
  } else if (val.length === 0) {
    $("#results-panel").hidden = true; $("#result-info").textContent = "";
  }
}, TYPE_DEBOUNCE_MS);

// Search history management
function getSearchHistory() {
  try {
    return JSON.parse(localStorage.getItem("mn-search-history") || "[]");
  } catch {
    return [];
  }
}

function saveSearchHistory(query) {
  if (!query || query.length < MIN_QUERY_LEN) return;
  const history = getSearchHistory();
  // Remove if already exists
  const filtered = history.filter(h => h !== query);
  // Add to front
  filtered.unshift(query);
  // Keep only last 10
  const limited = filtered.slice(0, 10);
  localStorage.setItem("mn-search-history", JSON.stringify(limited));
}

function showSearchSuggestions() {
  const input = $("#q");
  const val = input?.value.trim() || "";
  
  // Remove existing suggestions
  const existing = document.getElementById("search-suggestions");
  if (existing) existing.remove();
  
  if (val.length < MIN_QUERY_LEN) return;
  
  const history = getSearchHistory();
  const suggestions = history.filter(h => h.toLowerCase().includes(val.toLowerCase()) && h !== val);
  
  if (suggestions.length === 0) return;
  
  const container = document.createElement("div");
  container.id = "search-suggestions";
  container.className = "search-suggestions";
  container.innerHTML = suggestions.slice(0, 5).map(suggestion => 
    `<div class="suggestion-item" data-suggestion="${suggestion}">${suggestion}</div>`
  ).join("");
  
  // Position below search input
  const searchContainer = input.closest(".pill");
  if (searchContainer) {
    searchContainer.style.position = "relative";
    searchContainer.appendChild(container);
    
    // Add click handlers
    container.querySelectorAll(".suggestion-item").forEach(item => {
      item.addEventListener("click", () => {
        input.value = item.dataset.suggestion;
        input.dispatchEvent(new Event("input"));
        container.remove();
      });
    });
    
    // Hide on outside click
    setTimeout(() => {
      document.addEventListener("click", function hideSuggestions(e) {
        if (!searchContainer.contains(e.target)) {
          container.remove();
          document.removeEventListener("click", hideSuggestions);
        }
      });
    }, 0);
  }
}

function searchParams(){
  const params = { q: state.q, page: state.page, limit: state.limit };
  if(state.filters.status) params.status = state.filters.status;
  if(state.filters.type) params.type = state.filters.type;
  if(state.filters.content_rating) params.content_rating = state.filters.content_rating;
  if(state.filters.has_anime) params.has_anime = "true";
  return params;
}

export async function search(){
  if (!auth.requireAuth()) return;
  
  if(!state.q){ $("#results-panel").hidden=true; return; }
  if(state.aborter){ state.aborter.abort(); }
  state.aborter = new AbortController();

  // Reset pagination for new search
  state.page = 1;
  state.allResults = []; // Store all loaded results
  state.isLoadingMore = false;
  state.hasMoreResults = true;

  setStatus("Searching…");
  $("#results-panel").hidden=false;
  $("#results").innerHTML = Array.from({length:8}).map(()=>`
    <div class="card loading" role="listitem" aria-busy="true">
      <div class="cover shimmer"></div>
      <div class="meta">
        <div class="title shimmer" style="height:16px;border-radius:6px"></div>
        <div class="subline shimmer" style="height:12px;border-radius:6px;width:70%"></div>
        <div class="row" style="margin-top:8px">
          <div class="shimmer" style="height:24px;width:60px;border-radius:6px"></div>
          <div class="shimmer" style="height:24px;width:50px;border-radius:6px"></div>
        </div>
      </div>
    </div>`).join("");

  try{
    const qs = buildQuery(searchParams());
    if(searchCache.has(qs)){ renderResults(searchCache.get(qs)); setStatus("Cached"); return; }
    const js = await api.search(searchParams());
    searchCache.set(qs, js);
    renderResults(js);
    setStatus("Done");
    
    // Initialize infinite scroll
    initializeInfiniteScroll();
  }catch(e){
    if(e.name==="AbortError") return;
    const errorMsg = e.toString().replace(/[<>]/g, "");
    $("#results").innerHTML = `<div style="padding:18px" class="subline">Search failed. ${errorMsg}</div>`;
    setStatus("Search failed");
  }
}

async function loadMoreResults() {
  if (state.isLoadingMore || !state.hasMoreResults) return;
  
  state.isLoadingMore = true;
  state.page += 1;
  
  // Add loading indicator
  const loadingIndicator = document.createElement('div');
  loadingIndicator.className = 'infinite-scroll-loading';
  loadingIndicator.innerHTML = `
    <div class="card loading" role="listitem" aria-busy="true">
      <div class="cover shimmer"></div>
      <div class="meta">
        <div class="title shimmer" style="height:16px;border-radius:6px"></div>
        <div class="subline shimmer" style="height:12px;border-radius:6px;width:70%"></div>
        <div class="row" style="margin-top:8px">
          <div class="shimmer" style="height:24px;width:60px;border-radius:6px"></div>
          <div class="shimmer" style="height:24px;width:50px;border-radius:6px"></div>
        </div>
      </div>
    </div>
  `;
  $("#results").appendChild(loadingIndicator);
  
  try {
    const js = await api.search(searchParams());
    
    if (js.data && js.data.length > 0) {
      // Append new results
      state.allResults = state.allResults.concat(js.data);
      renderInfiniteResults(js.data);
      
      // Check if there are more results
      const pagination = js.pagination || js.meta || {};
      state.hasMoreResults = pagination.next || false;
    } else {
      state.hasMoreResults = false;
    }
  } catch (e) {
    console.error("Failed to load more results:", e);
    state.hasMoreResults = false;
  } finally {
    state.isLoadingMore = false;
    loadingIndicator.remove();
  }
}

function initializeInfiniteScroll() {
  // Remove existing scroll listener
  const existingListener = document.getElementById('infinite-scroll-observer');
  if (existingListener) {
    existingListener.remove();
  }
  
  // Create intersection observer for infinite scroll
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && state.hasMoreResults && !state.isLoadingMore) {
        loadMoreResults();
      }
    });
  }, {
    rootMargin: '100px' // Start loading 100px before reaching the bottom
  });
  
  // Create a sentinel element at the bottom
  const sentinel = document.createElement('div');
  sentinel.id = 'infinite-scroll-observer';
  sentinel.style.height = '1px';
  sentinel.style.width = '100%';
  $("#results").appendChild(sentinel);
  
  observer.observe(sentinel);
}

function renderInfiniteResults(newItems) {
  const box = $("#results");
  
  newItems.forEach(item => {
    const el = document.createElement("div");
    el.className = "card";
    el.setAttribute("role", "listitem");
    
    const title = item.title || item.romanized_title || item.native_title || "(no title)";
    const cover = getCoverUrl(item.cover);
    const authors = (item.authors || []).join(", ");
    const total = item.total_chapters ?? "—";
    const cr = (item.content_rating || "").toLowerCase();
    const status = item.status || "";

    el.innerHTML = `
      <div class="cover ${cover ? "" : "shimmer"}">${cover ? `<img src="${cover}" alt="${title} cover" loading="lazy" decoding="async">` : ""}</div>
      <div class="meta">
        <h3 class="title" title="${title}">${title}</h3>
        <div class="subline">ID: <code>${item.id}</code>${authors ? ` · ${authors}` : ""} · Chapters: ${total}${status?` · ${status}`:""}${cr?` · ${cr}`:""}</div>
        <div class="row">
          <select class="btn" data-add-status="${item.id}" title="Initial status" style="padding:6px 8px">
            ${["reading","to-read","on-hold","finished","dropped"].map(s=>`<option value="${s}" ${s==="reading"?"selected":""}>${s}</option>`).join("")}
          </select>
          <button class="btn" data-add="${item.id}">Watch</button>
          <button class="btn" data-open="${item.id}">Open</button>
          <button class="btn" data-details="${item.id}">Details</button>
          <button class="btn" data-copy="${item.id}" title="Copy ID">Copy ID</button>
        </div>
      </div>
      <div class="manga-preview" data-manga-id="${item.id}">
        <div class="preview-content">
          <div class="preview-cover">${cover ? `<img src="${cover}" alt="${title} cover">` : ""}</div>
          <div class="preview-info">
            <div class="preview-title">${title}</div>
            <div class="preview-meta">${authors ? `By ${authors}` : ""}</div>
            <div class="preview-stats">
              <span class="preview-stat">📖 ${total} chapters</span>
              ${status ? `<span class="preview-stat">📊 ${status}</span>` : ""}
              ${cr ? `<span class="preview-stat">🔞 ${cr}</span>` : ""}
            </div>
            ${item.description ? `<div class="preview-description">${item.description.substring(0, 150)}${item.description.length > 150 ? '...' : ''}</div>` : ""}
          </div>
        </div>
      </div>`;
    
    box.appendChild(el);

    // Add hover preview functionality
    el.addEventListener('mouseenter', () => {
      const preview = el.querySelector('.manga-preview');
      if (preview) {
        preview.style.display = 'block';
        setTimeout(() => preview.classList.add('visible'), 10);
      }
    });
    
    el.addEventListener('mouseleave', () => {
      const preview = el.querySelector('.manga-preview');
      if (preview) {
        preview.classList.remove('visible');
        setTimeout(() => preview.style.display = 'none', 200);
      }
    });

    // Wire up the buttons
    el.querySelector(`[data-add="${item.id}"]`).onclick = async ()=>{
      try{
        const statusSel = el.querySelector(`[data-add-status="${item.id}"]`);
        const status = statusSel ? statusSel.value : undefined;
        await api.addWatch({ id: item.id, title, total_chapters: total, last_read: 0, status });
        toast("Added to watchlist", 2200, "success"); await loadWatchlist();
      }catch{
        toast("Failed to add", 2500, "error");
      }
    };
    
    el.querySelector(`[data-open="${item.id}"]`).onclick = ()=> window.open(`https://mangadex.org/title/${item.id}`, "_blank");
    
    el.querySelector(`[data-details="${item.id}"]`).onclick = async ()=>{
      try{
        const js = await api.series(item.id, true);
        showDetails(js);
      }catch{
        toast("Failed to load details", 2500, "error");
      }
    };
    
    el.querySelector(`[data-copy="${item.id}"]`).onclick = async ()=>{
      try{ await navigator.clipboard.writeText(String(item.id)); toast("ID copied", 1500, "success"); }catch{}
    };
  });
}

function renderResults(js){
  const items = js.data || js.results || [];
  const p = js.pagination || null;
  state.pagination = p;
  
  // Store initial results for infinite scroll
  state.allResults = items;

  const info = p ? `${p.count || items.length} result${(p.count || items.length)===1?"":"s"}`
                 : `${items.length} result${items.length===1?"":"s"}`;
  $("#result-info").textContent = info;

  const box=$("#results");
  box.innerHTML="";
  if(!items.length){
    box.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🔍</div>
        <div class="empty-state-title">No results found</div>
        <div class="empty-state-description">Try adjusting your search terms or filters to find more manga.</div>
      </div>`;
    $("#pager").hidden=true; return;
  }

  // Hide pagination controls for infinite scroll
  $("#pager").hidden=true;

  for(const it of items){
    const el=document.createElement("div");
    el.className="card"; el.setAttribute("role","listitem");
    const title = it.title || it.romanized_title || it.native_title || "(no title)";
    const cover = getCoverUrl(it.cover);
    const authors=(it.authors||[]).join(", ");
    const total = it.total_chapters ?? "—";
    const cr = (it.content_rating || "").toLowerCase();
    const status = it.status || "";

    el.innerHTML = `
      <div class="cover ${cover ? "" : "shimmer"}">${cover ? `<img src="${cover}" alt="${title} cover" loading="lazy" decoding="async">` : ""}</div>
      <div class="meta">
        <h3 class="title" title="${title}">${title}</h3>
        <div class="subline">ID: <code>${it.id}</code>${authors ? ` · ${authors}` : ""} · Chapters: ${total}${status?` · ${status}`:""}${cr?` · ${cr}`:""}</div>
        <div class="row">
          <select class="btn" data-add-status="${it.id}" title="Initial status" style="padding:6px 8px">
            ${["reading","to-read","on-hold","finished","dropped"].map(s=>`<option value="${s}" ${s==="reading"?"selected":""}>${s}</option>`).join("")}
          </select>
          <button class="btn" data-add="${it.id}">Watch</button>
          <button class="btn" data-open="${it.id}">Open</button>
          <button class="btn" data-details="${it.id}">Details</button>
          <button class="btn" data-copy="${it.id}" title="Copy ID">Copy ID</button>
        </div>
      </div>
      <div class="manga-preview" data-manga-id="${it.id}">
        <div class="preview-content">
          <div class="preview-cover">${cover ? `<img src="${cover}" alt="${title} cover">` : ""}</div>
          <div class="preview-info">
            <div class="preview-title">${title}</div>
            <div class="preview-meta">${authors ? `By ${authors}` : ""}</div>
            <div class="preview-stats">
              <span class="preview-stat">📖 ${total} chapters</span>
              ${status ? `<span class="preview-stat">📊 ${status}</span>` : ""}
              ${cr ? `<span class="preview-stat">🔞 ${cr}</span>` : ""}
            </div>
            ${it.description ? `<div class="preview-description">${it.description.substring(0, 150)}${it.description.length > 150 ? '...' : ''}</div>` : ""}
          </div>
        </div>
      </div>`;
    box.appendChild(el);

    // Add hover preview functionality
    el.addEventListener('mouseenter', () => {
      const preview = el.querySelector('.manga-preview');
      if (preview) {
        preview.style.display = 'block';
        setTimeout(() => preview.classList.add('visible'), 10);
      }
    });
    
    el.addEventListener('mouseleave', () => {
      const preview = el.querySelector('.manga-preview');
      if (preview) {
        preview.classList.remove('visible');
        setTimeout(() => preview.style.display = 'none', 200);
      }
    });

    el.querySelector(`[data-add="${it.id}"]`).onclick = async ()=>{
      try{
        const statusSel = el.querySelector(`[data-add-status="${it.id}"]`);
        const status = statusSel ? statusSel.value : undefined;
        await api.addWatch({ id: it.id, title, total_chapters: total, last_read: 0, status });
        toast("Added to watchlist", 2200, "success"); await loadWatchlist();
      }catch{ toast("Failed to add", 2600, "error"); }
    };
    el.querySelector(`[data-open="${it.id}"]`).onclick = ()=> window.open(`https://mangabaka.dev/${it.id}`, "_blank");
    el.querySelector(`[data-copy="${it.id}"]`).onclick = async ()=>{ try{ await navigator.clipboard.writeText(String(it.id)); toast("ID copied", 2200, "success"); }catch{ toast("Copy failed", 2200, "error"); } };
    el.querySelector(`[data-details="${it.id}"]`).onclick = ()=> openDetails(it.id, title);
  }

  if(p){
    $("#pager").hidden=false;
    $("#page-indicator").textContent = `Page ${p.page}`;
    $("#prev").disabled = !p.previous;
    $("#next").disabled = !p.next;
  }else{
    $("#pager").hidden=true;
  }
}

/* ===== Details modal ===== */
async function openDetails(id, title){
  $("#modal-title").textContent = title || `Series ${id}`;
  const body = $("#modal-body");
  body.innerHTML = `<div class="subline">Loading…</div>`;
  modal.showModal?.();
  try{
    const js = await api.series(id, true);
    const s  = js.minimal || {};
    const merged = js.merged_with ? `<span class="badge">merged → ${js.merged_with}</span>` : "";
    const linksHtml = []; // populate when you add /links

    body.innerHTML = `
      <div class="kvs">
        <div><strong>Title:</strong> ${s.title || "(unknown)"} ${merged}</div>
        <div><strong>ID:</strong> <code>${s.id ?? id}</code></div>
        <div><strong>Status:</strong> ${s.status || "—"} · <strong>Type:</strong> ${s.type || "—"} · <strong>Rating:</strong> ${s.content_rating || "—"}</div>
        <div><strong>Chapters:</strong> ${s.total_chapters ?? "—"}</div>
      </div>
      ${linksHtml.length ? `<div class="tags">${linksHtml.join("")}</div>` : `<div class="muted">No external links.</div>`}
    `;
  }catch{
    body.innerHTML = `<div class="subline">Failed to load details.</div>`;
  }
}

/* ===== Notification Settings Modal ===== */
async function openNotificationSettings(id, title){
  $("#modal-title").textContent = `Notification Settings - ${title || `Series ${id}`}`;
  const body = $("#modal-body");
  body.innerHTML = `<div class="subline">Loading…</div>`;
  modal.showModal?.();
  
  try{
    const js = await api.getNotificationPrefs(id);
    const prefs = js.notifications || {
      enabled: true,
      pushover: true,
      discord: true,
      only_when_reading: true
    };
    
    body.innerHTML = `
      <div class="notification-settings">
        <div class="setting-group">
          <label class="checkbox-label">
            <input type="checkbox" id="notif-enabled" ${prefs.enabled ? 'checked' : ''}>
            <span>Enable notifications for this series</span>
          </label>
        </div>
        
        <div class="setting-group">
          <label class="checkbox-label">
            <input type="checkbox" id="notif-pushover" ${prefs.pushover ? 'checked' : ''} ${!prefs.enabled ? 'disabled' : ''}>
            <span>Send Pushover notifications</span>
          </label>
        </div>
        
        <div class="setting-group">
          <label class="checkbox-label">
            <input type="checkbox" id="notif-discord" ${prefs.discord ? 'checked' : ''} ${!prefs.enabled ? 'disabled' : ''}>
            <span>Send Discord notifications</span>
          </label>
        </div>
        
        <div class="setting-group">
          <label class="checkbox-label">
            <input type="checkbox" id="notif-only-reading" ${prefs.only_when_reading ? 'checked' : ''} ${!prefs.enabled ? 'disabled' : ''}>
            <span>Only notify when status is "reading"</span>
          </label>
        </div>
        
        <div class="setting-actions">
          <button class="btn" id="save-notifications">Save Settings</button>
          <button class="btn secondary" onclick="modal.close()">Cancel</button>
        </div>
      </div>
    `;
    
    // Wire up the save button
    document.getElementById("save-notifications").onclick = async () => {
      const enabled = document.getElementById("notif-enabled").checked;
      const pushover = document.getElementById("notif-pushover").checked;
      const discord = document.getElementById("notif-discord").checked;
      const onlyReading = document.getElementById("notif-only-reading").checked;
      
      try {
        await api.updateNotificationPrefs(id, {
          enabled,
          pushover,
          discord,
          only_when_reading: onlyReading
        });
        toast("Notification settings saved", 2200, "success");
        modal.close();
      } catch {
        toast("Failed to save settings", 2600, "error");
      }
    };
    
    // Wire up the enabled checkbox to enable/disable others
    document.getElementById("notif-enabled").onchange = (e) => {
      const enabled = e.target.checked;
      document.getElementById("notif-pushover").disabled = !enabled;
      document.getElementById("notif-discord").disabled = !enabled;
      document.getElementById("notif-only-reading").disabled = !enabled;
    };
    
  }catch{
    body.innerHTML = `<div class="subline">Failed to load notification settings.</div>`;
  }
}

/* ===== Bulk Operations ===== */
function addBulkOperationsToolbar(container) {
  // Remove any existing toolbar first to prevent duplicates
  const existingToolbar = document.querySelector('.bulk-operations-toolbar');
  if (existingToolbar) {
    existingToolbar.remove();
  }
  
  const toolbar = document.createElement('div');
  toolbar.className = 'bulk-operations-toolbar';
  toolbar.innerHTML = `
    <div class="bulk-controls">
      <label class="bulk-checkbox">
        <input type="checkbox" id="select-all" />
        <span>Select All</span>
      </label>
      <div class="bulk-actions" style="display: none;">
        <select id="bulk-status-change" class="btn">
          <option value="">Change Status</option>
          <option value="reading">Reading</option>
          <option value="to-read">To Read</option>
          <option value="on-hold">On Hold</option>
          <option value="finished">Finished</option>
          <option value="dropped">Dropped</option>
        </select>
        <button id="bulk-delete" class="btn btn-danger">Delete Selected</button>
        <button id="bulk-export" class="btn">Export Selected</button>
        <span id="selected-count" class="selected-count">0 selected</span>
      </div>
    </div>
  `;
  container.parentNode.insertBefore(toolbar, container);
}

function initializeBulkOperations(container, list) {
  const selectAllCheckbox = document.getElementById('select-all');
  const bulkActions = document.querySelector('.bulk-actions');
  const selectedCount = document.getElementById('selected-count');
  const bulkStatusChange = document.getElementById('bulk-status-change');
  const bulkDelete = document.getElementById('bulk-delete');
  const bulkExport = document.getElementById('bulk-export');
  
  // Return early if bulk operations toolbar doesn't exist
  if (!selectAllCheckbox || !bulkActions || !selectedCount) {
    return;
  }
  
  let selectedItems = new Set();
  
  // Remove existing checkboxes first to prevent duplicates
  container.querySelectorAll('.item-checkbox-label').forEach(label => label.remove());
  
  // Add checkboxes to each item
  container.querySelectorAll('.watch-item').forEach((item, index) => {
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'item-checkbox';
    checkbox.dataset.itemId = list[index]?.id;
    
    const checkboxLabel = document.createElement('label');
    checkboxLabel.className = 'item-checkbox-label';
    checkboxLabel.appendChild(checkbox);
    
    const main = item.querySelector('.watch-item-main');
    if (main) {
      main.insertBefore(checkboxLabel, main.firstChild);
    }
    
    checkbox.addEventListener('change', updateBulkState);
  });
  
  function updateBulkState() {
    const checkboxes = container.querySelectorAll('.item-checkbox');
    selectedItems.clear();
    
    checkboxes.forEach(checkbox => {
      if (checkbox.checked) {
        selectedItems.add(checkbox.dataset.itemId);
      }
    });
    
    const selectedCountValue = selectedItems.size;
    selectedCount.textContent = `${selectedCountValue} selected`;
    
    if (selectedCountValue > 0) {
      bulkActions.style.display = 'flex';
      selectAllCheckbox.indeterminate = selectedCountValue < checkboxes.length;
      selectAllCheckbox.checked = selectedCountValue === checkboxes.length;
    } else {
      bulkActions.style.display = 'none';
      selectAllCheckbox.indeterminate = false;
      selectAllCheckbox.checked = false;
    }
  }
  
  selectAllCheckbox.addEventListener('change', () => {
    const checkboxes = container.querySelectorAll('.item-checkbox');
    checkboxes.forEach(checkbox => {
      checkbox.checked = selectAllCheckbox.checked;
    });
    updateBulkState();
  });
  
  bulkStatusChange.addEventListener('change', async () => {
    if (!bulkStatusChange.value || selectedItems.size === 0) return;
    
    const status = bulkStatusChange.value;
    const promises = Array.from(selectedItems).map(id => 
      api.updateWatch({ id, status })
    );
    
    try {
      await Promise.all(promises);
      toast(`Updated ${selectedItems.size} items to ${status}`, 2000, 'success');
      await loadWatchlist();
    } catch (error) {
      toast('Failed to update items', 2000, 'error');
    }
    
    bulkStatusChange.value = '';
  });
  
  bulkDelete.addEventListener('click', async () => {
    if (selectedItems.size === 0) return;
    
    if (!confirm(`Are you sure you want to delete ${selectedItems.size} items from your watchlist?`)) {
      return;
    }
    
    const promises = Array.from(selectedItems).map(id => 
      api.removeWatch({ id })
    );
    
    try {
      await Promise.all(promises);
      toast(`Deleted ${selectedItems.size} items`, 2000, 'success');
      await loadWatchlist();
    } catch (error) {
      toast('Failed to delete items', 2000, 'error');
    }
  });
  
  bulkExport.addEventListener('click', () => {
    if (selectedItems.size === 0) return;
    
    const selectedList = list.filter(item => selectedItems.has(item.id.toString()));
    const exportData = selectedList.map(item => ({
      title: item.title,
      status: item.status,
      last_read: item.last_read,
      total_chapters: item.total_chapters,
      id: item.id
    }));
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `manganotify-watchlist-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
    
    toast(`Exported ${selectedItems.size} items`, 2000, 'success');
  });
}

/* ===== Watchlist ===== */
export async function loadWatchlist(){
  if (!auth.requireAuth()) return;
  
  const container = document.getElementById("watchlist");
  if (!container) return;
  
  // Show skeleton loader
  container.innerHTML = Array.from({length: 6}).map(() => `
    <div class="card loading" role="listitem" aria-busy="true">
      <div class="cover shimmer"></div>
      <div class="meta">
        <div class="title shimmer" style="height:16px;border-radius:6px"></div>
        <div class="subline shimmer" style="height:12px;border-radius:6px;width:70%"></div>
        <div class="row" style="margin-top:8px">
          <div class="shimmer" style="height:24px;width:60px;border-radius:6px"></div>
          <div class="shimmer" style="height:24px;width:50px;border-radius:6px"></div>
        </div>
      </div>
    </div>
  `).join("");
  
  // Add bulk operations toolbar
  addBulkOperationsToolbar(container);
  
  const statusFilter = document.getElementById("wl-status-filter")?.value || "";
  const js = await api.watchlist(statusFilter ? { status: statusFilter } : undefined);
  let list = js.data || [];

  if(state.unreadOnly){
    list = list.filter(it=>{
      const total = Number.isFinite(+it.total_chapters) ? +it.total_chapters : null;
      const lastRead = parseProgress(it.last_read ?? 0);
      const unread = total!==null ? unreadCount(total, lastRead) : 0;
      return unread > 0;
    });
  }

  // Optionally hide dropped
  if(state.hideDropped){ list = list.filter(it => (it.status || "reading") !== "dropped"); }

  list = sortWatchlist(list);

  $("#watch-count").textContent = `${list.length} item${list.length===1?"":"s"}`;
  $("#watch-unread-count").textContent = `Unread: ${list.reduce((sum,it)=>{
    const tot = Number.isFinite(+it.total_chapters) ? +it.total_chapters : null;
    const last = parseProgress(it.last_read ?? 0);
    return sum + (tot!==null ? unreadCount(tot,last) : 0);
  },0)}`;

  const box = $("#watchlist");
  box.innerHTML = "";

  if(!list.length){
    box.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📚</div>
        <div class="empty-state-title">No manga in watchlist</div>
        <div class="empty-state-description">Search for manga above and add them to your watchlist to track new chapters.</div>
      </div>`;
    return;
  }

  for(const it of list){
    const total    = Number.isFinite(+it.total_chapters) ? +it.total_chapters : null;
    const lastRead = parseProgress(it.last_read ?? 0);
    const unread   = total!==null ? unreadCount(total, lastRead) : 0;
    const behind   = total!==null ? unread > 0 : false;

    const lastCheckedTxt = it.last_checked ? `· Last checked: ${timeAgo(it.last_checked)}` : "";
    const lastChapterTxt = it.last_chapter_at ? `· Last update: ${timeAgo(it.last_chapter_at)}` : "";
    const mergeTxt = it.merge_note ? ` · <span class="badge">merged</span>` : "";

    const row = document.createElement("div");
    row.className = "watch-item" + (behind ? " unread" : "");
    row.dataset.tags = it.tags ? it.tags.join(',') : '';
    row.innerHTML = `
      <div class="watch-item-main">
        <div class="watch-item-left">
          <span class="dot-spacer ${behind ? "unread" : ""}" aria-hidden="true"></span>
          ${
            state.showCovers && it.cover
              ? `<img src="${it.cover}" alt="" width="40" height="60" loading="lazy" decoding="async"
                     style="border-radius:6px; border:1px solid var(--border); object-fit:cover" />`
              : `<div class="cover-ph" aria-hidden="true"></div>`
          }
          <div class="watch-item-info">
            <div class="watch-item-title" title="${it.title || ""}">
              ${it.title || "(no title)"} ${mergeTxt}
            </div>
            <div class="watch-item-meta" title="${it.last_checked ? formatLocal(it.last_checked) : ""}">
              ${state.showIds ? `ID: <code>${it.id}</code> · ` : ""}Chapters: ${total ?? "—"}
              ${state.showLastChecked ? lastCheckedTxt : ""} ${lastChapterTxt}
              ${state.showStatus && it.status? ` · <span class="status-badge status-${(it.status||"reading").replace(/[^a-z-]/g,"")}">${it.status}</span>` : ""} ${state.showContentRating && it.content_rating? ` · ${it.content_rating}` : ""}
            </div>
            <div class="watch-item-badges">
              <span class="badge ${behind ? "warn":"ok"}" title="Unread chapters">
                ${behind ? "Unread" : "Up to date"}${total!==null ? `: ${unread}` : ""}
              </span>
              ${total!==null ? `<span class="badge">Read: ${String(lastRead).replace(/\.0$/,"")}/${total}</span>` : ""}
              ${it.tags && it.tags.length > 0 ? `<div class="watch-tags">${it.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}</div>` : ''}
            </div>
          </div>
        </div>

        <div class="watch-item-actions">
          <div class="primary-actions">
            ${total!==null ? `
              <div class="progress-controls">
                <button class="btn btn-sm" data-prev="${it.id}" title="Decrement read (−1)">−1</button>
                <input class="input-mini" type="number" min="0" ${total!==null ? `max="${total}"`:""}
                       step="1" value="${String(lastRead).replace(/\.0$/,"")}" aria-label="Last read chapter" data-lr="${it.id}" />
                <button class="btn btn-sm" data-set="${it.id}" title="Set last read">Set</button>
                <button class="btn btn-sm" data-next="${it.id}" title="Increment read (+1)">+1</button>
                <button class="btn btn-sm" data-latest="${it.id}" title="Mark latest">Latest</button>
              </div>
            ` : ""}
            <select class="btn btn-sm" data-status="${it.id}" title="Set status">
              ${["reading","to-read","on-hold","finished","dropped"].map(s=>`<option value="${s}" ${String(it.status||"reading")==="${s}"?"selected":""}>${s}</option>`).join("")}
            </select>
          </div>
          
          <div class="secondary-actions">
            <button class="btn btn-icon" data-details="${it.id}" title="Details" data-emoji="${state.useEmojis}">${getIcon("📋", "Details")}</button>
            <button class="btn btn-icon" data-open="${it.id}" title="Open series page" data-emoji="${state.useEmojis}">${getIcon("🔗", "Open")}</button>
            <button class="btn btn-icon" data-copy="${it.id}" title="Copy ID" data-emoji="${state.useEmojis}">${getIcon("📋", "Copy")}</button>
            <button class="btn btn-icon" data-notifications="${it.id}" title="Notification Settings" data-emoji="${state.useEmojis}">${getIcon("🔔", "Notify")}</button>
            <button class="btn btn-icon btn-danger" data-remove="${it.id}" title="Remove" data-emoji="${state.useEmojis}">${getIcon("🗑", "Remove")}</button>
          </div>
        </div>
      </div>
    `;

    const id = it.id;
    row.querySelector(`[data-open="${id}"]`).onclick = ()=> window.open(`https://mangabaka.dev/${id}`, "_blank");
    row.querySelector(`[data-copy="${id}"]`).onclick = async ()=>{ try{ await navigator.clipboard.writeText(String(id)); toast("ID copied", 2200, "success"); }catch{ toast("Copy failed", 2200, "error"); } };
    row.querySelector(`[data-details="${id}"]`).onclick = ()=> openDetails(id, it.title || `Series ${id}`);
    row.querySelector(`[data-remove="${id}"]`).onclick = async ()=>{ try{ await api.removeWatch(id); toast("Removed", 2200, "success"); loadWatchlist(); }catch{ toast("Failed to remove",2600, "error");} };
    row.querySelector(`[data-notifications="${id}"]`).onclick = ()=> openNotificationSettings(id, it.title || `Series ${id}`);
    row.querySelector(`[data-more="${id}"]`)?.addEventListener("click", ()=>{ row.classList.toggle("show-more"); });

    const inp = row.querySelector(`[data-lr="${id}"]`);
    row.querySelector(`[data-set="${id}"]`)?.addEventListener("click", async ()=>{
      const val = parseProgress(inp.value);
      try{ await api.setProgress(id, { last_read: val }); toast("Progress updated", 2200, "success"); loadWatchlist(); }
      catch{ toast("Failed to update", 2600, "error"); }
    });
    row.querySelector(`[data-next="${id}"]`)?.addEventListener("click", async ()=>{
      try{ await api.readNext(id); toast("+1 read", 2200, "success"); loadWatchlist(); } catch{ toast("Failed to bump",2600, "error"); }
    });
    row.querySelector(`[data-prev="${id}"]`)?.addEventListener("click", async ()=>{
      try{ await api.setProgress(id, { decrement: 1 }); toast("−1 read", 2200, "success"); loadWatchlist(); } catch{ toast("Failed to decrement",2600, "error"); }
    });

    // Status change handler (optimistic)
    const statusSel = row.querySelector(`[data-status="${id}"]`);
    statusSel?.addEventListener("change", async (e)=>{
      const newStatus = e.target.value;
      const prev = it.status || "reading";
      try{
        await api.setStatus(id, newStatus);
        toast(`Status: ${newStatus}`, 2200, "success");
      }catch{
        // rollback UI value on failure
        statusSel.value = prev;
        toast("Failed to set status", 2600, "error");
      }
    });

    $("#watchlist").appendChild(row);
  }

  // Add bulk operations functionality
  initializeBulkOperations($("#watchlist"), list);
  
  // Add drag-and-drop functionality
  initializeDragAndDrop($("#watchlist"), list);
  
  // Add watchlist search functionality
  initializeWatchlistSearch(list);
  
  // Add tag filtering functionality
  initializeTagFiltering(list);

  state.lastRefreshTs = Date.now();
}

/* ===== Delegated: Mark latest (works even after re-render) ===== */
document.getElementById("watchlist")?.addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-latest]");
  if (!btn) return;
  const id = btn.getAttribute("data-latest");
  try{
    await api.setProgress(id, { mark_latest: true });
    toast("Marked latest", 2200, "success");
    loadWatchlist();
  }catch{
    toast("Failed", 2500, "error");
  }
});

function sortWatchlist(list){
  const by = state.sortBy;
  const dir = state.sortDir === "desc" ? -1 : 1;

  // If custom order is selected, use it
  if (by === "custom") {
    return applyCustomOrder(list);
  }

  return [...list].sort((a,b)=>{
    const aTitle=(a.title||"").toLowerCase(); const bTitle=(b.title||"").toLowerCase();
    const aTotal=Number.isFinite(+a.total_chapters)?+a.total_chapters:null;
    const bTotal=Number.isFinite(+b.total_chapters)?+b.total_chapters:null;
    const aLast=parseProgress(a.last_read??0); const bLast=parseProgress(b.last_read??0);
    const aUnread=aTotal!==null?unreadCount(aTotal,aLast):-1; const bUnread=bTotal!==null?unreadCount(bTotal,bLast):-1;
    const aChecked=a.last_checked?Date.parse(a.last_checked):0; const bChecked=b.last_checked?Date.parse(b.last_checked):0;
    const aAdded=a.added_at?Date.parse(a.added_at):0; const bAdded=b.added_at?Date.parse(b.added_at):0;

    let cmp=0;
    switch(by){
      case "title":        cmp=aTitle.localeCompare(bTitle); break;
      case "unread":       cmp=(bUnread-aUnread); break;
      case "chapters":     cmp=((bTotal??-1)-(aTotal??-1)); break;
      case "last_checked": cmp=(bChecked-aChecked); break;
      case "added_at":     cmp=(bAdded-aAdded); break;
      default: cmp=0;
    }
    return dir===1?cmp:-cmp;
  });
}

/* ===== Tabs/layout helpers ===== */
export function selectTab(name){
  localStorage.setItem("mn-last-tab", name);
  const map = { watch: "#watchlist-panel", search:"#search-group", notif:"#notifications" };
  for(const [key, sel] of Object.entries(map)){
    const on = key===name;
    document.querySelector(sel).hidden = !on;
    $(`#tab-${key}`)?.setAttribute("aria-selected", on ? "true" : "false");
  }
}

export function applyLayout(v){
  state.layout = v;
  localStorage.setItem("mn-layout", v);
  document.body.setAttribute("data-layout", v);
  if(v==="tabs"){
    const last = localStorage.getItem("mn-last-tab") || "watch"; // default to Watch
    selectTab(last);
  }else{
    $("#search-group").hidden = false;
    $("#watchlist-panel").hidden = false;
    $("#notifications").hidden = false;
  }
}

/* ===== Settings Drawer wiring (and export) ===== */
const drawer = document.getElementById("settings-drawer");
export function openSettings(){
  drawer?.classList.add("open");
  drawer?.setAttribute("aria-hidden","false");
  document.getElementById("open-settings")?.setAttribute("aria-expanded","true");
  document.body.classList.add("drawer-open"); // shows scrim
}
export function closeSettings(){
  drawer?.classList.remove("open");
  drawer?.setAttribute("aria-hidden","true");
  document.getElementById("open-settings")?.setAttribute("aria-expanded","false");
  document.body.classList.remove("drawer-open"); // hides scrim
}
document.getElementById("open-settings")?.addEventListener("click", openSettings);
document.getElementById("open-settings-2")?.addEventListener("click", openSettings);
document.getElementById("close-settings")?.addEventListener("click", closeSettings);
window.addEventListener("keydown",(e)=>{ if(e.key==="Escape") closeSettings(); });

/* ===== small public inits used elsewhere ===== */
export function wireSearchBox(){
  $("#q")?.addEventListener("input", (e) => {
    debouncedSearch();
    showSearchSuggestions();
  });
  $("#go")?.addEventListener("click", ()=>{
    const v=$("#q").value.trim(); if(v.length>=MIN_QUERY_LEN){ state.q=v; state.page=1; syncUrl(); search(); }
  });
  $("#clear-q")?.addEventListener("click", ()=>{
    $("#q").value=""; state.q=""; $("#results-panel").hidden=true; $("#result-info").textContent=""; syncUrl();
    // Clear suggestions
    const existing = document.getElementById("search-suggestions");
    if (existing) existing.remove();
  });

  $("#prev")?.addEventListener("click", ()=>{ if(state.pagination?.previous){ state.page=Math.max(1,(state.pagination.page||1)-1); search(); } });
  $("#next")?.addEventListener("click", ()=>{ if(state.pagination?.next){ state.page=(state.pagination.page||1)+1; search(); } });

  // Tab buttons (only visible in tabs layout)
  document.getElementById("tab-watch")?.addEventListener("click", ()=>selectTab("watch"));
  document.getElementById("tab-search")?.addEventListener("click", ()=>selectTab("search"));
  document.getElementById("tab-notif")?.addEventListener("click", ()=>selectTab("notif"));
  
  // Initialize advanced filtering
  initializeAdvancedFilters();
}

function initializeAdvancedFilters() {
  // Filter chip functionality
  document.querySelectorAll('.filter-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const filterType = chip.dataset.filter;
      const filterValue = chip.dataset.value;
      
      // Update state
      if (filterType === 'status') {
        state.filters.status = filterValue;
        localStorage.setItem("mn-f-status", filterValue);
      } else if (filterType === 'type') {
        state.filters.type = filterValue;
        localStorage.setItem("mn-f-type", filterValue);
      } else if (filterType === 'content_rating') {
        state.filters.content_rating = filterValue;
        localStorage.setItem("mn-f-cr", filterValue);
      }
      
      // Update UI
      updateFilterChips(filterType);
      updateActiveFilters();
      
      // Trigger search if there's a query
      if (state.q) {
        state.page = 1;
        search();
      }
      
      syncUrl();
    });
  });
  
  // Has anime checkbox
  $("#f-has-anime")?.addEventListener("change", (e) => {
    state.filters.has_anime = e.target.checked;
    localStorage.setItem("mn-f-has-anime", e.target.checked);
    updateActiveFilters();
    if (state.q) {
      state.page = 1;
      search();
    }
    syncUrl();
  });
  
  // Clear all filters
  $("#clear-filters")?.addEventListener("click", () => {
    state.filters = { status: "", type: "", has_anime: false, content_rating: "" };
    localStorage.removeItem("mn-f-status");
    localStorage.removeItem("mn-f-type");
    localStorage.removeItem("mn-f-has-anime");
    localStorage.removeItem("mn-f-cr");
    
    // Update UI
    document.querySelectorAll('.filter-chip').forEach(chip => {
      chip.classList.remove('active');
      if (chip.dataset.value === '') {
        chip.classList.add('active');
      }
    });
    
    $("#f-has-anime").checked = false;
    updateActiveFilters();
    
    if (state.q) {
      state.page = 1;
      search();
    }
    syncUrl();
  });
  
  // Initialize active states
  updateFilterChips('status');
  updateFilterChips('type');
  updateFilterChips('content_rating');
  updateActiveFilters();
}

function updateFilterChips(filterType) {
  const chips = document.querySelectorAll(`[data-filter="${filterType}"]`);
  const currentValue = state.filters[filterType] || "";
  
  chips.forEach(chip => {
    chip.classList.remove('active');
    if (chip.dataset.value === currentValue) {
      chip.classList.add('active');
    }
  });
}

function updateActiveFilters() {
  const activeFiltersContainer = document.getElementById('active-filters');
  const activeFilterChips = document.getElementById('active-filter-chips');
  
  if (!activeFiltersContainer || !activeFilterChips) return;
  
  const activeFilters = [];
  
  // Collect active filters
  if (state.filters.status) {
    activeFilters.push({ type: 'status', value: state.filters.status, label: getFilterLabel('status', state.filters.status) });
  }
  if (state.filters.type) {
    activeFilters.push({ type: 'type', value: state.filters.type, label: getFilterLabel('type', state.filters.type) });
  }
  if (state.filters.content_rating) {
    activeFilters.push({ type: 'content_rating', value: state.filters.content_rating, label: getFilterLabel('content_rating', state.filters.content_rating) });
  }
  if (state.filters.has_anime) {
    activeFilters.push({ type: 'has_anime', value: 'true', label: 'Has Anime' });
  }
  
  // Update UI
  if (activeFilters.length > 0) {
    activeFiltersContainer.style.display = 'flex';
    activeFilterChips.innerHTML = activeFilters.map(filter => `
      <div class="active-filter-chip">
        <span>${filter.label}</span>
        <span class="remove" data-filter-type="${filter.type}">×</span>
      </div>
    `).join('');
    
    // Add remove functionality
    activeFilterChips.querySelectorAll('.remove').forEach(removeBtn => {
      removeBtn.addEventListener('click', () => {
        const filterType = removeBtn.dataset.filterType;
        if (filterType === 'has_anime') {
          state.filters.has_anime = false;
          localStorage.setItem("mn-f-has-anime", false);
          $("#f-has-anime").checked = false;
        } else {
          state.filters[filterType] = "";
          localStorage.removeItem(`mn-f-${filterType}`);
          updateFilterChips(filterType);
        }
        
        updateActiveFilters();
        if (state.q) {
          state.page = 1;
          search();
        }
        syncUrl();
      });
    });
  } else {
    activeFiltersContainer.style.display = 'none';
  }
}

function getFilterLabel(filterType, value) {
  const labels = {
    status: {
      'releasing': 'Releasing',
      'finished': 'Finished',
      'hiatus': 'Hiatus',
      'cancelled': 'Cancelled',
      'upcoming': 'Upcoming'
    },
    type: {
      'manga': 'Manga',
      'manhwa': 'Manhwa',
      'manhua': 'Manhua',
      'novel': 'Novel',
      'one_shot': 'Oneshot'
    },
    content_rating: {
      'safe': 'Safe',
      'suggestive': 'Suggestive',
      'erotica': 'Erotica',
      'pornographic': 'Pornographic'
    }
  };
  
  return labels[filterType]?.[value] || value;
}

/* ===== Drag and Drop ===== */
function initializeDragAndDrop(container, list) {
  if (!container) return;
  
  let draggedElement = null;
  let draggedIndex = -1;
  
  // Add drag handles to each watchlist item
  container.querySelectorAll('.watch-item').forEach((item, index) => {
    // Add drag handle
    const dragHandle = document.createElement('div');
    dragHandle.className = 'drag-handle';
    dragHandle.innerHTML = '⋮⋮';
    dragHandle.title = 'Drag to reorder';
    dragHandle.setAttribute('draggable', 'true');
    
    // Insert drag handle at the beginning of the item
    const main = item.querySelector('.watch-item-main');
    if (main) {
      main.insertBefore(dragHandle, main.firstChild);
    }
    
    // Make the entire item draggable
    item.setAttribute('draggable', 'true');
    item.classList.add('draggable-item');
    
    // Add drag event listeners
    item.addEventListener('dragstart', (e) => {
      draggedElement = item;
      draggedIndex = index;
      item.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/html', item.outerHTML);
      
      // Add visual feedback
      container.classList.add('drag-active');
    });
    
    item.addEventListener('dragend', (e) => {
      item.classList.remove('dragging');
      container.classList.remove('drag-active');
      draggedElement = null;
      draggedIndex = -1;
      
      // Remove all drag-over classes
      container.querySelectorAll('.drag-over').forEach(el => {
        el.classList.remove('drag-over');
      });
    });
    
    item.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      
      // Add visual feedback
      const afterElement = getDragAfterElement(container, e.clientY);
      if (afterElement == null) {
        container.appendChild(item);
      } else {
        container.insertBefore(item, afterElement);
      }
    });
    
    item.addEventListener('dragenter', (e) => {
      e.preventDefault();
      if (item !== draggedElement) {
        item.classList.add('drag-over');
      }
    });
    
    item.addEventListener('dragleave', (e) => {
      item.classList.remove('drag-over');
    });
    
    item.addEventListener('drop', (e) => {
      e.preventDefault();
      item.classList.remove('drag-over');
      
      if (draggedElement && draggedElement !== item) {
        const newIndex = Array.from(container.children).indexOf(item);
        
        // Reorder the list array
        const draggedItem = list[draggedIndex];
        list.splice(draggedIndex, 1);
        list.splice(newIndex, 0, draggedItem);
        
        // Save custom order to localStorage
        saveCustomOrder(list);
        
        // Switch to custom sort mode
        state.sortBy = 'custom';
        localStorage.setItem('mn-sort-by', 'custom');
        
        // Update UI to show custom order controls
        import('./settings.js').then(module => {
          if (module.updateCustomOrderUI) {
            module.updateCustomOrderUI();
          }
        });
        
        // Show success feedback
        toast('Watchlist reordered - switched to custom order', 2000, 'success');
      }
    });
  });
}

function getDragAfterElement(container, y) {
  const draggableElements = [...container.querySelectorAll('.draggable-item:not(.dragging)')];
  
  return draggableElements.reduce((closest, child) => {
    const box = child.getBoundingClientRect();
    const offset = y - box.top - box.height / 2;
    
    if (offset < 0 && offset > closest.offset) {
      return { offset: offset, element: child };
    } else {
      return closest;
    }
  }, { offset: Number.NEGATIVE_INFINITY }).element;
}

function saveCustomOrder(list) {
  const order = list.map(item => item.id);
  localStorage.setItem('mn-custom-order', JSON.stringify(order));
}

function loadCustomOrder() {
  try {
    return JSON.parse(localStorage.getItem('mn-custom-order') || '[]');
  } catch {
    return [];
  }
}

function applyCustomOrder(list) {
  const customOrder = loadCustomOrder();
  if (customOrder.length === 0) return list;
  
  // Create a map for quick lookup
  const itemMap = new Map(list.map(item => [item.id, item]));
  
  // Reorder based on custom order
  const orderedList = [];
  const remainingItems = [...list];
  
  // Add items in custom order
  customOrder.forEach(id => {
    const item = itemMap.get(id);
    if (item) {
      orderedList.push(item);
      remainingItems.splice(remainingItems.findIndex(i => i.id === id), 1);
    }
  });
  
  // Add any remaining items (new items not in custom order)
  orderedList.push(...remainingItems);
  
  return orderedList;
}

/* ===== Watchlist Search ===== */
function initializeWatchlistSearch(list) {
  const searchInput = document.getElementById('watchlist-search');
  const clearButton = document.getElementById('clear-watchlist-search');
  
  if (!searchInput) return;
  
  // Store original list for search filtering
  state.originalWatchlist = [...list];
  
  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase().trim();
    
    if (query === '') {
      // Show clear button and restore original list
      clearButton.style.display = 'none';
      state.watchlistSearchQuery = '';
      loadWatchlist(); // Reload without search filter
    } else {
      // Show clear button and filter list
      clearButton.style.display = 'block';
      state.watchlistSearchQuery = query;
      filterWatchlistBySearch(query);
    }
  });
  
  clearButton.addEventListener('click', () => {
    searchInput.value = '';
    clearButton.style.display = 'none';
    state.watchlistSearchQuery = '';
    loadWatchlist(); // Reload without search filter
  });
}

function filterWatchlistBySearch(query) {
  const watchlistContainer = document.getElementById('watchlist');
  if (!watchlistContainer) return;
  
  const items = watchlistContainer.querySelectorAll('.watch-item');
  let visibleCount = 0;
  
  items.forEach(item => {
    const title = item.querySelector('.watch-item-title')?.textContent?.toLowerCase() || '';
    const description = item.querySelector('.watch-item-meta')?.textContent?.toLowerCase() || '';
    const tags = item.querySelector('.watch-tags')?.textContent?.toLowerCase() || '';
    
    const matches = title.includes(query) || 
                   description.includes(query) || 
                   tags.includes(query);
    
    if (matches) {
      item.style.display = '';
      visibleCount++;
    } else {
      item.style.display = 'none';
    }
  });
  
  // Update count display
  const countElement = document.getElementById('watch-count');
  if (countElement) {
    countElement.textContent = `${visibleCount} item${visibleCount === 1 ? '' : 's'} (filtered)`;
  }
}

/* ===== Tag Management ===== */
function initializeTagFiltering(list) {
  const tagFilter = document.getElementById('tag-filter');
  if (!tagFilter) return;
  
  // Extract all unique tags from the watchlist
  const allTags = new Set();
  list.forEach(item => {
    if (item.tags && Array.isArray(item.tags)) {
      item.tags.forEach(tag => allTags.add(tag));
    }
  });
  
  // Populate tag filter dropdown
  tagFilter.innerHTML = '<option value="">All tags</option>';
  Array.from(allTags).sort().forEach(tag => {
    const option = document.createElement('option');
    option.value = tag;
    option.textContent = tag;
    tagFilter.appendChild(option);
  });
  
  // Handle tag filtering
  tagFilter.addEventListener('change', (e) => {
    const selectedTag = e.target.value;
    state.selectedTag = selectedTag;
    localStorage.setItem('mn-selected-tag', selectedTag);
    filterWatchlistByTag(selectedTag);
  });
  
  // Load saved tag filter
  const savedTag = localStorage.getItem('mn-selected-tag');
  if (savedTag) {
    tagFilter.value = savedTag;
    state.selectedTag = savedTag;
  }
}

function filterWatchlistByTag(tag) {
  const watchlistContainer = document.getElementById('watchlist');
  if (!watchlistContainer) return;
  
  const items = watchlistContainer.querySelectorAll('.watch-item');
  let visibleCount = 0;
  
  items.forEach(item => {
    if (!tag) {
      // Show all items
      item.style.display = '';
      visibleCount++;
    } else {
      // Check if item has the selected tag
      const itemTags = item.dataset.tags ? item.dataset.tags.split(',') : [];
      if (itemTags.includes(tag)) {
        item.style.display = '';
        visibleCount++;
      } else {
        item.style.display = 'none';
      }
    }
  });
  
  // Update count display
  const countElement = document.getElementById('watch-count');
  if (countElement) {
    const suffix = tag ? ` (tag: ${tag})` : '';
    countElement.textContent = `${visibleCount} item${visibleCount === 1 ? '' : 's'}${suffix}`;
  }
}
