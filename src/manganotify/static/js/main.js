// Entry point – wire everything
import "./api.js"; // just to ensure early fetch helpers in cache
import "./auth.js"; // auth system
import { initSettings } from "./settings.js";
import {wireSearchBox, applyLayout, search, loadWatchlist, selectTab} from "./ui.js";
import { initNotifications, loadNotifications } from "./notifications-ui.js";
import { state, MIN_QUERY_LEN } from "./state.js";
import { $ } from "./ui.js";
import { auth } from "./auth.js";

// console.log("[MN] main.js loaded", import.meta.url);

queueMicrotask(async () => {
  try{
    // Initialize auth first
    await auth.init();
    
    initSettings();
    wireSearchBox();
    applyLayout(state.layout);
    initNotifications();
    
            // Wire auth UI
            $("#login-btn")?.addEventListener("click", () => $("#login-modal")?.showModal());
            $("#logout-btn")?.addEventListener("click", () => auth.logout());
            $("#login-close")?.addEventListener("click", () => $("#login-modal")?.close());
            $("#login-cancel")?.addEventListener("click", () => $("#login-modal")?.close());
            $("#create-login-btn")?.addEventListener("click", () => {
              $("#login-modal")?.close();
              window.location.href = '/setup';
            });
    
    $("#login-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const username = $("#login-username")?.value;
      const password = $("#login-password")?.value;
      if (username && password) {
        await auth.login(username, password);
      }
    });
    
    // main.js
    const ENABLE_SHORTCUTS = false;
    if (ENABLE_SHORTCUTS) {
      const { initKeyboard } = await import("/keyboard.js");
      initKeyboard({
        focusSearch: () => document.getElementById("q")?.focus(),
        refreshWatchlist: () => loadWatchlist(),
        openSettings: () => openSettings(),
        toggleTheme: () => document.getElementById("theme")?.click(),
        selectTab: (name) => selectTab(name)
      });
    }

    // initial data (only if authenticated)
    if (auth.requireAuth()) {
      await loadWatchlist();
      await loadNotifications();

      // if there is a query in URL, run a search immediately
      const qinit = $("#q")?.value.trim() || "";
      if(qinit.length >= MIN_QUERY_LEN){ state.q = qinit; state.page = 1; search(); }
    }

    // console.log("[MN] bootstrap complete");
  }catch(e){
    // console.error("[MN] bootstrap failed:", e);
  }
});
