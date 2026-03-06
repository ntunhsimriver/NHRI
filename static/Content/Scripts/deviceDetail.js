// 全域變數
let SERVER_DATA = null;
let vitalsChart = null;

document.addEventListener('DOMContentLoaded', function () {
    const toggle = document.getElementById('vitalsToggle');
    const deviceId = document.getElementById('hidden_device_id').value;
    const statusText = document.getElementById('data-status');
    const spinner = document.getElementById('chart-loading-spinner');
    const collapseEl = document.getElementById('collapseVitals');

    toggle.classList.add('pointer-events-none', 'opacity-60');

    // 抓資料
    fetch(`/api/deviceDetailObs14days/${deviceId}`)
        .then(response => response.json())
        .then(data => {

            SERVER_DATA = {
                sbp: data[0],
                dbp: data[1],
                hr: data[2],
                labels: data[3]
            };

            toggle.classList.remove('pointer-events-none', 'opacity-60');
            statusText.innerText = "數據已就緒（點我展開）";
            statusText.classList.replace('text-blue-500', 'text-green-500');

            if (spinner) spinner.style.display = 'none';
        })
        .catch(err => {
            console.error("資料抓取失敗:", err);
            statusText.innerText = "連線逾時";
            statusText.classList.replace('text-blue-500', 'text-red-500');
        });

    // 監聽 collapse 是否被展開
    const observer = new MutationObserver(() => {
        if (!collapseEl.classList.contains("hidden")) {
            setTimeout(drawChart, 100);
        }
    });

    observer.observe(collapseEl, { attributes: true, attributeFilter: ["class"] });
});

// 繪圖
function drawChart() {
    console.log("drawChart called");

    const canvas = document.getElementById('myChart-Vitals');
    if (!canvas) return;

    if (!SERVER_DATA || !SERVER_DATA.labels) {
        console.warn("SERVER_DATA 尚未準備好");
        return;
    }

    const hasAnyData =
        SERVER_DATA.sbp.some(v => v !== null) ||
        SERVER_DATA.dbp.some(v => v !== null) ||
        SERVER_DATA.hr.some(v => v !== null);

    if (!hasAnyData) {
        document.getElementById('myChartText').innerText = "生理趨勢圖 - 暫無量測紀錄";
        return;
    }

    if (vitalsChart) {
        vitalsChart.destroy();
    }

    const ctx = canvas.getContext('2d');
    vitalsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: SERVER_DATA.labels,
            datasets: [
                {
                    label: '收縮壓 (SBP)',
                    data: SERVER_DATA.sbp,
                    borderColor: '#ef4444',
                    backgroundColor: '#ef4444',
                    tension: 0.4,
                    spanGaps: true
                },
                {
                    label: '舒張壓 (DBP)',
                    data: SERVER_DATA.dbp,
                    borderColor: '#3b82f6',
                    backgroundColor: '#3b82f6',
                    tension: 0.4,
                    spanGaps: true
                },
                {
                    label: '心率 (HR)',
                    data: SERVER_DATA.hr,
                    borderColor: '#22c55e',
                    backgroundColor: '#22c55e',
                    tension: 0.4,
                    spanGaps: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            resizeDelay: 100,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                }
            },
            scales: {
                y: {
                    suggestedMin: 40,
                    suggestedMax: 160,
                    title: {
                        display: true,
                        text: '數值'
                    }
                }
            }
        }
    });
}