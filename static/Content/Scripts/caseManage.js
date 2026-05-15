document.querySelectorAll('.progress-bar').forEach(el => {
    el.style.width = el.dataset.width + '%';
});


document.querySelectorAll('.case-row').forEach(row => {
    row.addEventListener('click', function () {
        window.location.href = this.dataset.url;
    });
});


const modalAddPatient = document.getElementById('Modal_addPatient');
const msg = document.getElementById('message');


document.querySelectorAll('[data-url]').forEach(btn => {
    btn.addEventListener('click', function () {
        window.location.href = this.dataset.url;
    });
});

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


document.getElementById("updateDataCountBtn").addEventListener("click", async function () {
  const btn = this;
  var input_data = btn.getAttribute('data-bs-study')
  btn.disabled = true;
  btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> 更新中...';

  try {
    const response = await fetch("/api/update-data-count", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        study_id: input_data
      })
    });

    const result = await response.json();

    if (result.success) {
      alert("資料量已更新完成!!");
      setTimeout(() => {
            location.reload();
        }, 0);
    } else {
      alert("更新失敗：" + result.message);
    }
  } catch (error) {
    console.error(error);
    alert("呼叫 API 失敗");
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-gear"></i> 更新資料完整度數據';
  }
});