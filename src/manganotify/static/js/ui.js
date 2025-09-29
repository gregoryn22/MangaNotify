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
  } else if (val.length === 0) {
    $("#results-panel").hidden = true; $("#result-info").textContent = "";
  }
}, TYPE_DEBOUNCE_MS);

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
  }catch(e){
    if(e.name==="AbortError") return;
    const errorMsg = e.toString().replace(/[<>]/g, "");
    $("#results").innerHTML = `<div style="padding:18px" class="subline">Search failed. ${errorMsg}</div>`;
    setStatus("Search failed");
  }
}

function renderResults(js){
  const items = js.data || js.results || [];
  const p = js.pagination || null;
  state.pagination = p;

  const info = p ? `Page ${p.page} · ${p.count} result${p.count===1?"":"s"}`
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
      </div>`;
    box.appendChild(el);

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

/* ===== Watchlist ===== */
export async function loadWatchlist(){
  if (!auth.requireAuth()) return;
  
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
  $("#q")?.addEventListener("input", debouncedSearch);
  $("#go")?.addEventListener("click", ()=>{
    const v=$("#q").value.trim(); if(v.length>=MIN_QUERY_LEN){ state.q=v; state.page=1; syncUrl(); search(); }
  });
  $("#clear-q")?.addEventListener("click", ()=>{
    $("#q").value=""; state.q=""; $("#results-panel").hidden=true; $("#result-info").textContent=""; syncUrl();
  });

  $("#prev")?.addEventListener("click", ()=>{ if(state.pagination?.previous){ state.page=Math.max(1,(state.pagination.page||1)-1); search(); } });
  $("#next")?.addEventListener("click", ()=>{ if(state.pagination?.next){ state.page=(state.pagination.page||1)+1; search(); } });

  // Tab buttons (only visible in tabs layout)
  document.getElementById("tab-watch")?.addEventListener("click", ()=>selectTab("watch"));
  document.getElementById("tab-search")?.addEventListener("click", ()=>selectTab("search"));
  document.getElementById("tab-notif")?.addEventListener("click", ()=>selectTab("notif"));
}
