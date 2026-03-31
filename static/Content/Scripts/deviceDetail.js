let SERVER_DATA = null;
let vitalsChart = null;
let collapseObserverBound = false;

document.addEventListener('DOMContentLoaded', function () {
    const today = new Date();
    const end = today.toISOString().split("T")[0];

    const startDate = new Date();
    startDate.setDate(today.getDate() - 7);
    const start = startDate.toISOString().split("T")[0];

    const startInput = document.getElementById("startDate");
    const endInput = document.getElementById("endDate");
    const collapseEl = document.getElementById("collapseVitals");

    startInput.value = start;
    endInput.value = end;
    endInput.min = start;

    startInput.addEventListener("change", (e) => {
        endInput.min = e.target.value;

        if (endInput.value && endInput.value < e.target.value) {
            endInput.value = "";
        }
    });

    endInput.addEventListener("change", (e) => {
        startInput.max = e.target.value;
    });

    if (!collapseObserverBound && collapseEl) {
        const observer = new MutationObserver(() => {
            if (!collapseEl.classList.contains("hidden")) {
                setTimeout(drawChart, 100);
            }
        });

        observer.observe(collapseEl, {
            attributes: true,
            attributeFilter: ["class"]
        });

        collapseObserverBound = true;
    }

    handleFilter();
});

function handleFilter() {
    const start = document.getElementById("startDate").value;
    const end = document.getElementById("endDate").value;
    const deviceId = document.getElementById("hidden_device_id").value;
    const toggle = document.getElementById('vitalsToggle');
    const statusText = document.getElementById('data-status');
    const spinner = document.getElementById('chart-loading-spinner');

    console.log(start, end);

    if (vitalsChart) {
        vitalsChart.destroy();
        vitalsChart = null;
    }

    toggle.classList.add('pointer-events-none', 'opacity-60');
    statusText.innerText = "資料載入中...";
    statusText.classList.remove('text-green-500', 'text-red-500');
    statusText.classList.add('text-blue-500');
    if (spinner) spinner.style.display = 'block';

    fetch(`/api/deviceDetailObs14days/${deviceId}?start=${start}&end=${end}`)
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
            statusText.classList.remove('text-blue-500', 'text-red-500');
            statusText.classList.add('text-green-500');

            if (spinner) spinner.style.display = 'none';

            // 如果已經展開，就直接重畫
            const collapseEl = document.getElementById("collapseVitals");
            if (collapseEl && !collapseEl.classList.contains("hidden")) {
                drawChart();
            }
        })
        .catch(err => {
            console.error("資料抓取失敗:", err);
            statusText.innerText = "連線逾時";
            statusText.classList.remove('text-blue-500', 'text-green-500');
            statusText.classList.add('text-red-500');
            if (spinner) spinner.style.display = 'none';
        });
}

// 繪圖
function drawChart() {
    console.log("drawChart called");

    document.getElementById('myChartText').innerText = "生理趨勢圖";
    
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
                        text: '生理量測平均數值'
                    }
                }
            }
        }
    });
}