document.addEventListener('DOMContentLoaded', function () {

    document.addEventListener('click', function (e) {

        
        const stepBtn = e.target.closest('.step-btn');
        if (stepBtn) {
            const type = stepBtn.dataset.type;
            goToStep2(type);
            return;
        }

        
        const backBtn = e.target.closest('.btn-step-back');
        if (backBtn) {
            goToStep1();
            return;
        }

        
        const uploadBtn = e.target.closest('.btn-upload');
        if (uploadBtn) {
            handleUpload();
            return;
        }

    });

});


function goToStep2(type) {
    
    document.getElementById('step-1-content').classList.add('hidden');
    document.getElementById('step-2-content').classList.remove('hidden');

    document.getElementById('fhir_project').classList.add('hidden');

    
    const circle2 = document.getElementById('step-circle-2');
    circle2.classList.remove('bg-slate-200', 'text-slate-500');
    circle2.classList.add('bg-blue-600', 'text-white');

    
    document.getElementById('step-line-1').classList.remove('bg-slate-200');
    document.getElementById('step-line-1').classList.add('bg-blue-600');

    console.log("選取的來源類型是:", type);

    document.getElementById('type-hidden').value = type; 
    const hintElement = document.getElementById('format-hint'); 
    const infoElement = document.getElementById('file-info-text'); 

    if (type === 'FHIR') {
        hintElement.innerText = ".json";
        infoElement.innerText = "請上傳 Bundle transaction 格式的 FHIR 檔案，type 需為 transaction，且每筆資料需包含 request 設定。若需保留原始 ID 並完整匯入資料，請於 transaction 中使用 PUT 方式上傳；使用 collection 或 POST 可能導致資料無法完整寫入或 ID 被系統重新產生。";
        fileInput.accept = ".json"; 
    } 
    else if (type === 'Watch') {
        hintElement.innerText = ".csv";
        infoElement.innerText = "格式範例";
        fileInput.accept = ".csv,.xlsx"; 
    }
    else if (type === 'Asus') {
        document.getElementById('fhir_project').classList.remove('hidden');
        hintElement.innerText = ".json";
        infoElement.innerText = "請直接上傳華碩手表api的回傳檔案，並直接由系統上傳FHIR Server。";
        fileInput.accept = ".json"; 
    }
}

function goToStep1() {
    
    document.getElementById('step-1-content').classList.remove('hidden');
    document.getElementById('step-2-content').classList.add('hidden');

    
    const circle2 = document.getElementById('step-circle-2');
    circle2.classList.add('bg-slate-200', 'text-slate-500');
    circle2.classList.remove('bg-blue-600', 'text-white');

    document.getElementById('step-line-1').classList.add('bg-slate-200');
    document.getElementById('step-line-1').classList.remove('bg-blue-600');

    
    const fileInput = document.getElementById('file-upload'); 
    fileInput.value = ""; 

    
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
    
    const file = fileInput.files[0];

    const select = document.getElementById("fhir_project");
    if (fileType === "Asus" && !select.value) {
        alert("手錶資料必須選擇上傳的資料為哪一類型資料!");
        return;
    }

    
    if (!file) {
        alert("請先選擇或拖曳檔案！");
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file); 
    formData.append('fileType', fileType);  
    formData.append('fhir_project', select.value);  

    
    const xhr = new XMLHttpRequest();
    showUploadSpinner();

    
    xhr.open('POST', '/api/uploadFHIR', true);

    

    
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

    
    xhr.upload.onprogress = function (e) {
        if (e.lengthComputable) {
            const percent = (e.loaded / e.total) * 100;
            console.log("目前進度: " + Math.round(percent) + "%");
        }
    };

    
    xhr.send(formData);
    
    
}








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


['dragover', 'dragenter', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
    }, false);
});


['dragover', 'dragenter'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
        dropZone.classList.add('border-blue-500', 'bg-blue-100/50');
    }, false);
});


['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
        dropZone.classList.remove('border-blue-500', 'bg-blue-100/50');
    }, false);
});


dropZone.addEventListener('drop', (e) => {
    const draggedFiles = e.dataTransfer.files; 

    if (draggedFiles.length > 0) {
        
        fileInput.files = draggedFiles; 
        
        
        updateFileName(draggedFiles[0].name);
    }
});


fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        updateFileName(e.target.files[0].name);
    }
});


function updateFileName(name) {
    statusText.innerText = "已選取檔案：" + name;
    statusText.classList.remove('text-slate-700');
    statusText.classList.add('text-blue-600', 'font-bold');
}

function goToStep3(stats = null) {
    
    document.getElementById('step-1-content')?.classList.add('hidden');
    document.getElementById('step-2-content')?.classList.add('hidden');
    document.getElementById('step-3-content')?.classList.remove('hidden');

    
    const circle1 = document.getElementById('step-circle-1');
    const circle2 = document.getElementById('step-circle-2');
    const circle3 = document.getElementById('step-circle-3');

    const line1 = document.getElementById('step-line-1');
    const line2 = document.getElementById('step-line-2');

    circle1?.classList.remove('bg-slate-200', 'text-slate-500');
    circle1?.classList.add('bg-blue-600', 'text-white');

    circle2?.classList.remove('bg-slate-200', 'text-slate-500');
    circle2?.classList.add('bg-blue-600', 'text-white');

    circle3?.classList.remove('bg-slate-200', 'text-slate-500');
    circle3?.classList.add('bg-blue-600', 'text-white');

    line1?.classList.remove('bg-slate-200');
    line1?.classList.add('bg-blue-600');

    line2?.classList.remove('bg-slate-200');
    line2?.classList.add('bg-blue-600');

    
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

    
    
    
    
    
    
    
    
    
}


document.addEventListener("DOMContentLoaded", function () {
    const btnReloadUploadLogs = document.getElementById("btnReloadUploadLogs");

    if (btnReloadUploadLogs) {
        btnReloadUploadLogs.addEventListener("click", function () {
            const studyId = btnReloadUploadLogs.dataset.bsStudyid;
            loadUploadLogs(studyId);
        });

        
        const studyId = btnReloadUploadLogs.dataset.bsStudyid;
        loadUploadLogs(studyId);

    }
});

function loadUploadLogs(studyId) {
    const tbody = document.getElementById("uploadLogTableBody");

    if (!tbody) return;

    if (!studyId) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="px-4 py-6 text-center text-rose-500">
                    缺少 study_id，無法讀取上傳紀錄
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = `
        <tr>
            <td colspan="5" class="px-4 py-6 text-center text-slate-400">
                載入中...
            </td>
        </tr>
    `;

    fetch(`/api/fhir_upload_logs/${encodeURIComponent(studyId)}`)
        .then(res => res.json())
        .then(result => {
            if (!result.success) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="5" class="px-4 py-6 text-center text-rose-500">
                            讀取失敗
                        </td>
                    </tr>
                `;
                return;
            }

            const logs = result.data || [];

            if (logs.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="5" class="px-4 py-6 text-center text-slate-400">
                            尚無上傳紀錄
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = logs.map(log => `
                <tr class="hover:bg-slate-50">
                    <td class="px-4 py-3 text-slate-700">${log.time}</td>
                    <td class="px-4 py-3 font-mono text-xs text-slate-500">${log.original_filename || log.folder}</td>
                    <td class="px-4 py-3 text-slate-700">${log.total_resources}</td>
                    <td class="px-4 py-3">
                        <span class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                            log.has_stats
                                ? "bg-emerald-50 text-emerald-700"
                                : "bg-amber-50 text-amber-700"
                        }">
                            ${log.status}
                        </span>
                    </td>
                    <td class="px-4 py-3 text-center">
                        <button
                            type="button"
                            class="btn-open-upload-log rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
                            data-log-folder="${log.folder}"
                            data-study-id="${studyId}">
                            查看結果
                        </button>
                    </td>
                </tr>
            `).join("");
        })
        .catch(err => {
            console.error(err);
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="px-4 py-6 text-center text-rose-500">
                        讀取上傳紀錄失敗
                    </td>
                </tr>
            `;
        });
}



document.addEventListener("click", function (event) {
    const btn = event.target.closest(".btn-open-upload-log");

    if (!btn) return;

    const studyId = btn.dataset.studyId;
    const logFolder = btn.dataset.logFolder;

    openUploadLog(studyId, logFolder);
});

function openUploadLog(studyId, logFolder) {
    if (!studyId || !logFolder) {
        alert("缺少上傳紀錄資訊");
        return;
    }

    fetch(`/api/fhir_upload_logs/${encodeURIComponent(studyId)}/${encodeURIComponent(logFolder)}`)
        .then(res => res.json())
        .then(result => {
            if (!result.success) {
                alert(result.message || "讀取上傳結果失敗");
                return;
            }

            goToStep3(result.stats);
        })
        .catch(err => {
            console.error(err);
            alert("讀取上傳結果失敗");
        });
}