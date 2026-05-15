let myChart = null;

const maxValue = Math.max(...SERVER_DATA.months_data);
const minValue = Math.min(...SERVER_DATA.months_data);


function drawChart() {
    const ctx = document.getElementById('myChart-SubjectIn');
    if (!ctx) return;

    
    if (myChart) {
        myChart.destroy();
    }

    
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
          mode: 'nearest',   
          axis: 'x',         
          intersect: false   
        },

        plugins: {
          title: {
            display: false,
            text: '收案人數統計'
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


const mockData = [12, 45, 7, 15, 22, 5, 2, 8];

function CountDataChart() {
    const canvas = document.getElementById('CountDataChart');
    if (!canvas) return; 

    const ctx = canvas.getContext('2d');
    
    
    if (window.myChart instanceof Chart) {
        window.myChart.destroy();
    }

    
    const fhirPalette = [
        '#60a5fa', 
        '#16a34a', 
        '#fb923c', 
        '#a78bfa', 
        '#f87171', 
        '#22d3ee', 
        '#fbbf24', 
        '#94a3b8'  
    ];

    const rawMax = Math.max(...SERVER_DATA.CountData_data);
    const chartMax = Math.ceil(rawMax <= 0 ? 10 : rawMax * 1.2); 

    window.myChart = new Chart(ctx, {
        type: 'bar', 
        data: {
            labels: SERVER_DATA.CountData_list,
            datasets: [{
                
                data: SERVER_DATA.CountData_data, 
                backgroundColor: fhirPalette, 
                borderRadius: 6, 
                barPercentage: 0.7, 
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, 
            plugins: {
                legend: {
                    display: false 
                },
                tooltip: {
                    
                    backgroundColor: 'rgba(15, 23, 42, 0.9)', 
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
                        display: false 
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45,
                        color: '#64748b', 
                        font: { size: 12 } 
                    }
                },
                y: {
                    beginAtZero: true,
                    border: {
                        display: false 
                    },
                    grid: {
                        color: '#f1f5f9' 
                    },
                    ticks: {
                        color: '#64748b', 
                        stepSize: 10 
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


