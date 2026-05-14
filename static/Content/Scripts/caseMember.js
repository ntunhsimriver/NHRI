document.addEventListener('DOMContentLoaded', function () {
    document.addEventListener('click', function (e) {
        const addBtn = e.target.closest('.btn-add-list');
        if (addBtn) {
            const studyId = addBtn.dataset.studyId;
            addList(studyId);
            return;
        }

        const sendBtn = e.target.closest('.btn-send-list');
        if (sendBtn) {
            sendList();
            return;
        }

        const removeBtn = e.target.closest('.btn-remove-row');
        if (removeBtn) {
            removeRow(removeBtn);
        }
    });
});

function sendList() {
    const rows = document.querySelectorAll("#caseTableBody tr");
    const list = [];

    let hasError = false;

    rows.forEach((row, index) => {
        // 已標記刪除的列，不送出
        if (row.classList.contains("row-deleted")) {
            return;
        }

        const tds = row.querySelectorAll("td");
        if (tds.length < 4) return;

        const projectId = tds[0]?.innerText.trim() || "";
        const oldPatientInput = tds[1]?.querySelector("input");
        const newPatientInput = tds[2]?.querySelector("input");
        const createdAt = tds[3]?.innerText.trim() || "";

        const oldPatientId = oldPatientInput?.value.trim() || "";
        const newPatientId = newPatientInput?.value.trim() || "";

        // 檢查 old_patient_id 格式
        if (!oldPatientId.startsWith("Patient/") || oldPatientId === "Patient/") {
            hasError = true;

            oldPatientInput.classList.add("border-red-500");

            alert(`第 ${index + 1} 列：原有ID 必須是 "Patient/xxx"`);

            return;
        } else {
            oldPatientInput.classList.remove("border-red-500");
        }

        if (!projectId || !oldPatientId || !newPatientId) {
            return;
        }

        list.push({
            project_id: projectId,
            old_patient_id: oldPatientId,
            new_patient_id: newPatientId,
            created_at: createdAt
        });
    });

    if (hasError) {
        return;
    }

    if (list.length === 0) {
        alert("沒有可送出的資料");
        return;
    }

    fetch("/api/project_member/save_all", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ data: list })
    })
    .then(res => {
        if (!res.ok) throw new Error("送出失敗");
        return res.json();
    })
    .then(() => {
        alert("送出成功");
        window.location.reload();
    })
    .catch(err => {
        console.error(err);
        alert("送出失敗");
    });
}


function removeRow(button) {
    const row = button.closest("tr");

    if (!row) return;

    row.classList.toggle("row-deleted");

    const icon = button.querySelector("i");

    if (row.classList.contains("row-deleted")) {
        button.title = "取消刪除";
        button.classList.remove("hover:text-red-600");
        button.classList.add("text-red-600");

        if (icon) {
            icon.className = "bi bi-arrow-counterclockwise";
        }
    } else {
        button.title = "刪除";
        button.classList.remove("text-red-600");
        button.classList.add("hover:text-red-600");

        if (icon) {
            icon.className = "bi bi-trash";
        }
    }
}


function formatNow() {
    const d = new Date();

    const yyyy = d.getFullYear();
    const MM = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');

    const HH = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    const ss = String(d.getSeconds()).padStart(2, '0');

    return `${yyyy}-${MM}-${dd} ${HH}:${mm}:${ss}`;
}

function createCaseTable(studyId) {
    const emptyBlock = document.getElementById("emptyCaseBlock");

    if (!emptyBlock) {
        console.error("找不到 emptyCaseBlock");
        return;
    }

    emptyBlock.innerHTML = `
        <div class="space-y-6 fade-in">
            

          <div class="flex flex-col justify-between gap-4 md:flex-row md:items-center">
            <div>
              <h2 class="text-2xl font-bold text-slate-900">個案人員清單</h2>
              <p class="text-sm text-slate-500">因部分醫院來源資料可能會有重複的狀況，因此可由此頁面管理所有受試者對應的Patient id對應。</p>
            </div>
            <div class="flex gap-3">
              <button
                class="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors shadow-sm shadow-blue-500/30 btn-add-list"
                data-study-id="${studyId || ''}">
                <i class="bi bi-plus"></i> 新增對照
              </button>

              <button
                class="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 btn-send-list">

                <i class="bi bi-link-45deg"></i> 送出清單
              </button>
            </div>
          </div>

        <div class="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div class="relative flex-1">
                    <i class="bi bi-search absolute left-3 top-2 h-4 w-4 text-slate-400"></i>
                    <input
                        type="text"
                        placeholder="搜尋 Hash ID..."
                        class="w-full rounded-lg !border !border-slate-200 py-2 pl-9 pr-4 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                        id="searchInput">
                </div>
            </div>
            <div class="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
                <table class="w-full text-left text-sm">
                    <thead class="bg-slate-50 text-slate-500 border-b border-slate-200">
                        <tr>
                            <th class="px-6 py-3 font-medium">計畫代碼</th>
                            <th class="px-6 py-3 font-medium">原有ID</th>
                            <th class="px-6 py-3 font-medium">系統ID</th>
                            <th class="px-6 py-3 font-medium">創立日期</th>
                            <th class="px-3 py-3 font-medium">刪除</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100" id="caseTableBody">
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

function addList(projectId) {
    let tbody = document.getElementById("caseTableBody");

    // 如果沒有 table，代表目前是第一筆資料，要先建立 table
    if (!tbody) {
        createCaseTable(projectId);
        tbody = document.getElementById("caseTableBody");
    }

    if (!tbody) {
        console.error("找不到 table body");
        return;
    }

    const newRow = document.createElement("tr");
    newRow.className = "hover:bg-slate-50 transition-colors group cursor-pointer case-row";

    const now = formatNow();

    newRow.innerHTML = `
        <td class="px-6 py-4 font-mono font-medium text-blue-600">
            ${projectId || "-"}
        </td>

        <td class="px-6 py-4 text-slate-600">
            <input 
                type="text"
                placeholder="請輸入舊ID(如：Patient/test)"
                class="w-full rounded-md !border !border-slate-300 px-2 py-1 text-sm bg-white old-id-input">
        </td>

        <td class="px-6 py-4 text-slate-600">
            <input 
                type="text"
                placeholder="產生中..."
                readonly
                class="w-full rounded-md !border !border-slate-300 px-2 py-1 text-sm bg-slate-100 cursor-not-allowed new-id-input">
        </td>

        <td class="px-6 py-4 text-slate-600">
            ${now}
        </td>

        <td class="px-6 py-4">
            <button class="text-slate-400 hover:text-red-600 btn-remove-row">
                <i class="bi bi-trash"></i>
            </button>
        </td>
    `;

    tbody.appendChild(newRow);

    const newIdInput = newRow.querySelector(".new-id-input");

    fetch(`/api/getNewID`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            projectId: projectId
        })
    })
    .then(res => {
        if (!res.ok) {
            throw new Error("API 錯誤");
        }
        return res.json();
    })
    .then(data => {
        newIdInput.value = data || "產生失敗";
    })
    .catch(err => {
        console.error("取得 new ID 失敗:", err);
        newIdInput.value = "ERROR";
    });
}

document.addEventListener('DOMContentLoaded', function() {

    // const statusSelect = document.getElementById('statusSelect');
    const searchInput = document.getElementById('searchInput');
    const caseRows = document.querySelectorAll('.case-row');

    function filterRows() {
        // const selectedStatus = statusSelect.value;
        const searchText = searchInput.value.toLowerCase();

        caseRows.forEach(row => {

            // const rowStatus = row.getAttribute('data-status');
            const hashId_oldID = row.getAttribute('data-hash-oldID').toLowerCase();
            const hashId_newID = row.getAttribute('data-hash-newID').toLowerCase();

            // const matchStatus =
            //     selectedStatus === 'all' || rowStatus === selectedStatus;
            
            const matchSearch =
                hashId_oldID.includes(searchText) ||
                hashId_newID.includes(searchText);

            if (matchSearch) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }

        });
    }

    //  if (statusSelect) {
    //     statusSelect.addEventListener('change', filterRows);
    // }

    if (searchInput) {
        searchInput.addEventListener('input', filterRows);
    }


});