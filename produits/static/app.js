document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const sidebarBackdrop = document.getElementById("sidebarBackdrop");
  const mobileToggle = document.getElementById("sidebarToggle");
  const collapseToggle = document.getElementById("sidebarCollapse");
  const themeToggle = document.getElementById("themeToggle");
  const collapseKey = "sidebarCollapsed";
  const themeKey = "uiTheme";

  const isMobile = () => window.innerWidth <= 980;
  const closeMobileSidebar = () => {
    if (!sidebar) return;
    sidebar.classList.remove("open");
    document.body.classList.remove("sidebar-open");
  };
  const toggleMobileSidebar = () => {
    if (!sidebar) return;
    const open = !sidebar.classList.contains("open");
    sidebar.classList.toggle("open", open);
    document.body.classList.toggle("sidebar-open", open);
  };
  const applyCollapsed = (collapsed) => {
    document.body.classList.toggle("sidebar-collapsed", collapsed);
  };
  const applyTheme = (theme) => {
    const isDark = theme === "dark";
    document.body.classList.toggle("theme-dark", isDark);
    document.body.classList.toggle("theme-light", !isDark);
    if (themeToggle) {
      themeToggle.setAttribute("aria-pressed", isDark ? "true" : "false");
      const label = isDark ? "Activer mode clair" : "Activer mode sombre";
      themeToggle.setAttribute("aria-label", label);
      themeToggle.title = label;
    }
  };

  const savedTheme = localStorage.getItem(themeKey);
  const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(savedTheme || (prefersDark ? "dark" : "light"));

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const nextTheme = document.body.classList.contains("theme-dark") ? "light" : "dark";
      applyTheme(nextTheme);
      localStorage.setItem(themeKey, nextTheme);
    });
  }

  if (mobileToggle && sidebar) {
    mobileToggle.addEventListener("click", () => {
      toggleMobileSidebar();
    });
  }

  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener("click", closeMobileSidebar);
  }

  if (!isMobile()) {
    const saved = localStorage.getItem(collapseKey);
    applyCollapsed(saved === "1");
  } else {
    applyCollapsed(false);
  }

  if (collapseToggle && sidebar) {
    collapseToggle.addEventListener("click", () => {
      if (isMobile()) {
        sidebar.classList.toggle("open");
        return;
      }
      const collapsed = !document.body.classList.contains("sidebar-collapsed");
      applyCollapsed(collapsed);
      localStorage.setItem(collapseKey, collapsed ? "1" : "0");
    });
  }

  window.addEventListener("resize", () => {
    if (isMobile()) {
      applyCollapsed(false);
    } else {
      closeMobileSidebar();
      const saved = localStorage.getItem(collapseKey);
      applyCollapsed(saved === "1");
    }
  });

  const links = document.querySelectorAll("[data-nav]");
  const path = window.location.pathname;
  links.forEach(link => {
    if (link.getAttribute("href") === path) {
      link.classList.add("active");
    }
    link.addEventListener("click", () => {
      if (isMobile()) closeMobileSidebar();
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMobileSidebar();
  });
});
