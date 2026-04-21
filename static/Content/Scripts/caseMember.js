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
        const tds = row.querySelectorAll("td");
        if (tds.length < 4) return;

        const projectId = tds[0]?.innerText.trim() || "";
        const oldPatientInput = tds[1]?.querySelector("input");
        const newPatientInput = tds[2]?.querySelector("input");
        const createdAt = tds[3]?.innerText.trim() || "";


        const oldPatientId = oldPatientInput?.value.trim() || "";
        const newPatientId = newPatientInput?.value.trim() || "";

        // 🔥 檢查 old_patient_id 格式
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

    // ❌ 有錯就不要送
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
    if (row) {
        row.remove();
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

function addList(projectId) {
    const tbody = document.getElementById("caseTableBody");
    if (!tbody) {
        console.error("找不到 table body");
        return;
    }

    const newRow = document.createElement("tr");
    newRow.className = "hover:bg-slate-50 transition-colors group";

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

    // 👉 找到剛新增那一列的 new_id input
    const newIdInput = newRow.querySelector(".new-id-input");

    // 👉 呼叫 API 取得 new ID
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