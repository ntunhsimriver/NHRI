// 新增個案及關連個案
document.querySelectorAll('.progress-bar').forEach(el => {
    el.style.width = el.dataset.width + '%';
});


document.querySelectorAll('.case-row').forEach(row => {
    row.addEventListener('click', function () {
        window.location.href = this.dataset.url;
    });
});
document.querySelectorAll('.btn-back').forEach(btn => {
    btn.addEventListener('click', function () {
        history.back();
    });
});


const modalAddPatient = document.getElementById('Modal_addPatient');
const msg = document.getElementById('message');


document.querySelectorAll('[data-url]').forEach(btn => {
    btn.addEventListener('click', function () {
        window.location.href = this.dataset.url;
    });
});

// 先宣告
const form = document.getElementById('registerForm');
const patid = document.getElementById("addPatId");



document.addEventListener('DOMContentLoaded', function() {

    const statusSelect = document.getElementById('statusSelect');
    const searchInput = document.getElementById('searchInput');
    const caseRows = document.querySelectorAll('.case-row');

    function filterRows() {
        const selectedStatus = statusSelect.value;
        const searchText = searchInput.value.toLowerCase();

        caseRows.forEach(row => {

            const rowStatus = row.getAttribute('data-status');
            const hashId = row.getAttribute('data-hash').toLowerCase();

            const matchStatus =
                selectedStatus === 'all' || rowStatus === selectedStatus;

            const matchSearch =
                hashId.includes(searchText);

            if (matchStatus && matchSearch) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }

        });
    }

     if (statusSelect) {
        statusSelect.addEventListener('change', filterRows);
    }

    if (searchInput) {
        searchInput.addEventListener('input', filterRows);
    }


});


