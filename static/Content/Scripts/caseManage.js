// 新增個案及關連個案
const modalAddPatient = document.getElementById('Modal_addPatient');
const msg = document.getElementById('message');

const spinner = document.getElementById('chart-loading-spinner');

document.addEventListener("DOMContentLoaded", () => {
    const startInput = document.getElementById("startDate");
    const endInput = document.getElementById("endDate");

    // 如果元素不存在就不做
    if (!startInput || !endInput) return;

    const today = new Date();
    const end = today.toISOString().split("T")[0];

    const startDate = new Date();
    startDate.setDate(today.getDate() - 14);
    const start = startDate.toISOString().split("T")[0];

    // ⭐ 只有在沒有值時才自動填
    if (!startInput.value) startInput.value = start;
    if (!endInput.value) endInput.value = end;

    // 限制日期
    endInput.min = startInput.value;
    startInput.max = endInput.value;
});

modalAddPatient.addEventListener('show.bs.modal', async function (event) {

    const button = event.relatedTarget;
    // 取得 data-bs-for 的值
    const mode = button.getAttribute('data-bs-for');



    document.getElementById('hidden_addPatient').value = mode;

    const title = document.getElementById('Modal_addPatient_title');
    const submitBtn = modalAddPatient.querySelector('button[type="submit"]');

    const fields_Gender_birth = document.getElementById('addPatient_Gender_birth');

    if (mode === 'new') {
    title.innerText = '新增個案';
    submitBtn.innerText = '確認新增';
    submitBtn.className = 'rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700';
    fields_Gender_birth.classList.remove('hidden');

    } else if (mode === 'connect') {
    title.innerText = '關聯已存在個案(Patient)';
    submitBtn.innerText = '立即關聯';
    fields_Gender_birth.classList.add('hidden');

    }

});

// 當 Modal 關閉時自動重置表單
modalAddPatient.addEventListener('hidden.bs.modal', function () {
    form.reset();
    msg.textContent = '';
    msg.className = 'message';
});


// 先宣告
const form = document.getElementById('registerForm');
const patid = document.getElementById("addPatId");
// const patidenti = document.getElementById("addPatIdenti");
// // 這邊是原本有身份證字號時用的，現在沒用了
// function toggleInput() {
//     // 控制 patidenti
//     if (patid.value.trim()) {
//         patidenti.disabled = true;
//         patidenti.classList.add("bg-gray-100", "cursor-not-allowed");
//     } else {
//         patidenti.disabled = false;
//         patidenti.classList.remove("bg-gray-100", "cursor-not-allowed");
//     }

//     // 控制 patid
//     if (patidenti.value.trim()) {
//         patid.disabled = true;
//         patid.classList.add("bg-gray-100", "cursor-not-allowed");
//     } else {
//         patid.disabled = false;
//         patid.classList.remove("bg-gray-100", "cursor-not-allowed");
//     }
// }

// function resetFormState() {
//     patid.value = "";
//     patidenti.value = "";

//     patid.disabled = false;
//     patidenti.disabled = false;

//     patid.classList.remove("bg-gray-100", "cursor-not-allowed");
//     patidenti.classList.remove("bg-gray-100", "cursor-not-allowed");
// }

patid.addEventListener("input", toggleInput);
// patidenti.addEventListener("input", toggleInput);

form.addEventListener('submit', async function (e) {
    e.preventDefault();
    const pat_id = patid.value;
    // const pat_identi = patidenti.value;
    const gender = document.getElementById('addGender').value;
    const birthDate = document.getElementById('addBirth').value;
    const start = document.getElementById('addPeriodStart').value;
    const type = document.getElementById('hidden_addPatient').value; // 存這個json到底是新增還是關聯
    

    // const role = document.getElementById('newUser_role').value;

    // 清除前一次樣式
    msg.classList.remove('error-message', 'success-message');
    const response = await fetch('/api/addPatient', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pat_id, gender, birthDate, start, type })
    });

    const result = await response.json();
    if (result.success) {
        msg.textContent = result.message;
        msg.classList.add('success-message');
        setTimeout(() => {
            location.reload();
        }, 1000);
    } else {
        msg.textContent = result.message;
        msg.classList.add('error-message');
    }
});



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

    statusSelect.addEventListener('change', filterRows);
    searchInput.addEventListener('input', filterRows);

});

// 這邊寫搜尋受測者的ajax，未來有空再寫
let debounceTimer;
const searchInput = document.getElementById('searchInput'); // 假設你的 input ID 是這個


if (searchInput) {
    searchInput.addEventListener('input', function() {
        
        
    });
}

// searchInput.addEventListener('input', function() {
//     alert(searchInput);
//     const query = this.value.trim();
    
//     // 1. 清除上一次的計時器
//     clearTimeout(debounceTimer);

//     // 2. 設定 300ms 後執行 (使用者停止打字 0.3 秒才發送)
//     debounceTimer = setTimeout(() => {
//         // 顯示載入中狀態 (選選)
//         tableBody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-slate-400">搜尋中...</td></tr>';

//         // 3. 發送 AJAX 請求
//         alert("searchInput");
//     //     fetch(`/api/cases/search?q=${encodeURIComponent(query)}`)
//     //         .then(response => response.json())
//     //         .then(data => {
//     //             renderTable(data.cases);
//     //         })
//     //         .catch(err => console.error('搜尋失敗:', err));
//     // }, 300);
// });


function handleFilter() {
    const startInput = document.getElementById("startDate");
    const endInput = document.getElementById("endDate");
    const patIdInput = document.getElementById("pat_id_hidden");
    const spinner = document.getElementById("chart-loading-spinner");

    if (!startInput || !endInput || !patIdInput) {
        console.error("找不到必要的 DOM 元素");
        return;
    }

    const start = startInput.value;
    const end = endInput.value;
    const patId = patIdInput.value;

    console.log("handleFilter:", { start, end, patId });

    // 清掉舊圖
    if (vitalsChart) {
        vitalsChart.destroy();
        vitalsChart = null;
    }

    // 顯示 loading
    if (spinner) {
        spinner.classList.remove("hidden");
    }

    fetch(`/api/caseManageObs14days/${patId}?start=${start}&end=${end}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            SERVER_DATA.sbp = data[0];
            SERVER_DATA.dbp = data[1];
            SERVER_DATA.hr = data[2];
            SERVER_DATA.labels = data[3];

            // 隱藏 loading
            if (spinner) {
                spinner.classList.add("hidden");
            }
            // 直接畫圖
            drawChart();
        })
        .catch(err => {
            console.error("資料抓取失敗:", err);

            if (spinner) {
                spinner.classList.add("hidden");
            }
        });
}

let vitalsChart = null;

// 將原本的繪圖邏輯封裝成函式
function drawChart() {
    const ctx = document.getElementById('myChart-Vitals');
    if (!ctx) return;

    // 如果已經有圖表，先銷毀防止重複疊加
    if (vitalsChart) {
        vitalsChart.destroy();
    }

    // 這裡放你原本定義的 data 與 config
    const data = {
        labels: SERVER_DATA.labels,
        datasets: [
            {
                label: '收縮壓 (SBP)',
                data: SERVER_DATA.sbp,
                borderColor: '#ef4444',
                fill: false,
                cubicInterpolationMode: 'monotone',
                tension: 0.4
            },
            {
                label: '舒張壓 (DBP)',
                data: SERVER_DATA.dbp,
                borderColor: '#3b82f6',
                fill: false,
                cubicInterpolationMode: 'monotone',
                tension: 0.4
            },
            {
                label: '心率 (HR)',
                data: SERVER_DATA.hr,
                borderColor: '#22c55e',
                fill: false,
                cubicInterpolationMode: 'monotone',
                tension: 0.4
            }
        ]
    };

    vitalsChart = new Chart(ctx, {
        type: 'line',
        data: data,
        options: {
        responsive: true,
        interaction: {
          mode: 'nearest',   // 吸附最近的點
          axis: 'x',         // 只看 X 軸距離（Day）
          intersect: false   // 不用滑到點上
        },

        plugins: {
          title: {
            display: false,
            text: '生理數據 (Vitals)'
          },
          legend: {
            labels: {
              usePointStyle: true,   // 要啟用自定義的圖例
              pointStyle: 'line',  // circle | rect | rectRounded | triangle
              boxWidth: 30
            }
          }
        },

        scales: {
          x: {
            display: true,
            title: {
              display: false
            }
          },
          y: {
            display: true,
            title: {
              display: true,
              text: '生理量測平均數值'
            },
            suggestedMin: 50,
            suggestedMax: 200
          }
        }
      }
    });
}

// 監聽 Tab 點擊
document.querySelectorAll('#nav-tab button').forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = new bootstrap.Tab(btn);
        tab.show();

        // 只要點到「檢驗檢查」就觸發繪圖
        if (btn.innerText.includes("檢驗檢查")) {
            // 使用 requestAnimationFrame 確保在 DOM 更新後才畫圖
            window.requestAnimationFrame(() => {
                // --- 這裡就是你的外掛檢查邏輯 ---
                // 1. 先確認變數存在，避免噴 ReferenceError
                if (typeof SERVER_DATA !== 'undefined') {
                    
                    // 2. 檢查是否全為空
                    const hasData = SERVER_DATA.sbp && SERVER_DATA.sbp.some(v => v !== null);
                    
                    if (!hasData) {
                        // 沒資料就改文字，不畫圖
                        const title = document.getElementById('myChartText');
                        if (title) title.innerText = "生理趨勢圖 (近14天) - 暫無量測紀錄";
                        console.warn("No data found in SERVER_DATA");
                    } else {
                        // 有資料才執行你原本的 drawChart
                        drawChart();
                    }
                }
            });
        }
    });
});


// 這邊是同意書
var ModalConsent = document.getElementById('Modal_Consent');
if (ModalConsent) {
    ModalConsent.addEventListener('show.bs.modal', function (event) {
        var button = event.relatedTarget; // 取得被點擊的按鈕
        var title = button.getAttribute('data-bs-title');
        var pdfUrl = "/static/data/consent" + button.getAttribute('data-bs-url');

        // 更新標題
        ModalConsent.querySelector('#Modal_Consent_title').textContent = title;
        // 更新 PDF 檢視器
        var iframe = ModalConsent.querySelector('#Consent_PDF_Viewer');
        iframe.src = pdfUrl;

    });

    // 當 Modal 關閉時，清空 src 停止載入，節省資源
    ModalConsent.addEventListener('hidden.bs.modal', function () {
    ModalConsent.querySelector('#Consent_PDF_Viewer').src = "";
});
}




// 同意書上傳的按鈕
function handleFileSelect(event, fileType) {
    const file = event.target.files[0]; // 取得第一個檔案
    const patid = document.querySelector('h2').innerText.trim(); // 抓pat id
    if (file) {
        console.log("選取的檔案名稱:", file.name);
        console.log("檔案大小:", (file.size / 1024).toFixed(2), "KB");
        
        // 這裡可以加入上傳到伺服器的邏輯 (例如使用 Fetch API)
        alert("你已選取檔案：" + file.name);

        const formData = new FormData();
        formData.append('file', file); // 'file' 要對應 Flask 裡的 request.files['file']
        formData.append('fileType', fileType);  // 把fileType也一起傳到後端
        formData.append('patid', patid);  // 把patid也一起傳到後端

        // 3. 建立傳統的 AJAX 請求 (XMLHttpRequest)
        const xhr = new XMLHttpRequest();


        // 設定請求目標
        xhr.open('POST', '/api/uploadFHIR', true);

        // 監聽回傳結果
        xhr.onload = function () {
            if (xhr.status === 200) {
                // 解析 Flask 回傳的 JSON
                const response = JSON.parse(xhr.responseText);
                if (response.success) {
                    alert(response.message);
                    location.reload();
                } else {
                    alert("伺服器錯誤: " + response.message);
                }
            } else {
                alert("連線失敗，狀態碼: " + xhr.status);
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
}


document.addEventListener("click", function(e){

  const toggle = e.target.closest(".tw-encounter-one")
  if(!toggle) return

  const encounterId = toggle.dataset.encounterId
  const target = document.querySelector(toggle.dataset.target)

  const isOpening = target.classList.contains("hidden")

  // 如果是展開
  if (!isOpening){

    // 這裡 call API
    fetch(`/api/getEncounter/${encounterId}`)
        .then(response => response.json())
        .then(data => {

            const detail = document.querySelector(`#detail-${encounterId}`)

            let html = ""

            if(data.Condition){

                html += `
                <div>
                    <div class="mb-2 flex items-center justify-between">
                        <h5 class="text-sm font-semibold text-slate-800">Condition</h5>
                        <span class="text-xs text-slate-500">共 ${data.Condition.length} 筆</span>
                    </div>
                    <div class="space-y-2">
                `
                data.Condition.forEach(c => {

                    html += `
                    <div class="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
                        <p class="text-sm font-medium text-slate-800">診斷代碼：${c.code}</p>
                        <p class="mt-1 text-xs text-slate-500">看診日期：${c.recordedDate}</p>
                    </div>
                    `
                })

                html += `
                    </div>
                </div>
                `
            }

            detail.innerHTML = html
        })
        .catch(err => {
            console.error("資料抓取失敗:", err);
            statusText.innerText = "連線逾時";
            statusText.classList.replace('text-blue-500', 'text-red-500');
        });
  }

})