// 新增使用者
var ModaladdProject = document.getElementById('Modal_addProject');
// 等等要關閉這個彈跳視窗用的
var ModalInstance = bootstrap.Modal.getOrCreateInstance(ModaladdProject);


ModaladdProject.addEventListener('show.bs.modal', function (event) {
    var button = event.relatedTarget;
    var input_data = button.getAttribute('data-bs-value');

    var data = {};
    if (input_data) {
      data = JSON.parse(input_data);
    }

    var modalTitle = document.getElementById('Modal_addProject_title');
    var submitBtn = document.getElementById('Modal_addProject_submit');
    var Model_id = document.getElementById('new_id');
    // 有資料 => 更新模式
    if (data.id || data.name || data.status || data.note || data.dataType) {
      if (modalTitle) modalTitle.textContent = '更新計劃';
      if (submitBtn) submitBtn.textContent = '儲存修改';
      Model_id.readOnly = true;   // 編輯 → 鎖住

    } 
    // 沒資料 => 新增模式
    else {
      if (modalTitle) modalTitle.textContent = '新增計畫';
      if (submitBtn) submitBtn.textContent = '建立計畫';
      Model_id.readOnly = false;   // 編輯 → 鎖住

    }

    
    if (Model_id) Model_id.value = data.id || '';

    var Model_name = document.getElementById('new_name');
    if (Model_name) Model_name.value = data.name || '';

    var Model_status = document.getElementById('new_status');
    if (Model_status) Model_status.value = data.status || 'active';
    
    var Model_note = document.getElementById('new_note');
    if (Model_note) Model_note.value = data.note || '';

    const types = data.dataType ? data.dataType.split(",").map(t => t.trim()) : [];

    document.querySelectorAll('input[name="new_dataType"]').forEach(cb => {
      cb.checked = types.includes(cb.value);
    });
});


// 當 Modal 關閉時自動重置表單
document.getElementById('Modal_addProject').addEventListener('hidden.bs.modal', function () {
    form.reset();
    msg.textContent = '';
    msg.className = 'message';
});


// 先宣告
const form = document.getElementById('registerForm');
const msg = document.getElementById('message');

form.addEventListener('submit', async function (e) {
    e.preventDefault();
    var idInput = document.getElementById('new_id');
    const ProjectId = idInput.value;
    const ProjectName = document.getElementById('new_name').value;
    const ProjectStatus = document.getElementById('new_status').value;
    const ProjectNote = document.getElementById('new_note').value;
    const checkboxes = document.querySelectorAll('input[name="new_dataType"]:checked');
    // const role = document.getElementById('newUser_role').value;

	const dataType = Array.from(checkboxes).map(cb => cb.value).join(',');

    var modalTitle = document.getElementById('Modal_addProject_title').innerText;

    
    var type = idInput.readOnly ? "update" : "new";
    // 清除前一次樣式
    msg.classList.remove('error-message', 'success-message');

    const response = await fetch('/api/addProject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ProjectId, ProjectName, ProjectStatus, ProjectNote, dataType, type })
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

// 新增使用者
var ModalmemberManage = document.getElementById('Modal_memberManage');
// 等等要關閉這個彈跳視窗用的
var ModalInstance = bootstrap.Modal.getOrCreateInstance(ModalmemberManage);

ModalmemberManage.addEventListener('show.bs.modal', function (event) {
    var button = event.relatedTarget;

    var input_data = button.getAttribute('data-bs-member');
    var proid_data = button.getAttribute('data-bs-ProID');

    // 解析 JSON（重點）
    var members = JSON.parse(input_data);

    // 設定 hidden input
    var proidEl = document.getElementById('item_proid');
    if (proidEl) proidEl.value = proid_data;

    // 顯示 checkbox 的地方
    var container = document.getElementById('item_member');
    container.innerHTML = "";

    // 動態產生 checkbox
    members.forEach(item => {
        container.innerHTML += `
            <div>
                <label>
                    <input 
                        type="checkbox"
                        name="assistant_ids"
                        value="${item.id}"
                        ${item.selected ? "checked" : ""}
                    >
                    ${item.full_name} (${item.email})
                </label>
            </div>
        `;
    });

});

// 先宣告
const addMemberform = document.getElementById('addMemberForm');
const addMembermsg = document.getElementById('addMember_message');
// 抓選項用的
function getSelectedAssistants() {
    const checkedBoxes = document.querySelectorAll('input[name="assistant_ids"]:checked');
    const selected = Array.from(checkedBoxes).map(cb => cb.value);
    const selectedStr = selected.join(';');
    return selectedStr;
}
addMemberform.addEventListener('submit', async function (e) {
    e.preventDefault();
    const item_member = getSelectedAssistants();
    const item_proid = document.getElementById('item_proid').value;

    // 清除前一次樣式
    msg.classList.remove('error-message', 'success-message');

    const response = await fetch('/api/addMember', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_member, item_proid })
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