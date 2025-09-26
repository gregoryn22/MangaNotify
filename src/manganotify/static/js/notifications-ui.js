import api from "./api.js";
import { timeAgo } from "./ui.js";

export function initNotifications(){
  // nothing extra; buttons are wired in settings.js
  loadNotifications();
}

export async function loadNotifications(){
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
      return `
      <div class="notif-item">
        <div class="notif-left">
          <div class="notif-title">${n.title || n.series || "Notification"}</div>
          <div class="notif-meta">${when ? timeAgo(when) : ""} · <span class="mono">${n.id || ""}</span></div>
          ${n.message ? `<div class="subline" style="margin-top:4px">${n.message}</div>` : ""}
        </div>
        <div class="notif-actions">
          ${n.id ? `<button class="btn" data-copy="${n.id}">Copy ID</button>` : ""}
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
    box && (box.innerHTML = `<div class="subline" style="padding:10px 12px">Failed to load: ${e}</div>`);
  }
}
