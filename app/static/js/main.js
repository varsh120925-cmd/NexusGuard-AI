/**
 * NexusGuard Main JavaScript Client
 * Manages API communication, Chart.js instances, live forms, and alerts.
 */

// Global state
window.NexusApp = {
    token: localStorage.getItem("nexus_token") || null,
    user: JSON.parse(localStorage.getItem("nexus_user") || "null"),

    setAuth: function(token, user) {
        this.token = token;
        this.user = user;
        localStorage.setItem("nexus_token", token);
        localStorage.setItem("nexus_user", JSON.stringify(user));
        this.updateHeaderProfile();
    },

    clearAuth: function() {
        this.token = null;
        this.user = null;
        localStorage.removeItem("nexus_token");
        localStorage.removeItem("nexus_user");
        fetch("/api/logout", { method: "POST" });
        window.location.href = "/login";
    },

    getHeaders: function() {
        const headers = { "Content-Type": "application/json" };
        if (this.token) {
            headers["Authorization"] = `Bearer ${this.token}`;
        }
        return headers;
    },

    updateHeaderProfile: function() {
        const elName = document.getElementById("navUserName");
        const elAvatar = document.getElementById("navUserAvatar");
        if (this.user && elName) {
            elName.textContent = this.user.name || "Operations Lead";
            if (elAvatar) {
                elAvatar.textContent = (this.user.name || "N").charAt(0).toUpperCase();
            }
        }
    },

    showToast: function(title, message, type = "info") {
        const toastContainer = document.getElementById("toastContainer");
        if (!toastContainer) return;

        const id = "toast_" + Date.now();
        const bgClass = type === "success" ? "bg-success text-white" : (type === "danger" ? "bg-danger text-white" : "bg-dark text-white");
        
        const toastHtml = `
            <div id="${id}" class="toast align-items-center ${bgClass} border-0 show mb-2 shadow" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        <strong>${title}</strong><br/>${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        toastContainer.insertAdjacentHTML("beforeend", toastHtml);
        setTimeout(() => {
            const t = document.getElementById(id);
            if (t) t.remove();
        }, 5000);
    },

    updateAlertBadge: async function() {
        try {
            const resp = await fetch("/api/alerts?unread_only=true");
            if (resp.ok) {
                const alerts = await resp.json();
                const badge = document.getElementById("sidebarAlertBadge");
                if (badge) {
                    if (alerts.length > 0) {
                        badge.textContent = alerts.length;
                        badge.classList.remove("d-none");
                    } else {
                        badge.classList.add("d-none");
                    }
                }
            }
        } catch (e) {
            // silent fail
        }
    }
};

document.addEventListener("DOMContentLoaded", () => {
    NexusApp.updateHeaderProfile();
    NexusApp.updateAlertBadge();
});
