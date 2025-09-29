// Small fetch helpers + endpoint wrappers
function getAuthHeaders() {
  const token = localStorage.getItem('auth_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

async function jget(url, init){ 
  const headers = { ...getAuthHeaders(), ...(init?.headers || {}) };
  const r = await fetch(url, { ...init, headers }); 
  if(!r.ok) throw new Error(`HTTP ${r.status}`); 
  return r.json(); 
}
async function jpost(url, body){ 
  const headers = { 'Content-Type': 'application/json', ...getAuthHeaders() };
  const r = await fetch(url, { method: "POST", headers, body: JSON.stringify(body||{}) }); 
  if(!r.ok) throw new Error(`HTTP ${r.status}`); 
  return r.json(); 
}
async function jpatch(url, body){ 
  const headers = { 'Content-Type': 'application/json', ...getAuthHeaders() };
  const r = await fetch(url, { method: "PATCH", headers, body: JSON.stringify(body||{}) }); 
  if(!r.ok) throw new Error(`HTTP ${r.status}`); 
  return r.json(); 
}
async function jdel(url){ 
  const headers = getAuthHeaders();
  const r = await fetch(url, { method: "DELETE", headers }); 
  if(!r.ok) throw new Error(`HTTP ${r.status}`); 
  return r.json(); 
}

export const api = {
  health:          ()=> jget("/api/health"),
  search:          (params)=> jget(`/api/search?${new URLSearchParams(params||{})}`),
  series:          (id, full=true)=> jget(`/api/series/${id}?full=${full?"true":"false"}`),
  watchlist:       (params)=> jget(`/api/watchlist${params && params.status ? `?status=${encodeURIComponent(params.status)}` : ""}`),
  addWatch:        (item)=> jpost("/api/watchlist", item),
  removeWatch:     (id)=> jdel(`/api/watchlist/${id}`),
  readNext:        (id)=> jpost(`/api/watchlist/${id}/read/next`),
  setProgress:     (id, body)=> jpatch(`/api/watchlist/${id}/progress`, body),
  setStatus:       (id, status)=> jpatch(`/api/watchlist/${id}/status`, { status }),
  refreshNow:      ()=> jpost("/api/watchlist/refresh"),
  // Notification preferences
  getNotificationPrefs: (id)=> jget(`/api/watchlist/${id}/notifications`),
  updateNotificationPrefs: (id, prefs)=> jpatch(`/api/watchlist/${id}/notifications`, prefs),
  notifications:   ()=> jget("/api/notifications"),
  clearNotifications: ()=> jdel("/api/notifications"),
  notifyTest:      ()=> jpost("/api/notify/test"),
  // Discord notification endpoints
  getDiscordSettings: () => jget("/api/discord/settings"),
  setDiscordSettings: (body) => jpost("/api/discord/settings", body),
  discordTest: () => jpost("/api/discord/test"),
  // Auth endpoints
  login:           (username, password)=> jpost("/api/auth/login", { username, password }),
  logout:          ()=> jpost("/api/auth/logout"),
  getMe:           ()=> jget("/api/auth/me"),
  authStatus:      ()=> jget("/api/auth/status"),
};

export default api;
