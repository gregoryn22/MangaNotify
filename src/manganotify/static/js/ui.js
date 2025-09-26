import { state, MIN_QUERY_LEN, TYPE_DEBOUNCE_MS, searchCache, dtFormatter } from "./state.js";
import api from "./api.js";

/* ===== DOM utils & formatting ===== */
export const $  = (s)=>document.querySelector(s);
export const $$ = (s)=>Array.from(document.querySelectorAll(s));
export function debounce(fn, ms=350){ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), ms); }; }
export function buildQuery(params){ return Object.entries(params).filter(([,v])=>v!=="" && v!==undefined && v!==null).map(([k,v])=>`${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join("&"); }

export function getCoverUrl(c){ if(!c) return ""; if(typeof c==="string") return c; if(typeof c==="object") return c.small||c.default||c.raw||""; return ""; }
export function toast(msg, ms=2200){ const t=$("#toast"); if(!t) return; t.textContent=msg; t.classList.add("show"); setTimeout(()=>t.classList.remove("show"), ms); }
export function setStatus(text){
  const el = document.getElementById("status");
  if (el) el.textContent = text || "—";
}
export function parseProgress(v){ const n=parseFloat(String(v??"").replace(",",".")); return Number.isFinite(n)?Math.max(0,n):0; }
export function unreadCount(total,lastRead){ const t=Number(total)||0; const r=parseProgress(lastRead); return Math.max(0,t-Math.floor(r)); }
export function formatLocal(iso){ try{ return dtFormatter.format(new Date(iso)); } catch { return iso||""; } }
export function timeAgo(iso){
  try{ const then=new Date(iso).getTime(); if(!Number.isFinite(then)) return "";
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
$("#modal-close")?.addEventListener("click", ()=> modal?.close());

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
  if(!state.q){ $("#results-panel").hidden=true; return; }
  if(state.aborter){ state.aborter.abort(); }
  state.aborter = new AbortController();

  setStatus("Searching…");
  $("#results-panel").hidden=false;
  $("#results").innerHTML = Array.from({length:8}).map(()=>`
    <div class="card" role="listitem" aria-busy="true">
      <div class="cover shimmer"></div>
      <div class="meta">
        <div class="title shimmer" style="height:16px;border-radius:6px"></div>
        <div class="subline shimmer" style="height:12px;border-radius:6px;width:70%"></div>
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
    $("#results").innerHTML = `<div style="padding:18px" class="subline">Search failed. ${e}</div>`;
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
    box.innerHTML = `<div style="padding:18px" class="subline">No results.</div>`;
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
          <button class="btn" data-add="${it.id}">Watch</button>
          <button class="btn" data-open="${it.id}">Open</button>
          <button class="btn" data-details="${it.id}">Details</button>
          <button class="btn" data-copy="${it.id}" title="Copy ID">Copy ID</button>
        </div>
      </div>`;
    box.appendChild(el);

    const img = el.querySelector("img");
    if(img){
      img.addEventListener("load", ()=> el.querySelector(".cover").classList.remove("shimmer"));
      img.addEventListener("error", ()=> el.querySelector(".cover").classList.add("shimmer"));
    }

    el.querySelector(`[data-add="${it.id}"]`).onclick = async ()=>{
      try{
        await api.addWatch({ id: it.id, title, total_chapters: total, last_read: 0, cover });
        toast("Added to watchlist"); await loadWatchlist();
      }catch{ toast("Failed to add", 2600); }
    };
    el.querySelector(`[data-open="${it.id}"]`).onclick = ()=> window.open(`https://mangabaka.dev/${it.id}`, "_blank");
    el.querySelector(`[data-copy="${it.id}"]`).onclick = async ()=>{ try{ await navigator.clipboard.writeText(String(it.id)); toast("ID copied"); }catch{ toast("Copy failed", 2200); } };
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
  modal.showModal();
  try{
    // Your server exposes /api/series/{id}
    const js = await api.series(id, true);
    const s  = js.minimal || {};
    const merged = js.merged_with ? `<span class="badge">merged → ${js.merged_with}</span>` : "";
    const linksHtml = []; // populate later if you add /links

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

/* ===== Watchlist ===== */
export async function loadWatchlist(){
  const js = await api.watchlist();
  let list = js.data || [];

  if(state.unreadOnly){
    list = list.filter(it=>{
      const total = Number.isFinite(+it.total_chapters) ? +it.total_chapters : null;
      const lastRead = parseProgress(it.last_read ?? 0);
      const unread = total!==null ? unreadCount(total, lastRead) : 0;
      return unread > 0;
    });
  }

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
    box.innerHTML = `<div class="subline" style="padding:0 12px 16px">Nothing here yet. Add items from the search results.</div>`;
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
      <div style="min-width:0; display:flex; gap:10px; align-items:flex-start">
        ${behind ? `<span class="unread-dot" title="Unread chapters"></span>` : ``}
        ${state.showCovers && it.cover ? `<img src="${it.cover}" alt="" width="40" height="60" loading="lazy" decoding="async" style="border-radius:6px; border:1px solid var(--border); object-fit:cover" />` : ""}
        <div style="min-width:0">
          <div style="font-weight:700; overflow:hidden; text-overflow:ellipsis; white-space:nowrap" title="${it.title || ""}">
            ${it.title || "(no title)"} ${mergeTxt}
          </div>
          <div class="subline" title="${it.last_checked ? formatLocal(it.last_checked) : ""}">
            ID: <code>${it.id}</code>
            · Chapters: ${total ?? "—"}
            ${lastCheckedTxt} ${lastChapterTxt}
            ${it.status? ` · ${it.status}` : ""} ${it.content_rating? ` · ${it.content_rating}` : ""}
          </div>
          <div class="row" style="margin-top:6px; gap:8px">
            <span class="badge ${behind ? "warn":"ok"}" title="Unread chapters">
              ${behind ? "Unread" : "Up to date"}${total!==null ? `: ${unread}` : ""}
            </span>
            ${total!==null ? `<span class="badge">Read: ${String(lastRead).replace(/\.0$/,"")}/${total}</span>` : ""}
          </div>
        </div>
      </div>

      <div class="controls">
        ${total!==null ? `
          <button class="btn" data-prev="${it.id}" title="Decrement read (−1)">−1</button>
          <input class="input-mini" type="number" min="0" ${total!==null ? `max="${total}"`:""}
                 step="1" value="${String(lastRead).replace(/\.0$/,"")}" aria-label="Last read chapter" data-lr="${it.id}" />
          <button class="btn" data-set="${it.id}" title="Set last read">Set</button>
          <button class="btn" data-next="${it.id}" title="Increment read (+1)">+1</button>
          <button class="btn" data-latest="${it.id}" title="Mark latest">Mark latest</button>
        ` : ""}
        <button class="btn" data-details="${it.id}" title="Details">Details</button>
        <button class="btn" data-open="${it.id}" title="Open series page">Open</button>
        <button class="btn" data-copy="${it.id}" title="Copy ID">Copy ID</button>
        <button class="btn" data-remove="${it.id}" title="Remove">🗑</button>
      </div>
    `;

    const id = it.id;
    row.querySelector(`[data-open="${id}"]`).onclick = ()=> window.open(`https://mangabaka.dev/${id}`, "_blank");
    row.querySelector(`[data-copy="${id}"]`).onclick = async ()=>{ try{ await navigator.clipboard.writeText(String(id)); toast("ID copied"); }catch{ toast("Copy failed", 2200); } };
    row.querySelector(`[data-details="${id}"]`).onclick = ()=> openDetails(id, it.title || `Series ${id}`);
    row.querySelector(`[data-remove="${id}"]`).onclick = async ()=>{ try{ await api.removeWatch(id); toast("Removed"); loadWatchlist(); }catch{ toast("Failed to remove",2600);} };

    const inp = row.querySelector(`[data-lr="${id}"]`);
    row.querySelector(`[data-set="${id}"]`)?.addEventListener("click", async ()=>{
      const val = parseProgress(inp.value);
      try{ await api.setProgress(id, { last_read: val }); toast("Progress updated"); loadWatchlist(); }
      catch{ toast("Failed to update", 2600); }
    });
    row.querySelector(`[data-next="${id}"]`)?.addEventListener("click", async ()=>{
      try{ await api.readNext(id); toast("+1 read"); loadWatchlist(); } catch{ toast("Failed to bump",2600); }
    });
    row.querySelector(`[data-prev="${id}"]`)?.addEventListener("click", async ()=>{
      try{ await api.setProgress(id, { decrement: 1 }); toast("−1 read"); loadWatchlist(); } catch{ toast("Failed to decrement",2600); }
    });

    $("#watchlist").appendChild(row);
  }

  state.lastRefreshTs = Date.now();
}

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
  const map = { watch: "#watchlist-panel", search:"#search-group", notif:"#notifications" };
  for(const [key, sel] of Object.entries(map)){
    const on = key===name || (name==="search" && key==="search");
    document.querySelector(sel).hidden = !on;
    document.getElementById(`tab-${key}`)?.setAttribute("aria-selected", on ? "true" : "false");
  }
}

export function applyLayout(v){
  state.layout = v;
  localStorage.setItem("mn-layout", v);
  document.body.setAttribute("data-layout", v);
  if(v==="tabs"){ selectTab("search"); }
  if(v!=="tabs"){
    $("#search-group").hidden=false; $("#watchlist-panel").hidden=false; $("#notifications").hidden=false;
  }
}

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
}

function openSettings(){
  drawer.classList.add("open");
  drawer.setAttribute("aria-hidden","false");
  $("#open-settings").setAttribute("aria-expanded","true");
  document.body.classList.add("drawer-open");   // NEW: show scrim
}
function closeSettings(){
  drawer.classList.remove("open");
  drawer.setAttribute("aria-hidden","true");
  $("#open-settings").setAttribute("aria-expanded","false");
  document.body.classList.remove("drawer-open"); // NEW: hide scrim
}
