document.addEventListener('DOMContentLoaded', function() {
    const statusSelect = document.getElementById('statusSelect');
    const caseRows = document.querySelectorAll('.case-row');

    statusSelect.addEventListener('change', function() {
        const selectedStatus = this.value;

        caseRows.forEach(row => {
            // 取得該行的狀態資料
            const rowStatus = row.getAttribute('data-status');

            // 如果選「所有狀態」，或者該行狀態符合選中狀態，則顯示
            if (selectedStatus === 'all' || rowStatus === selectedStatus) {
                row.style.display = ''; // 恢復顯示 (table-row)
            } else {
                row.style.display = 'none'; // 隱藏
            }
        });
    });
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
              text: 'Value'
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

        // 只要點到「生理數據」就觸發繪圖
        if (btn.innerText.includes("生理數據")) {
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

ModalConsent.addEventListener('show.bs.modal', function (event) {
    var button = event.relatedTarget; // 取得被點擊的按鈕
    var title = button.getAttribute('data-bs-title');
    var pdfUrl = "/static/data" + button.getAttribute('data-bs-url');

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


