window.NotifyHub = window.NotifyHub || {};

NotifyHub.initNotifyBadge();

if (document.body && document.body.hasAttribute("data-app-shell")) {
    NotifyHub.connectNotificationsWS();
    NotifyHub.initNotificationFeedWatcher();
}
NotifyHub.bootstrapDjangoMessages();
NotifyHub.initProfileMenu();
NotifyHub.initNotificationActions();
NotifyHub.initPreferenceToggles();
NotifyHub.initDndControls();
NotifyHub.initNotificationsToolbar();
NotifyHub.initNotifSearchSlashFocus();

window.addEventListener("keydown", NotifyHub.unlockAudio, { once: true });
window.addEventListener("pointerdown", NotifyHub.unlockAudio, { once: true });
