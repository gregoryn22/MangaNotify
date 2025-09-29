// Shared state & constants
export const MIN_QUERY_LEN = 3;
export const TYPE_DEBOUNCE_MS = 500;

export const state = {
  q: "", page: 1, limit: 20, pagination: null,
  sortBy: localStorage.getItem("mn-sort-by")  || "title",
  sortDir: localStorage.getItem("mn-sort-dir") || "asc",
  unreadOnly: localStorage.getItem("mn-unread-only") === "true",
  showCovers: localStorage.getItem("mn-show-covers") !== "false",
  hideDropped: localStorage.getItem("mn-hide-dropped") === "true",
  useEmojis: localStorage.getItem("mn-use-emojis") !== "false", // Default to true
  autoRefresh: +(localStorage.getItem("mn-auto-refresh") || "0"),
  autoTimer: null,
  lastRefreshTs: null,
  online: navigator.onLine,
  filters: {
    status:        localStorage.getItem("mn-f-status") || "",
    type:          localStorage.getItem("mn-f-type") || "",
    has_anime:     localStorage.getItem("mn-f-has-anime") === "true",
    content_rating:localStorage.getItem("mn-f-cr") || ""
  },
  aborter: null,
  layout: localStorage.getItem("mn-layout") || "stack",
  
  // New customization settings
  layoutDensity: localStorage.getItem("mn-layout-density") || "normal", // compact, normal, spacious
  showIds: localStorage.getItem("mn-show-ids") !== "false", // Default to true
  showLastChecked: localStorage.getItem("mn-show-last-checked") !== "false", // Default to true
  showContentRating: localStorage.getItem("mn-show-content-rating") !== "false", // Default to true
  showStatus: localStorage.getItem("mn-show-status") !== "false", // Default to true
  customAccentColor: localStorage.getItem("mn-custom-accent") || "",
  quietHoursEnabled: localStorage.getItem("mn-quiet-hours-enabled") === "true",
  quietHoursStart: localStorage.getItem("mn-quiet-hours-start") || "22:00",
  quietHoursEnd: localStorage.getItem("mn-quiet-hours-end") || "08:00",
  notificationBatching: localStorage.getItem("mn-notification-batching") || "off", // off, hourly, daily
  batchNotifications: [], // Store pending notifications for batching
  fontSize: localStorage.getItem("mn-font-size") || "normal", // small, normal, large
  buttonSize: localStorage.getItem("mn-button-size") || "normal", // small, normal, large
};

// tiny cache just for searches
export const searchCache = new Map();

// datetime helpers
export const dtFormatter = new Intl.DateTimeFormat(undefined, {
  year:"numeric", month:"short", day:"2-digit",
  hour:"2-digit", minute:"2-digit", hour12:false, timeZoneName:"short"
});
