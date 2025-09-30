// Quick Actions Toolbar functionality
export function initializeQuickActions() {
  const quickActions = document.getElementById('quick-actions');
  if (!quickActions) return;
  
  let isVisible = false;
  let scrollTimeout = null;
  
  // Show/hide based on scroll position
  function handleScroll() {
    const scrollY = window.scrollY;
    const shouldShow = scrollY > 200; // Show after scrolling 200px
    
    if (shouldShow && !isVisible) {
      quickActions.style.display = 'block';
      setTimeout(() => quickActions.classList.add('visible'), 10);
      isVisible = true;
    } else if (!shouldShow && isVisible) {
      quickActions.classList.remove('visible');
      setTimeout(() => quickActions.style.display = 'none', 300);
      isVisible = false;
    }
  }
  
  // Throttled scroll handler
  window.addEventListener('scroll', () => {
    if (scrollTimeout) return;
    scrollTimeout = setTimeout(() => {
      handleScroll();
      scrollTimeout = null;
    }, 100);
  });
  
  // Quick action button handlers
  document.getElementById('qa-refresh')?.addEventListener('click', async () => {
    try {
      // Import loadWatchlist function
      const { loadWatchlist } = await import('./ui.js');
      await loadWatchlist();
      
      // Import toast function
      const { toast } = await import('./ui.js');
      toast('Watchlist refreshed', 1500, 'success');
    } catch (error) {
      console.error('Refresh failed:', error);
    }
  });
  
  document.getElementById('qa-search')?.addEventListener('click', () => {
    document.getElementById('q')?.focus();
    // Scroll to search if needed
    const searchInput = document.getElementById('q');
    if (searchInput) {
      searchInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  });
  
  document.getElementById('qa-settings')?.addEventListener('click', () => {
    // Import and call openSettings function
    import('./settings.js').then(module => {
      if (module.openSettings) {
        module.openSettings();
      }
    });
  });
  
  document.getElementById('qa-theme')?.addEventListener('click', () => {
    document.getElementById('theme-alt')?.click();
  });
  
  document.getElementById('qa-scroll-top')?.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
  
  // Update theme icon based on current theme
  function updateThemeIcon() {
    const themeIcon = document.querySelector('#qa-theme .qa-icon');
    if (themeIcon) {
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      themeIcon.textContent = isDark ? '☀️' : '🌙';
    }
  }
  
  // Listen for theme changes
  const themeObserver = new MutationObserver(updateThemeIcon);
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme']
  });
  
  // Initial theme icon update
  updateThemeIcon();
}
