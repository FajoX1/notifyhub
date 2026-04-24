window.NotifyHub = window.NotifyHub || {};

NotifyHub.getCookie = function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
        return parts.pop().split(";").shift();
    }
    return "";
};

NotifyHub.postJSON = async function postJSON(url) {
    return fetch(url, {
        method: "POST",
        headers: {
            "X-CSRFToken": NotifyHub.getCookie("csrftoken"),
            "X-Requested-With": "XMLHttpRequest",
        },
    });
};

NotifyHub.postForm = async function postForm(url, body) {
    return fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "X-CSRFToken": NotifyHub.getCookie("csrftoken"),
            "X-Requested-With": "XMLHttpRequest",
        },
        body: new URLSearchParams(body),
    });
};
