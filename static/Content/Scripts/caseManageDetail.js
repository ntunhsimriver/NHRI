const patIdInput = document.getElementById("pat_id_hidden");
const patId = patIdInput.value;


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

const spinner = document.getElementById('chart-loading-spinner');

document.addEventListener("DOMContentLoaded", () => {
    const startInput = document.getElementById("startDate");
    const endInput = document.getElementById("endDate");

    
    if (!startInput || !endInput) return;

    const today = new Date();
    const end = today.toISOString().split("T")[0];

    const startDate = new Date();
    startDate.setDate(today.getDate() - 14);
    const start = startDate.toISOString().split("T")[0];

    
    if (!startInput.value) startInput.value = start;
    if (!endInput.value) endInput.value = end;

    
    endInput.min = startInput.value;
    startInput.max = endInput.value;

    
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.file-trigger');
        if (!btn) return;

        const targetId = btn.dataset.target;
        const fileType = btn.dataset.type;
        const input = document.getElementById(targetId);

        if (input) {
            input.dataset.type = fileType; 
            input.click();
        }
    });

    
    document.querySelectorAll('input[type="file"]').forEach(input => {
        input.addEventListener('change', function (event) {
            const fileType = this.dataset.type;
            handleFileSelect(event, fileType);

            
            this.value = '';
        });
    });
});



document.querySelectorAll('[data-url]').forEach(btn => {
    btn.addEventListener('click', function () {
        window.location.href = this.dataset.url;
    });
});





const btn = document.getElementById('btn-filter');
if (btn) {
    btn.addEventListener('click', function () {
        handleFilter();
    });
}
let SERVER_DATA = {
    sbp: [],
    dbp: [],
    hr: [],
    labels: []
};

function handleFilter() {
    const startInput = document.getElementById("startDate");
    const endInput = document.getElementById("endDate");
    
    const spinner = document.getElementById("chart-loading-spinner");

    if (!startInput || !endInput || !patIdInput) {
        console.error("找不到必要的 DOM 元素");
        return;
    }

    const start = startInput.value;
    const end = endInput.value;

    console.log("handleFilter:", { start, end, patId });

    
    if (vitalsChart) {
        vitalsChart.destroy();
        vitalsChart = null;
    }

    
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

            
            if (spinner) {
                spinner.classList.add("hidden");
            }
            
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


function drawChart() {
    const ctx = document.getElementById('myChart-Vitals');
    if (!ctx) return;

    
    if (vitalsChart) {
        vitalsChart.destroy();
    }

    
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
          mode: 'nearest',   
          axis: 'x',         
          intersect: false   
        },

        plugins: {
          title: {
            display: false,
            text: '生理數據 (Vitals)'
          },
          legend: {
            labels: {
              usePointStyle: true,   
              pointStyle: 'line',  
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


document.querySelectorAll('#nav-tab button').forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = new bootstrap.Tab(btn);
        tab.show();

        
        if (btn.innerText.includes("檢驗檢查")) {
            
            window.requestAnimationFrame(() => {
                
                
                if (typeof SERVER_DATA !== 'undefined') {
                    
                    
                    const hasData = SERVER_DATA.sbp && SERVER_DATA.sbp.some(v => v !== null);
                    
                    if (!hasData) {
                        
                        const title = document.getElementById('myChartText');
                        if (title) title.innerText = "生理趨勢圖 (近14天) - 暫無量測紀錄";
                        console.warn("No data found in SERVER_DATA");
                    } else {
                        
                        drawChart();
                    }
                }
            });
        }
    });
});



var ModalConsent = document.getElementById('Modal_Consent');
if (ModalConsent) {
    ModalConsent.addEventListener('show.bs.modal', function (event) {
        var button = event.relatedTarget; 
        var title = button.getAttribute('data-bs-title');
        var pdfUrl = "/static/data/consent" + button.getAttribute('data-bs-url');
        
        ModalConsent.querySelector('#Modal_Consent_title').textContent = title;
        
        var iframe = ModalConsent.querySelector('#Consent_PDF_Viewer');
        iframe.src = pdfUrl;

    });

    
    ModalConsent.addEventListener('hidden.bs.modal', function () {
    ModalConsent.querySelector('#Consent_PDF_Viewer').src = "";
});
}





function handleFileSelect(event, fileType) {
    const file = event.target.files[0]; 
    const patid = document.getElementById('pat_id_hidden').value; 
    if (file) {
        console.log("選取的檔案名稱:", file.name);
        console.log("檔案大小:", (file.size / 1024).toFixed(2), "KB");
        
        
        alert("你已選取檔案：" + file.name);

        const formData = new FormData();
        formData.append('file', file); 
        formData.append('fileType', fileType);  
        formData.append('patid', patid);  

        
        const xhr = new XMLHttpRequest();


        
        xhr.open('POST', '/api/uploadFHIR', true);

        
        xhr.onload = function () {
            if (xhr.status === 200) {
                
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

        
        xhr.upload.onprogress = function (e) {
            if (e.lengthComputable) {
                const percent = (e.loaded / e.total) * 100;
                console.log("目前進度: " + Math.round(percent) + "%");
            }
        };

        
        xhr.send(formData);
        
    }
}



document.addEventListener("click", function(e) {
  const toggle = e.target.closest(".tw-encounter-one");
  if (!toggle) return;
  const encounterId = toggle.dataset.encounterId;
  const target = document.querySelector(toggle.dataset.target);

  if (!target) return;

  const isOpening = target.classList.contains("hidden");

  
  target.classList.toggle("hidden");

  
  if (isOpening) {
    fetch(`/api/getEncounter/${encounterId}`)
      .then(response => response.json())
      .then(data => {
        const detail = document.querySelector(`#detail-${encounterId}`);

        let html = "";

        if (data.Condition && data.Condition.length > 0) {
          html += `
            <div>
              <div class="mb-2 flex items-center justify-between">
                <h5 class="text-sm font-semibold text-slate-800">Condition</h5>
                <span class="text-xs text-slate-500">共 ${data.Condition.length} 筆</span>
              </div>

              <div class="space-y-2">
          `;

          data.Condition.forEach(c => {
            html += `
              <div class="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
                <p class="text-sm font-medium text-slate-800">診斷代碼：${c.code}</p>
                <p class="mt-1 text-xs text-slate-500">看診日期：${c.recordedDate}</p>
              </div>
            `;
          });

          html += `
              </div>
            </div>
          `;
        } else {
          html = `
            <div class="text-sm text-slate-400">
              沒有 Condition 資料
            </div>
          `;
        }

        detail.innerHTML = html;
      })
      .catch(err => {
        console.error("資料抓取失敗:", err);
      });
  }
});


document.addEventListener("click", function (e) {
  const toggle = e.target.closest(".tw-encounter-list-toggle");
  
  if (!toggle) return;

  const target = document.querySelector(toggle.dataset.target);
  const body = document.getElementById("EncounterListBody");

  if (!target || !body) return;

  const isOpening = target.classList.contains("hidden");

  target.classList.toggle("hidden");

  if (!isOpening) return;

  if (target.dataset.loaded === "true") return;

  body.innerHTML = `
    <div class="text-sm text-slate-500">
      資料讀取中......
    </div>
  `;

  fetch(`/api/getEncounter_all/${patId}`)
    .then(response => {
      if (!response.ok) {
        throw new Error("API 回傳錯誤");
      }
      return response.json();
    })
    .then(data => {
      let encounters = data.Encounter || data.encounters || data || [];

      if (!encounters || encounters.length === 0) {
        body.innerHTML = `
          <p class="text-sm text-slate-500">暫無資料</p>
        `;
        target.dataset.loaded = "true";
        return;
      }

      let html = "";

      encounters.forEach(item => {
        const start = item.start
          ? item.start.split("+")[0].replace("T", " ")
          : "-";

        const end = item.end
          ? item.end.split("+")[0].replace("T", " ")
          : "-";

        html += `
          <div class="relative flex gap-6">
            <div class="relative z-10 flex h-8 w-8 flex-none items-center justify-center rounded-full border-2 border-white shadow-sm bg-gray-500 text-white">
              Enc
            </div>

            <div class="flex-1 rounded-lg border border-slate-100 bg-slate-50 p-4 transition-all hover:border-blue-200 hover:bg-white hover:shadow-sm">
              <div
                class="tw-encounter-one"
                data-target="#detail-${item.id}"
                data-encounter-id="${item.id}"
                role="button"
              >
                <div class="mb-2 flex items-center justify-between">
                  <h4 class="text-base font-bold text-slate-800">就醫型態: ${item.class || "-"}</h4>
                  <h4 class="text-base font-bold text-slate-800">就醫科別: ${item.serviceType || "-"}</h4>
                  <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium type-${item.status || ""}">
                    ${item.status || "-"}
                  </span>
                </div>

                <p class="mt-1 text-sm text-slate-600">就醫日期: ${start}</p>
                <p class="mt-1 text-sm text-slate-600">離院日期: ${end}</p>
              </div>

              <div id="detail-${item.id}" class="hidden border-t border-slate-100 mt-4 pt-4">
                <div class="space-y-4">
                  資料讀取中......
                </div>
              </div>
            </div>
          </div>
        `;
      });

      body.innerHTML = html;
      target.dataset.loaded = "true";
    })
    .catch(err => {
      console.error("EncounterList 資料抓取失敗:", err);

      body.innerHTML = `
        <div class="text-sm text-red-500">
          看診紀錄讀取失敗，請稍後再試
        </div>
      `;
    });
});

document.addEventListener("click", function (e) {
  const toggle = e.target.closest(".tw-treatment-list-toggle");
  if (!toggle) return;

  const target = document.querySelector(toggle.dataset.target);
  const body = document.querySelector(toggle.dataset.body);
  const treatmentType = toggle.dataset.treatmentType;

  if (!target || !body || !treatmentType) return;

  const isOpening = target.classList.contains("hidden");

  target.classList.toggle("hidden");

  if (!isOpening) return;

  if (target.dataset.loaded === "true") return;

  body.innerHTML = `
    <div class="text-sm text-slate-500">
      資料讀取中......
    </div>
  `;

  fetch(`/api/getTreatment_all/${patId}/${treatmentType}`)
    .then(response => {
      if (!response.ok) {
        throw new Error("API 回傳錯誤");
      }
      return response.json();
    })
    .then(data => {
      const records =
        data[treatmentType] ||
        data.Procedure ||
        data.MedicationRequest ||
        data.DiagnosticReport ||
        data.treatments ||
        data ||
        [];

      if (!records || records.length === 0) {
        body.innerHTML = `
          <p class="text-sm text-slate-500">暫無資料</p>
        `;
        target.dataset.loaded = "true";
        return;
      }

      let html = "";

      records.forEach(item => {
        const type = item.type || treatmentType;
        const typeShort = type.substring(0, 3);

        const date = item.date
          ? item.date.split("+")[0].replace("T", " ")
          : "-";

        const code = item.code || "-";
        const status = item.status || "-";
        const outcome = item.outcome || "-";
        const dosage = item.dosage || "-";
        const result = item.result || item.conclusion || item.value || "-";

        let titleLabel = "治療項目";
        let dateLabel = "治療日期";
        let detailLabel = "治療結果";
        let detailValue = outcome;

        if (treatmentType === "MedicationRequest") {
          titleLabel = "用藥項目";
          dateLabel = "用藥日期";
          detailLabel = "劑量備註";
          detailValue = dosage;
        }

        if (treatmentType === "DiagnosticReport") {
          titleLabel = "檢驗檢查項目";
          dateLabel = "檢驗檢查日期";
          detailLabel = "檢驗檢查結果";
          detailValue = result;
        }

        html += `
          <div class="relative flex gap-6">
            <div class="relative z-10 flex h-8 w-8 flex-none items-center justify-center rounded-full border-2 border-white text-xs shadow-sm type-${typeShort}">
              ${typeShort}
            </div>

            <div class="flex-1 rounded-lg border border-slate-100 bg-slate-50 p-4 transition-all hover:border-blue-200 hover:bg-white hover:shadow-sm">
              <div>
                <div class="mb-2 flex items-center justify-between gap-4">
                  <h4 class="text-base font-bold text-slate-800">
                    ${titleLabel}: ${code}
                  </h4>

                  <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium type-${status}">
                    ${status}
                  </span>
                </div>

                <p class="mt-1 text-sm text-slate-600">
                  ${dateLabel}: ${date}
                </p>

                <p class="mt-1 text-sm text-slate-600 whitespace-pre-line">
                  <span class="font-medium">${detailLabel}:</span>
                  ${detailValue}
                </p>
              </div>
            </div>
          </div>
        `;
      });

      body.innerHTML = html;
      target.dataset.loaded = "true";
    })
    .catch(err => {
      console.error(`${treatmentType} 資料抓取失敗:`, err);

      body.innerHTML = `
        <div class="text-sm text-red-500">
          資料讀取失敗，請稍後再試
        </div>
      `;
    });
});




var ModalupdatePatient = document.getElementById('Modal_updatePatient');

var ModalInstance = bootstrap.Modal.getOrCreateInstance(ModalupdatePatient);

ModalupdatePatient.addEventListener('show.bs.modal', function (event) {
    var button = event.relatedTarget; 
    var input_data = button.getAttribute('data-bs-value')
    var data = JSON.parse(input_data);

    var modelPatId = document.getElementById('addPatId');
    if (modelPatId) modelPatId.value = data.PatId;

    var modelPeriodStart = document.getElementById('addPeriodStart');
    if (modelPeriodStart) modelPeriodStart.value = data.PeriodStart;

    var modelPeriodEnd = document.getElementById('addPeriodEnd');
    if (modelPeriodEnd) modelPeriodEnd.value = data.PeriodEnd;

    var modelStatus = document.getElementById('addStatus');
    if (modelStatus) modelStatus.value = data.Status;

});


const form = document.getElementById('registerForm');
const msg = document.getElementById('message');


document.getElementById('Modal_updatePatient').addEventListener('hidden.bs.modal', function () {
    form.reset();
    msg.textContent = '';
    msg.className = 'message';
    if (modalEl.contains(document.activeElement)) {
        document.activeElement.blur();
      }

});



form.addEventListener('submit', async function (e) {
    e.preventDefault();
    
    const pat_id = document.getElementById('addPatId').value;
    const start = document.getElementById('addPeriodStart').value;
    const end = document.getElementById('addPeriodEnd').value;
    const status = document.getElementById('addStatus').value;
    const type = 'update'


    
    msg.classList.remove('error-message', 'success-message');

    const response = await fetch('/api/addPatient', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pat_id, start, end, type, status })
    });

    const result = await response.json();
    if (result.success) {
        msg.textContent = result.message;
        msg.classList.add('success-message');
        setTimeout(() => {
            location.reload();
        }, 500);
    } else {
        msg.textContent = result.message;
        msg.classList.add('error-message');
    }
});

document.addEventListener("click", function (event) {
    const toggle = event.target.closest(".tw-collapse-toggle");

    if (!toggle) return;

    const targetSelector = toggle.getAttribute("data-target");
    const target = document.querySelector(targetSelector);

    if (!target) {
        console.error("找不到 collapse target:", targetSelector);
        return;
    }

    target.classList.toggle("hidden");
});