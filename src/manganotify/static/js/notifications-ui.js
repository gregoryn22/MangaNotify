import api from "./api.js";
import { timeAgo, getIcon } from "./ui.js";
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
    if (!items.length) { 
      box.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">${getIcon("🔔", "📭")}</div>
          <div class="empty-state-title">No notifications yet</div>
          <div class="empty-state-description">You'll see notifications here when new manga chapters are released.</div>
        </div>`; 
      return; 
    }
    
    // Group notifications by series
    const grouped = groupNotificationsBySeries(items);
    box.innerHTML = renderGroupedNotifications(grouped);

    // Add event listeners
    addNotificationEventListeners(box);
  }catch(e){
    const errorMsg = e.toString().replace(/[<>]/g, "");
    box && (box.innerHTML = `<div class="subline" style="padding:10px 12px">Failed to load: ${errorMsg}</div>`);
  }
}

function groupNotificationsBySeries(notifications) {
  const groups = {};
  
  notifications.forEach(notif => {
    const seriesId = notif.series_id || notif.id || 'unknown';
    const seriesTitle = notif.title || notif.series || 'Unknown Series';
    
    if (!groups[seriesId]) {
      groups[seriesId] = {
        title: seriesTitle,
        notifications: [],
        latestTime: null
      };
    }
    
    groups[seriesId].notifications.push(notif);
    
    // Track latest notification time for sorting
    const notifTime = new Date(notif.detected_at || notif.created_at || notif.timestamp || notif.time || 0);
    if (!groups[seriesId].latestTime || notifTime > groups[seriesId].latestTime) {
      groups[seriesId].latestTime = notifTime;
    }
  });
  
  // Sort groups by latest notification time
  return Object.values(groups).sort((a, b) => b.latestTime - a.latestTime);
}

function renderGroupedNotifications(groups) {
  return groups.map(group => {
    const latestNotif = group.notifications[0];
    const when = latestNotif.detected_at || latestNotif.created_at || latestNotif.timestamp || latestNotif.time || "";
    const count = group.notifications.length;
    
    return `
      <div class="notif-group">
        <div class="notif-group-header">
          <div class="notif-group-title">
            <span class="notif-series-title">${group.title.replace(/[<>]/g, "")}</span>
            <span class="notif-count-badge">${count} ${count === 1 ? 'update' : 'updates'}</span>
          </div>
          <div class="notif-group-meta">${when ? timeAgo(when) : ""}</div>
        </div>
        <div class="notif-group-items">
          ${group.notifications.slice(0, 3).map(n => {
            const message = n.message ? n.message.replace(/[<>]/g, "") : "";
            const id = n.id ? n.id.toString().replace(/[<>]/g, "") : "";
            return `
              <div class="notif-item-small">
                <div class="notif-message">${message}</div>
                <div class="notif-item-actions">
                  ${id ? `<button class="btn btn-sm" data-copy="${id}" title="Copy ID">Copy</button>` : ""}
                </div>
              </div>
            `;
          }).join("")}
          ${group.notifications.length > 3 ? 
            `<div class="notif-more">+${group.notifications.length - 3} more updates</div>` : 
            ""
          }
        </div>
      </div>
    `;
  }).join("");
}

function addNotificationEventListeners(container) {
  // Copy buttons
  container.querySelectorAll("[data-copy]").forEach(btn => {
    btn.addEventListener("click", async () => {
      try { 
        await navigator.clipboard.writeText(String(btn.getAttribute("data-copy"))); 
        toast("ID copied", 1500, "success");
      } catch {}
    });
  });
  
  // Expand/collapse groups
  container.querySelectorAll(".notif-group-header").forEach(header => {
    header.addEventListener("click", () => {
      const group = header.closest(".notif-group");
      group.classList.toggle("expanded");
    });
  });
}
