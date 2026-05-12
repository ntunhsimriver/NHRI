document.addEventListener('DOMContentLoaded', function () {

    document.addEventListener('click', function (e) {

        // Step1 → Step2
        const stepBtn = e.target.closest('.step-btn');
        if (stepBtn) {
            const type = stepBtn.dataset.type;
            goToStep2(type);
            return;
        }

        // 上一步
        const backBtn = e.target.closest('.btn-step-back');
        if (backBtn) {
            goToStep1();
            return;
        }

        // 上傳
        const uploadBtn = e.target.closest('.btn-upload');
        if (uploadBtn) {
            handleUpload();
            return;
        }

    });

});


function goToStep2(type) {
    // 1. 切換內容顯示
    document.getElementById('step-1-content').classList.add('hidden');
    document.getElementById('step-2-content').classList.remove('hidden');

    document.getElementById('fhir_project').classList.add('hidden');

    // 2. 更新進度條顏色 (把 2 號圓圈變藍色)
    const circle2 = document.getElementById('step-circle-2');
    circle2.classList.remove('bg-slate-200', 'text-slate-500');
    circle2.classList.add('bg-blue-600', 'text-white');

    // 更新 1 號跟 2 號之間的線
    document.getElementById('step-line-1').classList.remove('bg-slate-200');
    document.getElementById('step-line-1').classList.add('bg-blue-600');

    console.log("選取的來源類型是:", type);

    document.getElementById('type-hidden').value = type; // 暫存一下type是什麼
    const hintElement = document.getElementById('format-hint'); // 顯示支援的附檔名有哪些
    const infoElement = document.getElementById('file-info-text'); // 顯示檔案說明

    if (type === 'FHIR') {
        hintElement.innerText = ".json";
        infoElement.innerText = "上傳的FHIR檔案將以POST方式上傳至FHIR server，若需以PUT上傳請用transaction打包。";
        fileInput.accept = ".json"; // FHIR 只收 JSON
    } 
    else if (type === 'Watch') {
        hintElement.innerText = ".csv";
        infoElement.innerText = "格式範例";
        fileInput.accept = ".csv,.xlsx"; // 其他來源收表格檔
    }
    else if (type === 'Asus') {
        document.getElementById('fhir_project').classList.remove('hidden');
        hintElement.innerText = ".json";
        infoElement.innerText = "請直接上傳華碩手表api的回傳檔案，並直接由系統上傳FHIR Server。";
        fileInput.accept = ".json"; // 其他來源收表格檔
    }
}

function goToStep1() {
    // 返回步驟 1 的邏輯
    document.getElementById('step-1-content').classList.remove('hidden');
    document.getElementById('step-2-content').classList.add('hidden');

    // 還原進度條顏色
    const circle2 = document.getElementById('step-circle-2');
    circle2.classList.add('bg-slate-200', 'text-slate-500');
    circle2.classList.remove('bg-blue-600', 'text-white');

    document.getElementById('step-line-1').classList.add('bg-slate-200');
    document.getElementById('step-line-1').classList.remove('bg-blue-600');

    // --- 核心步驟：清空檔案資料 ---
    const fileInput = document.getElementById('file-upload'); // 確保 ID 跟你的 input 一致
    fileInput.value = ""; 

    // 順便把介面上的檔名文字改回原本的提示
    const statusText = document.getElementById('file-status-text');
    statusText.innerText = "點擊上傳或將檔案拖曳至此";
    statusText.classList.remove('text-blue-600', 'font-bold');
    statusText.classList.add('text-slate-700');

}


function formatErrorMessage(response, xhr) {
    const msg = response.message || response.error || xhr.responseText;

    if (typeof msg === "object") {
        return JSON.stringify(msg, null, 2);
    }

    return msg;
}
function showUploadSpinner() {
    const spinner = document.getElementById("uploadSpinner");
    if (spinner) {
        spinner.classList.remove("d-none");
    }
}

function hideUploadSpinner() {
    const spinner = document.getElementById("uploadSpinner");
    if (spinner) {
        spinner.classList.add("d-none");
    }
}
function handleUpload() {
    const fileInput = document.getElementById('file-upload');
    const fileType = document.getElementById('type-hidden').value;
    // alert(fileType);
    const file = fileInput.files[0];

    const select = document.getElementById("fhir_project");
    if (fileType === "Asus" && !select.value) {
        alert("手錶資料必須選擇上傳的資料為哪一類型資料!");
        return;
    }

    // 1. 基本檢查
    if (!file) {
        alert("請先選擇或拖曳檔案！");
        return;
    }
    // 2. 建立 FormData 物件（這是 AJAX 傳檔案的關鍵）
    const formData = new FormData();
    formData.append('file', file); // 'file' 要對應 Flask 裡的 request.files['file']
    formData.append('fileType', fileType);  // 把fileType也一起傳到後端
    formData.append('fhir_project', select.value);  // 把fileType也一起傳到後端

    // 3. 建立傳統的 AJAX 請求 (XMLHttpRequest)
    const xhr = new XMLHttpRequest();
    showUploadSpinner();

    // 設定請求目標
    xhr.open('POST', '/api/uploadFHIR', true);

    

    // 監聽回傳結果
    xhr.onload = function () {
        

        let response = {};

        try {
            response = JSON.parse(xhr.responseText);
        } catch (e) {
            response = {};
        }
        
        console.log("後端回傳 response =", response);
        console.log("stats =", response.stats);
        hideUploadSpinner();
        if (xhr.status === 200) {
            if (response.success) {
                const stats = response.stats || response.response?.stats || null;
                goToStep3(stats);
            } else {
                alert("伺服器錯誤: " + formatErrorMessage(response, xhr));
            }
        } else {
            alert(
                "連線失敗，狀態碼: " + xhr.status + "\n" +
                "錯誤訊息: " + formatErrorMessage(response, xhr)
            );
        }
    };

    // (選填) 如果你以後想做進度條，就是在這監聽
    xhr.upload.onprogress = function (e) {
        if (e.lengthComputable) {
            const percent = (e.loaded / e.total) * 100;
            console.log("目前進度: " + Math.round(percent) + "%");
        }
    };

    // 4. 正式發送資料
    xhr.send(formData);
    
    
}





// 下面是寫上傳檔案的那個框框

// 上傳
document.getElementById('file-upload').addEventListener('change', function(e) {
  const fileName = e.target.files[0]?.name;
  if (fileName) {
    const statusText = document.getElementById('file-status-text');
    statusText.innerText = "已選取：" + fileName;
    statusText.classList.remove('text-slate-700');
    statusText.classList.add('text-blue-600', 'font-bold');
  }
});

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-upload');
const statusText = document.getElementById('file-status-text');

// 阻止瀏覽器預設行為（防止拖入檔案時瀏覽器直接打開檔案）
['dragover', 'dragenter', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
    }, false);
});

// 1. 當檔案拖到框框上方時：變色提示
['dragover', 'dragenter'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
        dropZone.classList.add('border-blue-500', 'bg-blue-100/50');
    }, false);
});

// 2. 當檔案離開框框或放開時：恢復原狀
['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
        dropZone.classList.remove('border-blue-500', 'bg-blue-100/50');
    }, false);
});

// 3. 核心功能：當使用者「放開檔案」時
dropZone.addEventListener('drop', (e) => {
    const draggedFiles = e.dataTransfer.files; // 取得拖進來的檔案

    if (draggedFiles.length > 0) {
        // 重要：將拖入的檔案賦值給隱藏的 input
        fileInput.files = draggedFiles; 
        
        // 更新介面文字
        updateFileName(draggedFiles[0].name);
    }
});

// 4. 監聽「點擊選擇」檔案的動作 (使用者不用拖的，用點的)
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        updateFileName(e.target.files[0].name);
    }
});

// 輔助函式：更新介面上的檔名
function updateFileName(name) {
    statusText.innerText = "已選取檔案：" + name;
    statusText.classList.remove('text-slate-700');
    statusText.classList.add('text-blue-600', 'font-bold');
}

function goToStep3(stats = null) {
    // 1. 隱藏步驟 2，顯示步驟 3
    document.getElementById('step-2-content').classList.add('hidden');
    document.getElementById('step-3-content').classList.remove('hidden');

    // 2. 更新上方進度條
    const circle3 = document.getElementById('step-circle-3');
    circle3.classList.remove('bg-slate-200', 'text-slate-500');
    circle3.classList.add('bg-blue-600', 'text-white');

    // 3. 更新 2 號與 3 號之間的連接線
    const line2 = document.getElementById('step-line-2');
    line2.classList.remove('bg-slate-200');
    line2.classList.add('bg-blue-600');

    // 4. 顯示 FHIR 驗證結果
    if (stats) {
        renderStep3FHIRResult(stats);
    }
}

function renderStep3FHIRResult(stats) {
    const resourceCount = stats.resource_count || {};
    const obsSummary = stats.observation_reference_summary_after || {};
    const obsLogs = stats.observation_reference_logs_after || [];

    const missingReference =
        (obsSummary.observation_missing_patient || 0) +
        (obsSummary.observation_missing_device || 0);

    document.getElementById("step3_total_resources").textContent =
        stats.total_resources || 0;

    document.getElementById("step3_observation_count").textContent =
        resourceCount.Observation || 0;

    document.getElementById("step3_obs_both_count").textContent =
        obsSummary.observation_with_both_patient_and_device || 0;

    document.getElementById("step3_missing_reference_count").textContent =
        missingReference;

    document.getElementById("step3_total_observation").textContent =
        obsSummary.total_observation || 0;

    document.getElementById("step3_obs_with_patient").textContent =
        obsSummary.observation_with_patient || 0;

    document.getElementById("step3_obs_with_device").textContent =
        obsSummary.observation_with_device || 0;

    document.getElementById("step3_obs_missing_patient").textContent =
        obsSummary.observation_missing_patient || 0;

    document.getElementById("step3_obs_missing_device").textContent =
        obsSummary.observation_missing_device || 0;

    renderStep3ResourceCount(resourceCount);
    renderStep3ObservationTable(obsLogs);
}

function renderStep3ResourceCount(resourceCount) {
    const container = document.getElementById("step3_resource_count_list");
    if (!container) return;

    container.innerHTML = "";

    Object.entries(resourceCount).forEach(([resourceType, count]) => {
        container.innerHTML += `
            <div class="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div class="text-xs text-slate-500">${resourceType}</div>
                <div class="text-xl font-bold text-slate-800">${count}</div>
            </div>
        `;
    });

    if (Object.keys(resourceCount).length === 0) {
        container.innerHTML = `<div class="text-sm text-slate-500">沒有 Resource 統計資料</div>`;
    }
}

function renderStep3ObservationTable(obsLogs) {
    const tbody = document.getElementById("step3_observation_table");
    if (!tbody) return;

    tbody.innerHTML = "";

    obsLogs.forEach((item, index) => {
        const hasPatient = item.has_patient_reference;
        const hasDevice = item.has_device_reference;

        const patientBadge = hasPatient
            ? `<span class="inline-flex rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">有</span>`
            : `<span class="inline-flex rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-700">未綁定</span>`;

        const deviceBadge = hasDevice
            ? `<span class="inline-flex rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">有</span>`
            : `<span class="inline-flex rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-700">未綁定</span>`;

        const statusBadge = hasPatient && hasDevice
            ? `<span class="inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">完整</span>`
            : `<span class="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">需檢查</span>`;

        tbody.innerHTML += `
            <tr class="hover:bg-slate-50 step3-obs-row"
                data-search="${[
                    item.observation_id || "",
                    item.patient_reference || "",
                    item.device_reference || ""
                ].join(" ").toLowerCase()}"
            >
                <td class="px-4 py-3 text-slate-500">${index + 1}</td>
                <td class="px-4 py-3 font-mono text-xs text-slate-700">${item.observation_id || "-"}</td>
                <td class="px-4 py-3">
                    <div>${patientBadge}</div>
                    <div class="mt-1 font-mono text-xs text-slate-500">${item.patient_reference || "-"}</div>
                </td>
                <td class="px-4 py-3">
                    <div>${deviceBadge}</div>
                    <div class="mt-1 font-mono text-xs text-slate-500">${item.device_reference || "-"}</div>
                </td>
                <td class="px-4 py-3">${statusBadge}</td>
            </tr>
        `;
    });

    if (obsLogs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="px-4 py-6 text-center text-slate-500">
                    沒有 Observation 明細資料
                </td>
            </tr>
        `;
    }
}