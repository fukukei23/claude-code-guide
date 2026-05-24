/* Claude Code Guide — Interactive Features */

(function () {
    "use strict";

    // --- Theme Toggle ---
    function initTheme() {
        var saved = localStorage.getItem("cc-guide-theme");
        var prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        var theme = saved || (prefersDark ? "dark" : "light");
        document.documentElement.setAttribute("data-theme", theme);
    }

    function toggleTheme() {
        var current = document.documentElement.getAttribute("data-theme");
        var next = current === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        localStorage.setItem("cc-guide-theme", next);
    }

    // --- Sidebar Navigation ---
    function initSidebar() {
        var toggle = document.getElementById("menuToggle");
        var sidebar = document.getElementById("sidebar");
        var overlay = document.getElementById("sidebarOverlay");
        if (!toggle || !sidebar) return;

        toggle.addEventListener("click", function () {
            toggle.classList.toggle("active");
            sidebar.classList.toggle("open");
            if (overlay) overlay.classList.toggle("visible");
        });

        if (overlay) {
            overlay.addEventListener("click", function () {
                toggle.classList.remove("active");
                sidebar.classList.remove("open");
                overlay.classList.remove("visible");
            });
        }
    }

    // --- Initialize ---
    initTheme();
    initSidebar();

    var themeBtn = document.getElementById("themeToggle");
    if (themeBtn) {
        themeBtn.addEventListener("click", toggleTheme);
    }
})();
