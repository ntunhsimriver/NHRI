
function goToStep3(filename) {
    // 1. 隱藏步驟 2，顯示步驟 3
    document.getElementById('step-2-content').classList.add('hidden');
    document.getElementById('step-3-content').classList.remove('hidden');

    // 2. 更新上方進度條 (讓 3 號圈圈變藍色)
    const circle3 = document.getElementById('step-circle-3');
    circle3.classList.remove('bg-slate-200', 'text-slate-500');
    circle3.classList.add('bg-blue-600', 'text-white');
    
    // 3. 更新 2 號與 3 號之間的連接線
    document.getElementById('step-line-2').classList.remove('bg-slate-200');
    document.getElementById('step-line-2').classList.add('bg-blue-600');
}

function goToStep2(type) {
    // 1. 切換內容顯示
    document.getElementById('step-1-content').classList.add('hidden');
    document.getElementById('step-2-content').classList.remove('hidden');

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
    else if (type === 'Excel') {
        hintElement.innerText = ".csv,.xlsx";
        infoElement.innerText = "格式範例";
        fileInput.accept = ".csv,.xlsx"; // 其他來源收表格檔
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


function handleUpload() {
    const fileInput = document.getElementById('file-upload');
    const fileType = document.getElementById('type-hidden').value;
    alert(fileType);
    const file = fileInput.files[0];

    // 1. 基本檢查
    if (!file) {
        alert("請先選擇或拖曳檔案！");
        return;
    }

    // 2. 建立 FormData 物件（這是 AJAX 傳檔案的關鍵）
    const formData = new FormData();
    formData.append('file', file); // 'file' 要對應 Flask 裡的 request.files['file']

    // 3. 建立傳統的 AJAX 請求 (XMLHttpRequest)
    const xhr = new XMLHttpRequest();

    if (fileType === 'FHIR'){
        // 設定請求目標
        xhr.open('POST', '/api/uploadFHIR', true);

        // 監聽回傳結果
        xhr.onload = function () {
            if (xhr.status === 200) {
                // 解析 Flask 回傳的 JSON
                const response = JSON.parse(xhr.responseText);
                if (response.success) {
                    console.log("上傳成功:", response.filename);
                    // 順利上傳後，執行切換到步驟 3 的函式
                    goToStep3(); 
                } else {
                    alert("伺服器錯誤: " + response.error);
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

// 上傳檔案的那個框框 到這裡
