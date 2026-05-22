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
        window.location.href = "/logout";
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
            window.location.href = "/logout";
            return false;
        }

        const result = await res.json();

        if (!res.ok || result.expired) {
            alert(result.message || "登入已逾時，請重新登入");
            window.location.href = "/logout";
            return false;
        }

        return true;

    } catch (err) {
        console.error("檢查登入狀態失敗", err);
        return true;
    } finally {
        isCheckingSession = false;
    }
}

["click", "keydown", "scroll", "touchstart"].forEach(eventName => {
    document.addEventListener(eventName, resetIdleTimer, true);
});

document.addEventListener("click", async function (event) {
    const ok = await checkSessionFromServer();

    if (!ok) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
    }
}, true);

resetIdleTimer();


document.addEventListener("DOMContentLoaded", function () {
    if (window.layoutHelpers) {
        window.layoutHelpers.init();
    }

    document.querySelectorAll(".layout-sidenav-toggle").forEach(function (el) {
        el.addEventListener("click", function () {
            if (window.layoutHelpers && typeof window.layoutHelpers.toggleCollapsed === "function") {
                window.layoutHelpers.toggleCollapsed();
            }
        });
    });

    document.querySelectorAll(".project-btn").forEach(btn => {
        btn.addEventListener("click", function () {
            window.location.href = this.dataset.url;
        });
    });

    const userMenu = document.getElementById("userMenu");
    const userAvatar = document.getElementById("userAvatar");

    if (userMenu && userAvatar) {
        userAvatar.addEventListener("click", function (e) {
            e.stopPropagation();
            userMenu.classList.toggle("active");
        });

        document.addEventListener("click", function () {
            userMenu.classList.remove("active");
        });
    }

    const searchInput = document.getElementById("searchInput");
    const caseRows = document.querySelectorAll(".case-row");

    if (searchInput) {
        searchInput.addEventListener("input", function () {
            const searchText = searchInput.value.toLowerCase().trim();

            caseRows.forEach(row => {
                const proid = (row.getAttribute("data-proid") || "").toLowerCase();
                const proname = (row.getAttribute("data-name") || "").toLowerCase();

                const matchSearch =
                    proid.includes(searchText) ||
                    proname.includes(searchText);

                row.style.display = matchSearch ? "" : "none";
            });
        });
    }
});


document.addEventListener("click", function (event) {
    const btn = event.target.closest(".toggle-password");

    if (!btn) return;

    const targetId = btn.getAttribute("data-target");
    const input = document.getElementById(targetId);

    if (!input) return;

    const icon = btn.querySelector("i");

    if (input.type === "password") {
        input.type = "text";
        btn.setAttribute("aria-label", "隱藏密碼");

        if (icon) {
            icon.className = "bi bi-eye-slash text-sm";
        }
    } else {
        input.type = "password";
        btn.setAttribute("aria-label", "顯示密碼");

        if (icon) {
            icon.className = "bi bi-eye text-sm";
        }
    }
});

document.addEventListener("DOMContentLoaded", function () {
    const changepwForm = document.getElementById("changepwForm");
    const message = document.getElementById("message");

    if (!changepwForm) return;

    changepwForm.addEventListener("submit", function (event) {
        event.preventDefault();

        const oldPassword = document.getElementById("old_password")?.value || "";
        const newPassword = document.getElementById("new_password")?.value || "";

        if (!oldPassword || !newPassword) {
            if (message) {
                message.innerHTML = `<div class="text-red-500 text-sm">請輸入原始密碼與新密碼</div>`;
            } else {
                alert("請輸入原始密碼與新密碼");
            }
            return;
        }
        fetch("/api/change_password", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                old_password: oldPassword,
                new_password: newPassword
            })
        })
        .then(res => res.json())
        .then(result => {
            if (result.success) {
                alert("密碼修改成功，請重新登入");

                if (result.redirect) {
                    window.location.href = result.redirect;
                } else {
                    window.location.href = "/logout";
                }
            } else {
                if (message) {
                    message.innerHTML = `<div class="text-red-500 text-sm">${result.message || "修改失敗"}</div>`;
                } else {
                    alert(result.message || "修改失敗");
                }
            }
        })
        .catch(err => {
            console.error(err);

            if (message) {
                message.innerHTML = `<div class="text-red-500 text-sm">修改失敗，請稍後再試</div>`;
            } else {
                alert("修改失敗，請稍後再試");
            }
        });
    });
});