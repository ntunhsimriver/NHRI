document.querySelectorAll('.project-btn').forEach(btn => {
    btn.addEventListener('click', function () {
        // alert(this.dataset.url);
        window.location.href = this.dataset.url;
    });
});

document.addEventListener("DOMContentLoaded", function () {
            if (window.layoutHelpers) {
                window.layoutHelpers.init();
            }

            // 額外保險：任何 .layout-sidenav-toggle 被點擊時，切換側欄收合/展開
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