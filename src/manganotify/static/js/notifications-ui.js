import api from "./api.js";
import { timeAgo } from "./ui.js";
import { auth } from "./auth.js";

export function initNotifications(){
  // nothing extra; buttons are wired in settings.js
  loadNotifications();
}

export async function loadNotifications(){
  if (!auth.requireAuth()) return;
  
  const box = document.getElementById("notif-list");
  const count = document.getElementById("notif-count");
  try{
    const js = await api.notifications();
    const items = js.data || js.results || [];
    count && (count.textContent = `${items.length} entr${items.length===1?"y":"ies"}`);
    if (!box) return;
    if (!items.length) { box.innerHTML = `<div class="subline" style="padding:0 12px 12px">No notifications yet.</div>`; return; }
    box.innerHTML = items.map(n => {
      const when = n.detected_at || n.created_at || n.timestamp || n.time || "";
      const title = (n.title || n.series || "Notification").replace(/[<>]/g, "");
      const message = n.message ? n.message.replace(/[<>]/g, "") : "";
      const id = n.id ? n.id.toString().replace(/[<>]/g, "") : "";
      return `
      <div class="notif-item">
        <div class="notif-left">
          <div class="notif-title">${title}</div>
          <div class="notif-meta">${when ? timeAgo(when) : ""} · <span class="mono">${id}</span></div>
          ${message ? `<div class="subline" style="margin-top:4px">${message}</div>` : ""}
        </div>
        <div class="notif-actions">
          ${id ? `<button class="btn" data-copy="${id}">Copy ID</button>` : ""}
        </div>
      </div>`;
    }).join("");

    // copy buttons
    box.querySelectorAll("[data-copy]").forEach(btn=>{
      btn.addEventListener("click", async ()=>{
        try{ await navigator.clipboard.writeText(String(btn.getAttribute("data-copy"))); }catch{}
      });
    });
  }catch(e){
    const errorMsg = e.toString().replace(/[<>]/g, "");
    box && (box.innerHTML = `<div class="subline" style="padding:10px 12px">Failed to load: ${errorMsg}</div>`);
  }
}
