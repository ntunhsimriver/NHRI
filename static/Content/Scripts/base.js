let idleTimer = null;
let isUploading = false;
let isCheckingSession = false;

const IDLE_LIMIT = 30 * 60 * 1000;

function resetIdleTimer() {
    clearTimeout(idleTimer);

    idleTimer = setTimeout(() => {
        if (isUploading) {
            resetIdleTimer();
            return;
        }

        alert("您已超過 30 分鐘未操作，系統將自動登出");
        const reason = result.reason || "invalid";
        window.location.href = `/logout?reason=${encodeURIComponent(reason)}`;
    }, IDLE_LIMIT);
}

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

        const contentType = res.headers.get("content-type") || "";

        if (!contentType.includes("application/json")) {
            alert("登入狀態已失效，請重新登入");
            window.location.href = "/logout?reason=invalid";
            return false;
        }

        const result = await res.json();

        if (!res.ok || result.expired) {
            alert(result.message || "登入已逾時，請重新登入");

            const reason = result.reason || "invalid";
            window.location.href = `/logout?reason=${encodeURIComponent(reason)}`;

            return false;
        }

        return true;

    } catch (err) {
        console.error("檢查登入狀態失敗", err);
        alert("登入狀態檢查失敗，請重新登入");
        window.location.href = "/logout?reason=invalid";
        return false;
    } finally {
        isCheckingSession = false;
    }
}

["click"].forEach(eventName => {
    document.addEventListener(eventName, resetIdleTimer, true);
});

document.addEventListener("click", async function (event) {
    const linkOrButton = event.target.closest("a, .project-btn, [data-url]");

    if (!linkOrButton) return;

    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();

    const ok = await checkSessionFromServer();

    if (!ok) return;

    resetIdleTimer();

    if (linkOrButton.tagName === "A" && linkOrButton.href) {
        window.location.href = linkOrButton.href;
        return;
    }

    const url = linkOrButton.dataset.url;
    if (url) {
        window.location.href = url;
        return;
    }
}, true);

resetIdleTimer();

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

  userAvatar.addEventListener("click", function (e) {
    e.stopPropagation();
    userMenu.classList.toggle("active");
  });

  document.addEventListener("click", function () {
    userMenu.classList.remove("active");
  });

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