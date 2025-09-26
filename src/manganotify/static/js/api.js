// Small fetch helpers + endpoint wrappers
async function jget(url, init){ const r = await fetch(url, init); if(!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }
async function jpost(url, body){ const r = await fetch(url,{method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body||{})}); if(!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }
async function jpatch(url, body){ const r = await fetch(url,{method:"PATCH", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body||{})}); if(!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }
async function jdel(url){ const r = await fetch(url,{method:"DELETE"}); if(!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }

export const api = {
  health:          ()=> jget("/api/health"),
  search:          (params)=> jget(`/api/search?${new URLSearchParams(params||{})}`),
  series:          (id, full=true)=> jget(`/api/series/${id}?full=${full?"true":"false"}`),
  watchlist:       ()=> jget("/api/watchlist"),
  addWatch:        (item)=> jpost("/api/watchlist", item),
  removeWatch:     (id)=> jdel(`/api/watchlist/${id}`),
  readNext:        (id)=> jpost(`/api/watchlist/${id}/read/next`),
  setProgress:     (id, body)=> jpatch(`/api/watchlist/${id}/progress`, body),
  refreshNow:      ()=> jpost("/api/watchlist/refresh"),
  notifications:   ()=> jget("/api/notifications"),
  clearNotifications: ()=> jdel("/api/notifications"),
  notifyTest:      ()=> jpost("/api/notify/test"),
};

export default api;
