
// 新增使用者
var ModaladdDevice = document.getElementById('Modal_addDevice');
// 等等要關閉這個彈跳視窗用的
var ModalInstance = bootstrap.Modal.getOrCreateInstance(ModaladdDevice);

ModaladdDevice.addEventListener('show.bs.modal', function (event) {
    var button = event.relatedTarget; // 取得被點擊的按鈕
    var input_data = button.getAttribute('data-bs-value')
    var data = JSON.parse(input_data);

    var modalTitle = document.getElementById('Modal_addDevice_title');
    var Model_id = document.getElementById('DeviceId');
    if (data.id) {
      if (modalTitle) modalTitle.textContent = '更新設備';
      Model_id.readOnly = true;   // 編輯 → 鎖住

    } 
    // 沒資料 => 新增模式
    else {
      if (modalTitle) modalTitle.textContent = '新增設備';
      Model_id.readOnly = false;   // 編輯 → 鎖住

    }

    // 1. 處理設備型號 (Select)
    var modelEl = document.getElementById('DeviceModel');
    if (modelEl) modelEl.value = data.model;

    // 2. 處理設備序號 (Input)
    var idEl = document.getElementById('DeviceId');
    if (idEl) idEl.value = data.id;

    // 3. 處理狀態 (Select)
    var statusEl = document.getElementById('DeviceStatus');
    if (statusEl) statusEl.value = data.status;

    // 4. 處理個案 (如果有資料的話)
    var patEl = document.getElementById('PatId');
    if (patEl) patEl.value = data.pat_id || ""; // 防止出現 "null" 字樣



});


// 當 Modal 關閉時自動重置表單
document.getElementById('Modal_addDevice').addEventListener('hidden.bs.modal', function () {
    form.reset();
    msg.textContent = '';
    msg.className = 'message';
});


// 先宣告
const form = document.getElementById('registerForm');
const msg = document.getElementById('message');

form.addEventListener('submit', async function (e) {
    e.preventDefault();
    
    const id = document.getElementById('DeviceId').value;
    const status = document.getElementById('DeviceStatus').value;
    const model = document.getElementById('DeviceModel').value;
    const pat_id = document.getElementById('PatId').value;

    // 清除前一次樣式
    msg.classList.remove('error-message', 'success-message');
    

    const response = await fetch('/api/addDevice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, status, model, pat_id })
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
