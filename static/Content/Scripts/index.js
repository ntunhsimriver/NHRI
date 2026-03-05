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
              text: 'Value'
            },
            suggestedMin: 0,
            suggestedMax: maxValue + 20
          }
        }
      }
    });
}

drawChart();