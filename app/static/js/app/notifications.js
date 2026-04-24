window.NotifyHub = window.NotifyHub || {};

const TOAST_DURATION_MS = 5000;
let audioCtx = null;
let audioUnlocked = false;

NotifyHub.messageTagsToLevel = function messageTagsToLevel(tags) {
    const t = String(tags || "").toLowerCase();
    if (t.includes("error")) return "error";
    if (t.includes("warning")) return "warning";
    if (t.includes("success")) return "success";
    return "info";
};

NotifyHub.levelMeta = function levelMeta(level) {
    const lv = level || "info";
    const map = {
        success: {
            label: "Успех",
            badgeClass:
                "inline-flex items-center rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 dark:text-emerald-200",
            iconSvg:
                '<svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8.5"/><path d="m8.7 12.1 2.2 2.2 4.4-4.4"/></svg>',
        },
        error: {
            label: "Ошибка",
            badgeClass:
                "inline-flex items-center rounded-full bg-rose-500/15 px-2.5 py-0.5 text-xs font-semibold text-rose-800 dark:text-rose-200",
            iconSvg:
                '<svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8.5"/><path d="m9.2 9.2 5.6 5.6M14.8 9.2l-5.6 5.6"/></svg>',
        },
        warning: {
            label: "Важно",
            badgeClass:
                "inline-flex items-center rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs font-semibold text-amber-900 dark:text-amber-200",
            iconSvg:
                '<svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.4 4 2.1 18.2A1.3 1.3 0 0 0 3.2 20h17.6a1.3 1.3 0 0 0 1.1-1.8L13.6 4a1.8 1.8 0 0 0-3.2 0Z"/><path d="M12 9.3v4.7M12 16.8h.01"/></svg>',
        },
        debug: {
            label: "Система",
            badgeClass:
                "inline-flex items-center rounded-full bg-zinc-500/15 px-2.5 py-0.5 text-xs font-semibold text-zinc-700 dark:text-zinc-300",
            iconSvg:
                '<svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M4 12h10M4 17h16"/></svg>',
        },
        info: {
            label: "Инфо",
            badgeClass:
                "inline-flex items-center rounded-full bg-sky-500/15 px-2.5 py-0.5 text-xs font-semibold text-sky-800 dark:text-sky-200",
            iconSvg:
                '<svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8.5"/><path d="M12 10.1v4.4M12 7.6h.01"/></svg>',
        },
    };

    return map[lv] || map.info;
};

NotifyHub.kindMeta = function kindMeta(kind) {
    const map = {
        payment: {
            label: "Платежи",
            iconSvg:
                '<svg class="h-3.5 w-3.5 shrink-0" viewBox="0 0 16 16" fill="none" aria-hidden="true" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="10.5" cy="4.3" rx="3.1" ry="1.2"/><path d="M7.4 4.3v2.2c0 .7 1.4 1.2 3.1 1.2s3.1-.5 3.1-1.2V4.3"/><ellipse cx="5.2" cy="7.8" rx="2.2" ry="1"/><path d="M3 7.8v1.8c0 .5 1 1 2.2 1s2.2-.5 2.2-1V7.8"/></svg>',
        },
        message: {
            label: "Сообщения",
            iconSvg:
                '<svg class="h-3.5 w-3.5 shrink-0" viewBox="0 0 16 16" fill="none" aria-hidden="true" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3.2 3.4h9.6c.8 0 1.4.6 1.4 1.4v5.1c0 .8-.6 1.4-1.4 1.4H7l-3.2 2V4.8c0-.8.6-1.4 1.4-1.4Z"/><path d="M5.8 6.4h4.5M5.8 8.6h2.9"/></svg>',
        },
        system: {
            label: "Системное",
            iconSvg:
                '<svg class="h-3.5 w-3.5 shrink-0" viewBox="0 0 16 16" fill="none" aria-hidden="true" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6.2"/><path d="M8 5.4v3.2M8 10.9h.01"/></svg>',
        },
        marketing: {
            label: "Маркетинг",
            iconSvg:
                '<svg class="h-3.5 w-3.5 shrink-0" viewBox="0 0 16 16" fill="none" aria-hidden="true" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m2.4 8 7.3-3.3v6.6L2.4 8Z"/><path d="M9.7 6h1.7a1.7 1.7 0 0 1 0 3.4H9.7M4.3 9l.8 2.2a.7.7 0 0 0 .66.48h1.3"/></svg>',
        },
        security: {
            label: "Безопасность",
            iconSvg:
                '<svg class="h-3.5 w-3.5 shrink-0" viewBox="0 0 16 16" fill="none" aria-hidden="true" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2.3 3.3 4.4v3.7c0 2.8 2 5.2 4.7 5.9 2.7-.7 4.7-3.1 4.7-5.9V4.4L8 2.3Z"/><path d="m5.9 8 1.4 1.4L10.2 6.5"/></svg>',
        },
        support: {
            label: "Поддержка",
            iconSvg:
                '<svg class="h-3.5 w-3.5 shrink-0" viewBox="0 0 16 16" fill="none" aria-hidden="true" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4.4 7a3.6 3.6 0 1 1 7.2 0v1.4c0 1-.8 1.8-1.8 1.8h-.6a.9.9 0 0 1-.9-.9v-.7a.9.9 0 0 1 .9-.9h2.4M4.4 7.6h1.9a.9.9 0 0 1 .9.9v.7a.9.9 0 0 1-.9.9H4.4M8 12.7h1.4"/></svg>',
        },
    };

    return map[kind] || map.system;
};

NotifyHub.iconSvgForNotification = function iconSvgForNotification(level, kind) {
    const kindIcons = {
        payment:
            '<svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="15.5" cy="6.2" rx="5.4" ry="2.2"/><path d="M10.1 6.2v3.4c0 1.2 2.4 2.2 5.4 2.2s5.4-1 5.4-2.2V6.2"/><path d="M10.1 10.6V14c0 1.2 2.4 2.2 5.4 2.2s5.4-1 5.4-2.2v-3.4"/><ellipse cx="7.2" cy="11.4" rx="3.8" ry="1.7"/><path d="M3.4 11.4v2.8c0 .9 1.7 1.7 3.8 1.7S11 15.1 11 14.2v-2.8"/></svg>',
        security:
            '<svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3.5 5 6.6v5.5c0 4.3 2.9 7.8 7 8.9 4.1-1.1 7-4.6 7-8.9V6.6L12 3.5Z"/><path d="M9.2 12.2 11 14l3.8-3.8"/></svg>',
        message:
            '<svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 6.5h14A1.5 1.5 0 0 1 20.5 8v8A1.5 1.5 0 0 1 19 17.5H9l-4 3v-4H5A1.5 1.5 0 0 1 3.5 15V8A1.5 1.5 0 0 1 5 6.5Z"/><path d="M8 10h8M8 13h5"/></svg>',
        support:
            '<svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6.5 10.5a5.5 5.5 0 1 1 11 0v2.1a2.4 2.4 0 0 1-2.4 2.4h-.8a1.3 1.3 0 0 1-1.3-1.3v-1a1.3 1.3 0 0 1 1.3-1.3h3.2M6.5 11.4H9a1.3 1.3 0 0 1 1.3 1.3v1A1.3 1.3 0 0 1 9 15H6.5M12 19h2.2"/></svg>',
        marketing:
            '<svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m4 12 11-5v10L4 12Z"/><path d="M15 9h2.5a2.5 2.5 0 0 1 0 5H15M7 13.6l1.1 3.1a1 1 0 0 0 .95.66H11"/></svg>',
    };
    if (kindIcons[kind]) return kindIcons[kind];

    return NotifyHub.levelMeta(level).iconSvg;
};

NotifyHub.formatNotificationDate = function formatNotificationDate(notificationDate) {
    if (!notificationDate) return "";
    const dt = new Date(notificationDate);
    if (Number.isNaN(dt.getTime())) return "";
    return new Intl.DateTimeFormat("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    }).format(dt);
};

NotifyHub.initNotifyBadge = function initNotifyBadge() {
    const el = document.getElementById("header-notify-badge");
    if (!el) {
        window.__notifyhubBadgeCount = 0;
        return;
    }
    const initial = parseInt(el.dataset.initialCount || el.textContent || "0", 10);
    window.__notifyhubBadgeCount = Number.isFinite(initial) ? initial : 0;
};

NotifyHub.bumpNotifyBadge = function bumpNotifyBadge(delta) {
    const el = document.getElementById("header-notify-badge");
    if (!el) return;
    window.__notifyhubBadgeCount = Math.max(
        0,
        (window.__notifyhubBadgeCount || 0) + delta
    );
    const n = window.__notifyhubBadgeCount;
    el.textContent = n > 99 ? "99+" : String(n);
    el.classList.toggle("hidden", n <= 0);
    if (delta > 0) {
        const bellLink = document.getElementById("header-notify-link");
        if (bellLink) {
            bellLink.classList.remove("is-ringing");
            void bellLink.offsetWidth;
            bellLink.classList.add("is-ringing");
            window.setTimeout(() => {
                bellLink.classList.remove("is-ringing");
            }, 700);
        }
    }
};

NotifyHub.showToast = function showToast(notification, toastOpts = {}) {
    const skipBadge = toastOpts.skipBadge === true;
    const stack = document.getElementById("toast-stack");
    if (!stack) return;

    const level = notification.level || "info";
    const kind = notification.kind || "system";
    const meta = NotifyHub.levelMeta(level);
    const kindInfo = NotifyHub.kindMeta(kind);

    const item = document.createElement("div");
    item.className = `toast level-${level}`;
    item.setAttribute("role", "status");

    const inner = document.createElement("div");
    inner.className = "toast-inner";

    const row = document.createElement("div");
    row.className = "nh-toast-row";

    const iconWrap = document.createElement("div");
    iconWrap.className = "nh-toast-icon";
    iconWrap.setAttribute("aria-hidden", "true");
    iconWrap.innerHTML = NotifyHub.iconSvgForNotification(level, kind);
    const toastSvg = iconWrap.querySelector("svg");
    if (toastSvg) toastSvg.setAttribute("class", "h-6 w-6");

    const textCol = document.createElement("div");
    textCol.className = "nh-toast-text";

    const badge = document.createElement("span");
    badge.className = meta.badgeClass;
    badge.textContent = meta.label;

    const kindBadge = document.createElement("span");
    kindBadge.className =
        "inline-flex max-w-full items-center gap-1 rounded-full border border-zinc-200 px-2.5 py-0.5 text-xs font-medium text-zinc-600 dark:border-white/15 dark:text-zinc-300";
    kindBadge.innerHTML = `${kindInfo.iconSvg}<span class="truncate">${kindInfo.label}</span>`;

    const head = document.createElement("div");
    head.className = "nh-toast-head";
    const metaRow = document.createElement("div");
    metaRow.className = "nh-toast-meta";
    metaRow.append(badge, kindBadge);

    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "nh-toast-close";
    closeBtn.setAttribute("aria-label", "Закрыть уведомление");
    closeBtn.innerHTML =
        '<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M5 5l10 10M15 5 5 15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>';

    const topRow = document.createElement("div");
    topRow.className = "nh-toast-top";
    topRow.append(metaRow, closeBtn);

    const titleEl = document.createElement("strong");
    titleEl.className = "nh-toast-title";
    titleEl.textContent = notification.title || "Сообщение";
    head.append(topRow, titleEl);

    const msg = document.createElement("p");
    msg.className = "nh-toast-msg";
    msg.textContent = notification.message || "";

    textCol.append(head, msg);
    row.append(iconWrap, textCol);
    inner.append(row);

    if (!skipBadge) {
        NotifyHub.bumpNotifyBadge(1);
    }

    const track = document.createElement("div");
    track.className = "toast-progress-track";
    const bar = document.createElement("div");
    bar.className = "toast-progress-bar";
    bar.style.animationDuration = `${TOAST_DURATION_MS}ms`;

    item.append(inner, track);
    track.append(bar);
    stack.prepend(item);

    const removeToast = () => {
        item.classList.add("toast-exiting");
        const done = () => {
            item.removeEventListener("transitionend", done);
            item.remove();
        };
        item.addEventListener("transitionend", done);
        window.setTimeout(() => {
            if (item.isConnected) item.remove();
        }, 400);
    };

    closeBtn.addEventListener("click", removeToast);
    bar.addEventListener("animationend", removeToast, { once: true });
};

NotifyHub.createNotificationNode = function createNotificationNode(
    notification,
    withAction = false
) {
    const level = notification.level || "info";
    const kind = notification.kind || "system";
    const meta = NotifyHub.levelMeta(level);
    const kindInfo = NotifyHub.kindMeta(kind);
    const iconToneByLevel = {
        success:
            "border-emerald-200/70 bg-emerald-50/90 text-emerald-600 dark:border-emerald-500/25 dark:bg-emerald-500/10 dark:text-emerald-300",
        error:
            "border-rose-200/70 bg-rose-50/90 text-rose-600 dark:border-rose-500/25 dark:bg-rose-500/10 dark:text-rose-300",
        warning:
            "border-amber-200/80 bg-amber-50/90 text-amber-600 dark:border-amber-500/25 dark:bg-amber-500/10 dark:text-amber-300",
        debug:
            "border-zinc-200/80 bg-zinc-100 text-zinc-600 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
        info:
            "border-sky-200/70 bg-sky-50/90 text-sky-600 dark:border-sky-500/25 dark:bg-sky-500/10 dark:text-sky-300",
    };

    const item = document.createElement("div");
    item.className = `notification-item notif-card level-${level}`;
    item.dataset.id = String(notification.id || "");
    item.dataset.read = String(Boolean(notification.is_read));
    item.dataset.kind = String(notification.kind || "system");

    const glow = document.createElement("span");
    glow.className = "nh-notif-glow";
    glow.setAttribute("aria-hidden", "true");

    const shell = document.createElement("div");
    shell.className = "nh-notif-shell";

    const left = document.createElement("div");
    left.className = "nh-notif-left";

    const iconWrap = document.createElement("div");
    iconWrap.className = `nh-notif-icon ${iconToneByLevel[level] || iconToneByLevel.info}`;
    iconWrap.setAttribute("aria-hidden", "true");
    iconWrap.innerHTML = NotifyHub.iconSvgForNotification(level, kind);

    const body = document.createElement("div");
    body.className = "nh-notif-body";

    const badgeRow = document.createElement("div");
    badgeRow.className = "nh-notif-badge-row";
    const badge = document.createElement("span");
    badge.className = meta.badgeClass;
    badge.textContent = meta.label;
    const kindBadge = document.createElement("span");
    kindBadge.className =
        "inline-flex max-w-full items-center gap-1 rounded-full border border-zinc-200 px-2.5 py-0.5 text-xs font-medium text-zinc-600 dark:border-white/15 dark:text-zinc-300";
    kindBadge.innerHTML = `${kindInfo.iconSvg}<span class="truncate">${kindInfo.label}</span>`;
    badgeRow.append(badge, kindBadge);

    const title = document.createElement("strong");
    title.className = "nh-notif-title";
    title.textContent = notification.title || "";

    const message = document.createElement("p");
    message.className = "nh-notif-msg";
    message.textContent = notification.message || "";

    const notificationDate =
        notification.notification_date || notification.created_at || "";
    const dateText = NotifyHub.formatNotificationDate(notificationDate);
    if (dateText) {
        const date = document.createElement("time");
        date.className = "mt-2 block text-xs text-zinc-500 dark:text-zinc-400";
        date.dateTime = notificationDate;
        date.textContent = dateText;
        body.append(badgeRow, title, message, date);
    } else {
        body.append(badgeRow, title, message);
    }
    left.append(iconWrap, body);
    shell.append(left);

    if (withAction && !notification.is_read) {
        const nid = Number(notification.id);
        const serverId = Number.isFinite(nid) && nid > 0;
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className =
            "btn btn-outline btn-small mark-read-btn notif-read shrink-0 self-start sm:self-center";
        if (serverId) btn.dataset.id = String(notification.id);
        btn.textContent = "Прочитано";
        btn.addEventListener("click", async (event) => {
            const button = event.currentTarget;
            const notificationItem = event.currentTarget.closest(".notification-item");
            if (serverId) {
                button.disabled = true;
                const response = await NotifyHub.postJSON(
                    `/api/notifications/${event.currentTarget.dataset.id}/read/`
                );
                if (!response.ok) {
                    button.disabled = false;
                    return;
                }
            }
            if (notificationItem && notificationItem.dataset.read !== "true") {
                notificationItem.dataset.read = "true";
                NotifyHub.bumpNotifyBadge(-1);
            }
            button.remove();
            window.dispatchEvent(new Event("notifyhub:notifications-updated"));
        });
        shell.append(btn);
    }

    item.append(glow, shell);

    return item;
};

NotifyHub.removeEmptyPlaceholder = function removeEmptyPlaceholder(container) {
    const empty = container.querySelector(".empty");
    if (empty) empty.remove();
};

NotifyHub.prependNotificationToLists = function prependNotificationToLists(notification) {
    const fullList = document.getElementById("notification-list");
    if (fullList) {
        NotifyHub.removeEmptyPlaceholder(fullList);
        fullList.prepend(NotifyHub.createNotificationNode(notification, true));
    }

    const latestList = document.getElementById("latest-notification-list");
    if (latestList) {
        NotifyHub.removeEmptyPlaceholder(latestList);
        latestList.prepend(NotifyHub.createNotificationNode(notification, false));
        while (latestList.querySelectorAll(".notification-item").length > 5) {
            latestList.lastElementChild.remove();
        }
    }
};

NotifyHub.consumeIncomingNotification = function consumeIncomingNotification(
    notification,
    opts = {}
) {
    const src = opts.source || "ws";

    if (!(window.__notifyhubSeenIds instanceof Set)) {
        window.__notifyhubSeenIds = new Set();
    }

    const id = Number(notification.id);
    const sid =
        notification.id != null && notification.id !== ""
            ? String(notification.id)
            : "";

    if (Number.isFinite(id)) {
        window.__notifyhubLastId = Math.max(window.__notifyhubLastId || 0, id);
        if (window.__notifyhubSeenIds.has(id)) return;
        window.__notifyhubSeenIds.add(id);
    } else if (sid) {
        if (window.__notifyhubSeenIds.has(sid)) return;
        window.__notifyhubSeenIds.add(sid);
    }

    if (src !== "local") {
        NotifyHub.showToast(notification, { skipBadge: true });
        if (src === "ws") NotifyHub.playNotificationSound();
    }

    NotifyHub.prependNotificationToLists(notification);

    if (notification.is_read !== true) {
        NotifyHub.bumpNotifyBadge(1);
    }

    if (Number.isFinite(id)) {
        try {
            localStorage.setItem(
                "notifyhubFeedCursor",
                String(window.__notifyhubLastId || 0)
            );
        } catch {
            // ignore
        }
    }
    window.dispatchEvent(new Event("notifyhub:notifications-updated"));
};

NotifyHub.unlockAudio = function unlockAudio() {
    if (audioUnlocked) return;
    try {
        audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        gain.gain.value = 0.0001;
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.01);
        audioUnlocked = true;
    } catch {
        audioUnlocked = false;
    }
};

NotifyHub.playNotificationSound = function playNotificationSound() {
    if (!audioUnlocked) return;
    if (!audioCtx) return;
    if (localStorage.getItem("sound") === "off") return;

    const t0 = audioCtx.currentTime;
    const gain = audioCtx.createGain();
    gain.gain.setValueAtTime(0.0001, t0);
    gain.connect(audioCtx.destination);

    const osc1 = audioCtx.createOscillator();
    osc1.type = "sine";
    osc1.frequency.setValueAtTime(880, t0);
    osc1.connect(gain);
    osc1.start(t0);
    gain.gain.exponentialRampToValueAtTime(0.12, t0 + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.10);
    osc1.stop(t0 + 0.11);

    const osc2 = audioCtx.createOscillator();
    osc2.type = "sine";
    osc2.frequency.setValueAtTime(1320, t0 + 0.12);
    osc2.connect(gain);
    osc2.start(t0 + 0.12);
    gain.gain.exponentialRampToValueAtTime(0.08, t0 + 0.13);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.20);
    osc2.stop(t0 + 0.21);
};

NotifyHub.connectNotificationsWS = function connectNotificationsWS() {
    if (window.__notifyhubWsDisabled === true) return;
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    let opened = false;
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws/notifications/`);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        NotifyHub.consumeIncomingNotification(data, { source: "ws" });
    };

    ws.onopen = () => {
        opened = true;
        window.__notifyhubWsFailures = 0;
        console.debug("[NotifyHub] WS connected");
    };

    ws.onerror = (e) => {
        console.error("[NotifyHub] WS error", e);
    };

    ws.onclose = () => {
        if (!opened) {
            window.__notifyhubWsFailures = (window.__notifyhubWsFailures || 0) + 1;
            if (window.__notifyhubWsFailures >= 3) {
                window.__notifyhubWsDisabled = true;
                console.warn(
                    "[NotifyHub] WS endpoint unavailable. Fallback to polling only."
                );
                return;
            }
        }
        console.warn("[NotifyHub] WS closed. Reconnecting...");
        setTimeout(NotifyHub.connectNotificationsWS, 3000);
    };
};

NotifyHub.fetchNotificationFeed = async function fetchNotificationFeed() {
    const afterId = window.__notifyhubLastId || 0;
    const response = await fetch(`/api/notifications/feed/?after_id=${afterId}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    if (!response.ok) return;
    const payload = await response.json();
    const items = Array.isArray(payload.items)
        ? payload.items
        : payload.data && Array.isArray(payload.data.items)
          ? payload.data.items
          : null;
    const ok = payload.status === "success" || payload.ok === true;
    if (!payload || !ok || !items) return;
    items.forEach((item) => {
        NotifyHub.consumeIncomingNotification(item, { source: "poll" });
    });
};

NotifyHub.initNotificationFeedWatcher = function initNotificationFeedWatcher() {
    const ids = Array.from(document.querySelectorAll(".notification-item[data-id]"))
        .map((el) => Number(el.dataset.id))
        .filter((n) => Number.isFinite(n));
    const domMax = ids.length ? Math.max(...ids) : 0;
    const server = Number((document.body && document.body.dataset.feedCursor) || 0);
    let stored = 0;
    try {
        stored = Number(localStorage.getItem("notifyhubFeedCursor") || 0);
    } catch {
        stored = 0;
    }
    const trustedServerCursor = Math.max(domMax, server);
    const safeStored =
        Number.isFinite(stored) && stored > 0 && stored <= trustedServerCursor
            ? stored
            : 0;
    window.__notifyhubLastId = Math.max(trustedServerCursor, safeStored);
    window.__notifyhubSeenIds = new Set(ids);

    NotifyHub.fetchNotificationFeed();
    setInterval(NotifyHub.fetchNotificationFeed, 5000);
};
