// 新增使用者
var ModaladdProject = document.getElementById('Modal_addProject');
// 等等要關閉這個彈跳視窗用的
var ModalInstance = bootstrap.Modal.getOrCreateInstance(ModaladdProject);


// ModaladdUser.addEventListener('show.bs.modal', function (event) {
//     var button = event.relatedTarget; // 取得被點擊的按鈕
//     var input_data = button.getAttribute('data-bs-value')
//     var data = JSON.parse(input_data);

//     var modelfull_name = document.getElementById('newUser_name');
//     if (modelfull_name) modelfull_name.value = data.full_name;

//     var modelemail = document.getElementById('newUser_email');
//     if (modelemail) modelemail.value = data.email;

//     var modelorg = document.getElementById('newUser_org');
//     if (modelorg) modelorg.value = data.org;

//     var modelpra_id = document.getElementById('newUser_PraId');
//     if (modelpra_id) modelpra_id.value = data.pra_id;

//     var modelroleName = document.getElementById('newUser_role');
//     if (modelroleName) modelroleName.value = data.roleName;

// });


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
    
    const ProjectId = document.getElementById('new_id').value;
    const ProjectName = document.getElementById('new_name').value;
    const ProjectStatus = document.getElementById('new_status').value;
    const ProjectNote = document.getElementById('new_note').value;
    const checkboxes = document.querySelectorAll('input[name="new_dataType"]:checked');
    // const role = document.getElementById('newUser_role').value;

	const dataType = Array.from(checkboxes).map(cb => cb.value).join(',');


    // 清除前一次樣式
    msg.classList.remove('error-message', 'success-message');

    const response = await fetch('/api/addProject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ProjectId, ProjectName, ProjectStatus, ProjectNote, dataType })
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