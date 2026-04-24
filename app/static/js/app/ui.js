window.NotifyHub = window.NotifyHub || {};

NotifyHub.applyTheme = function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
};

NotifyHub.initProfileMenu = function initProfileMenu() {
    const btn = document.getElementById("profile-btn");
    const menu = document.getElementById("profile-menu");
    if (!btn || !menu) return;

    btn.addEventListener("click", () => {
        const isHidden = menu.hasAttribute("hidden");
        if (isHidden) menu.removeAttribute("hidden");
        else menu.setAttribute("hidden", "hidden");
    });

    document.addEventListener("click", (e) => {
        if (e.target === btn || menu.contains(e.target)) return;
        menu.setAttribute("hidden", "hidden");
    });

    const saved = localStorage.getItem("theme") || "dark";
    NotifyHub.applyTheme(saved);
    const themeToggle = document.getElementById("theme-toggle");
    if (themeToggle) {
        const isDark = saved === "dark";
        themeToggle.classList.toggle("on", isDark);
        themeToggle.dataset.on = String(isDark);
        themeToggle.addEventListener("click", () => {
            const next =
                (localStorage.getItem("theme") || "dark") === "dark"
                    ? "light"
                    : "dark";
            NotifyHub.applyTheme(next);
            const nextIsDark = next === "dark";
            themeToggle.classList.toggle("on", nextIsDark);
            themeToggle.dataset.on = String(nextIsDark);
        });
    }
};

NotifyHub.initNotificationActions = function initNotificationActions() {
    const markAllBtn = document.getElementById("mark-all-btn");
    if (markAllBtn) {
        markAllBtn.addEventListener("click", async () => {
            const unread = document.querySelectorAll(
                '.notification-item[data-read="false"]'
            ).length;
            await NotifyHub.postJSON("/api/notifications/read-all/");
            document.querySelectorAll(".notification-item").forEach((item) => {
                item.dataset.read = "true";
            });
            document.querySelectorAll(".mark-read-btn").forEach((btn) => btn.remove());
            NotifyHub.bumpNotifyBadge(-unread);
            window.dispatchEvent(new Event("notifyhub:notifications-updated"));
        });
    }

    document.querySelectorAll(".mark-read-btn").forEach((btn) => {
        btn.addEventListener("click", async (event) => {
            const button = event.currentTarget;
            const item = button.closest(".notification-item");
            const id = button.dataset.id || (item ? item.dataset.id : "");
            if (!id) return;
            button.disabled = true;
            const response = await NotifyHub.postJSON(`/api/notifications/${id}/read/`);
            if (!response.ok) {
                button.disabled = false;
                return;
            }
            if (item && item.dataset.read !== "true") {
                item.dataset.read = "true";
                NotifyHub.bumpNotifyBadge(-1);
            }
            button.remove();
            window.dispatchEvent(new Event("notifyhub:notifications-updated"));
        });
    });
};

NotifyHub.initPreferenceToggles = function initPreferenceToggles() {
    document.querySelectorAll(".switch[data-pref]").forEach((toggle) => {
        toggle.addEventListener("click", async (event) => {
            const el = event.currentTarget;
            const nextValue = !(el.dataset.on === "true");
            const response = await NotifyHub.postForm("/api/preferences/toggle/", {
                key: el.dataset.pref,
                value: String(nextValue),
            });
            if (!response.ok) return;
            el.dataset.on = String(nextValue);
            el.classList.toggle("on", nextValue);
            NotifyHub.consumeIncomingNotification(
                {
                    id: `pref-${Date.now()}`,
                    title: "Настройки обновлены",
                    message: "Параметр уведомлений успешно сохранён.",
                    level: "success",
                    is_read: true,
                },
                { source: "local" }
            );
        });
    });
};

NotifyHub.initDndControls = function initDndControls() {
    const start = document.getElementById("dnd-start");
    const end = document.getElementById("dnd-end");
    if (!start || !end) return;

    const save = async () => {
        const resp = await NotifyHub.postForm("/api/preferences/dnd/", {
            dnd_start: start.value,
            dnd_end: end.value,
        });
        if (!resp.ok) return;
        NotifyHub.consumeIncomingNotification(
            {
                id: `dnd-${Date.now()}`,
                title: "Сохранено",
                message: "Время DND обновлено.",
                level: "success",
                is_read: true,
            },
            { source: "local" }
        );
    };
    start.addEventListener("change", save);
    end.addEventListener("change", save);
};

NotifyHub.initNotificationsToolbar = function initNotificationsToolbar() {
    const search = document.getElementById("notif-search");
    const list = document.getElementById("notification-list");
    if (!search || !list) return;

    let filter = "all";
    const apply = () => {
        const q = (search.value || "").trim().toLowerCase();
        list.querySelectorAll(".notification-item").forEach((item) => {
            const text = item.innerText.toLowerCase();
            const isRead = item.dataset.read === "true";
            const matchesFilter = filter === "all" ? true : !isRead;
            const matchesQuery = !q || text.includes(q);
            item.style.display = matchesFilter && matchesQuery ? "" : "none";
        });
    };

    search.addEventListener("input", apply);
    document.querySelectorAll(".segmented-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            document
                .querySelectorAll(".segmented-btn")
                .forEach((b) => b.classList.remove("is-active"));
            btn.classList.add("is-active");
            filter = btn.dataset.filter;
            apply();
        });
    });

    window.addEventListener("notifyhub:notifications-updated", apply);
};

NotifyHub.initNotifSearchSlashFocus = function initNotifSearchSlashFocus() {
    const inp = document.getElementById("notif-search");
    if (!inp) return;

    document.addEventListener("keydown", (e) => {
        if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return;
        const el = e.target;
        if (
            el instanceof HTMLInputElement ||
            el instanceof HTMLTextAreaElement ||
            el instanceof HTMLSelectElement
        ) {
            return;
        }
        if (el instanceof HTMLElement && el.isContentEditable) return;
        if (document.activeElement === inp) return;
        e.preventDefault();
        inp.focus();
    });
};

NotifyHub.bootstrapDjangoMessages = function bootstrapDjangoMessages() {
    const el = document.getElementById("django-messages-data");
    if (!el) return;
    let items = [];
    try {
        items = JSON.parse(el.textContent || "[]");
    } catch {
        items = [];
    }
    el.remove();
    if (!items.length) return;
    const titleForLevel = (level) => {
        if (level === "error") return "Нужно внимание";
        if (level === "warning") return "На заметку";
        if (level === "success") return "Готово";
        return "Сообщение";
    };
    items.forEach((row, i) => {
        const level = NotifyHub.messageTagsToLevel(row.tags);
        NotifyHub.consumeIncomingNotification(
            {
                id: `django-${Date.now()}-${i}`,
                title: titleForLevel(level),
                message: row.body || "",
                level,
                is_read: true,
            },
            { source: "local" }
        );
    });
};
