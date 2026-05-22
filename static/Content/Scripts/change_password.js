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
document.querySelectorAll('.project-btn').forEach(btn => {
    btn.addEventListener('click', function () {
        
        window.location.href = this.dataset.url;
    });
});

document.addEventListener("DOMContentLoaded", function () {
            if (window.layoutHelpers) {
                window.layoutHelpers.init();
            }

            
            document.querySelectorAll('.layout-sidenav-toggle').forEach(function (el) {
                el.addEventListener('click', function () {
                    if (window.layoutHelpers && typeof window.layoutHelpers.toggleCollapsed === 'function') {
                        window.layoutHelpers.toggleCollapsed();
                    }
                });
            });
        });

        document.querySelectorAll('.project-btn').forEach(btn => {
            btn.addEventListener('click', function () {
                window.location.href = this.dataset.url;
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

  document.addEventListener('DOMContentLoaded', function() {

    const searchInput = document.getElementById('searchInput');
    const caseRows = document.querySelectorAll('.case-row');

    function filterRows() {
        const searchText = searchInput.value.toLowerCase().trim();

        caseRows.forEach(row => {

            const proid = (row.getAttribute('data-proid') || '').toLowerCase();
            const proname = (row.getAttribute('data-name') || '').toLowerCase();

            const matchSearch =
                proid.includes(searchText) ||
                proname.includes(searchText);

            row.style.display = matchSearch ? '' : 'none';
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', filterRows);
    }

});