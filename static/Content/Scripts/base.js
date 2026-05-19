let idleTimer = null;
let isUploading = false;

const IDLE_LIMIT = 30 * 60 * 1000;

function resetIdleTimer() {
    clearTimeout(idleTimer);

    idleTimer = setTimeout(() => {
        if (isUploading) {
            resetIdleTimer();
            return;
        }

        alert("您已超過 30 分鐘未操作，系統將自動登出");
        window.location.href = "/logout";
    }, IDLE_LIMIT);
}

["click", "keydown", "scroll", "touchstart"].forEach(eventName => {
    document.addEventListener(eventName, resetIdleTimer, true);
});

resetIdleTimer();

let isCheckingSession = false;

async function checkSessionFromServer() {
    if (isCheckingSession) return true;

    isCheckingSession = true;

    try {
        const res = await fetch("/api/check-session", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            }
        });

        const result = await res.json();

        if (!res.ok || result.expired) {
            alert(result.message || "登入已逾時，請重新登入");
            window.location.href = "/logout";
            return false;
        }

        return true;

    } catch (err) {
        console.error("檢查登入狀態失敗", err);
        return true; // 網路瞬斷時不要直接登出
    } finally {
        isCheckingSession = false;
    }
}

document.addEventListener("click", async function (event) {
    const ok = await checkSessionFromServer();

    if (!ok) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
    }
}, true);
document.addEventListener("click", function(e) {
    const btn = e.target.closest(".tw-collapse-toggle");
    if (!btn) return;

    const target = document.querySelector(btn.dataset.target);
    if (!target) return;

    target.classList.toggle("hidden");
});

document.querySelectorAll('.btn-back').forEach(btn => {
    btn.addEventListener('click', function () {
        history.back();
    });
});

const userMenu = document.getElementById("userMenu");
const userAvatar = document.getElementById("userAvatar");

if (userAvatar && userMenu) {
    userAvatar.addEventListener("click", function (e) {
        e.stopPropagation();
        userMenu.classList.toggle("active");
    });

    document.addEventListener("click", function () {
        userMenu.classList.remove("active");
    });
}

document.addEventListener("DOMContentLoaded", function () {
    const projectSelect = document.getElementById("projectSelect");

    if (projectSelect) {
        projectSelect.addEventListener("change", function () {
            const selectedOption = this.options[this.selectedIndex];
            const url = selectedOption.getAttribute("data-url");

            if (url) {
                window.location.href = url;
            }
        });
    }
});