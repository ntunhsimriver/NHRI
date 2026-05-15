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