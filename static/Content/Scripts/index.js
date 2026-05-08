let myChart = null;

const maxValue = Math.max(...SERVER_DATA.months_data);
const minValue = Math.min(...SERVER_DATA.months_data);

// 將原本的繪圖邏輯封裝成函式
function drawChart() {
    const ctx = document.getElementById('myChart-SubjectIn');
    if (!ctx) return;

    // 如果已經有圖表，先銷毀防止重複疊加
    if (myChart) {
        myChart.destroy();
    }

    // 這裡放你原本定義的 data 與 config
    const data = {
        labels: SERVER_DATA.months,
        datasets: [
            {
                label: '收案人數',
                data: SERVER_DATA.months_data,
                borderColor: '#3b82f6',
                fill: false,
                cubicInterpolationMode: 'monotone',
                tension: 0.4
            }
        ]
    };

    myChart = new Chart(ctx, {
        type: 'line',
        data: data,
        options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'nearest',   // 吸附最近的點
          axis: 'x',         // 只看 X 軸距離（Day）
          intersect: false   // 不用滑到點上
        },

        plugins: {
          title: {
            display: false,
            text: '收案人數統計'
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
              text: '累積收案人數'
            },
            suggestedMin: 0,
            suggestedMax: maxValue + 20
          }
        }
      }
    });
}

drawChart();



const resourceTypes = ["Encounter", "Observation", "MedicationRequest", "Procedure", "Condition", "DiagnosticReport", "Consent", "Device"];

// 模擬數據，實際請替換為你的 API 資料
const mockData = [12, 45, 7, 15, 22, 5, 2, 8];

function CountDataChart() {
    const canvas = document.getElementById('CountDataChart');
    if (!canvas) return; // 安全檢查

    const ctx = canvas.getContext('2d');
    
    // 如果圖表實例已存在，先銷毀它，避免重複渲染 bug
    if (window.myChart instanceof Chart) {
        window.myChart.destroy();
    }

    // 定義 8 種不同的柔和、現代感醫療風格顏色
    const fhirPalette = [
        '#60a5fa', // Blue (Encounter)
        '#16a34a', // Green (Observation)
        '#fb923c', // Orange (MedicationRequest)
        '#a78bfa', // Violet (Procedure)
        '#f87171', // Red (Condition)
        '#22d3ee', // Cyan (DiagnosticReport)
        '#fbbf24', // Amber (Consent)
        '#94a3b8'  // Slate (Device)
    ];

    const rawMax = Math.max(...SERVER_DATA.CountData_data);
    const chartMax = Math.ceil(rawMax <= 0 ? 10 : rawMax * 1.2); // 如果沒數據，預設 max 為 10

    window.myChart = new Chart(ctx, {
        type: 'bar', // 垂直直條圖
        data: {
            labels: SERVER_DATA.CountData_list,
            datasets: [{
                // label: '今日匯入數量', // 隱藏 legend 了，這裡可寫可不寫
                data: SERVER_DATA.CountData_data, // 這裡之後記得換成 SERVER_DATA 的值
                backgroundColor: fhirPalette, // 賦予不同的顏色陣列
                borderRadius: 6, // 頂部圓角，更顯現代感
                barPercentage: 0.7, // 調整直條寬度佔比 (0-1)，讓柱子之間有呼吸空間
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, // 搭配 CSS fixed height 防止無限拉長
            plugins: {
                legend: {
                    display: false // 隱藏上方的數據標籤，因為顏色已經區分了
                },
                tooltip: {
                    // 優化滑鼠移上去時的提示框
                    backgroundColor: 'rgba(15, 23, 42, 0.9)', // slate-900
                    padding: 12,
                    cornerRadius: 8,
                    titleFont: { size: 14, weight: 'bold' },
                    bodyFont: { size: 13 },
                    callbacks: {
                        label: function(context) {
                            return ` 匯入數量: ${context.parsed.y}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { 
                        display: false // 隱藏 X 軸網格線，畫面更乾淨
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45,
                        color: '#64748b', // slate-500
                        font: { size: 12 } 
                    }
                },
                y: {
                    beginAtZero: true,
                    border: {
                        display: false // 隱藏 Y 軸邊框線
                    },
                    grid: {
                        color: '#f1f5f9' // 使用輕微的灰色網格線 (slate-100)
                    },
                    ticks: {
                        color: '#64748b', // slate-500
                        stepSize: 10 // 根據數據量調整刻度間隔
                    }
                }
            }
        }
    });
}
CountDataChart();


document.querySelectorAll(".btn-update-resource-count").forEach(button => {
    button.addEventListener("click", async function () {
        const study_id = this.getAttribute("data-bs-study");

        this.disabled = true;
        this.innerHTML = '<i class="bi bi-arrow-repeat text-sm"></i>';

        try {
            const response = await fetch("/api/update-resource-count", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    study_id: study_id
                })
            });

            const result = await response.json();

            if (result.success) {
                alert("已更新完成!!");
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
            this.disabled = false;
            this.innerHTML = '<i class="bi bi-arrow-clockwise text-sm"></i>';
        }
    });
});


