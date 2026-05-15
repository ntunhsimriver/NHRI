
var ModaladdProject = document.getElementById('Modal_addProject');

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
    
    if (data.id || data.name || data.status || data.note || data.dataType) {
      if (modalTitle) modalTitle.textContent = '更新計劃';
      if (submitBtn) submitBtn.textContent = '儲存修改';
      Model_id.readOnly = true;   

    } 
    
    else {
      if (modalTitle) modalTitle.textContent = '新增計畫';
      if (submitBtn) submitBtn.textContent = '建立計畫';
      Model_id.readOnly = false;   

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



document.getElementById('Modal_addProject').addEventListener('hidden.bs.modal', function () {
    form.reset();
    msg.textContent = '';
    msg.className = 'message';
});



const form = document.getElementById('registerForm');
const msg = document.getElementById('message');

form.addEventListener('submit', async function (e) {
    e.preventDefault();
    var idInput = document.getElementById('new_id');
    const ProjectId = idInput.value;
    const value = ProjectId.trim();

    const regex = /^[A-Za-z0-9-]+$/;

    if (!regex.test(value)) {
        e.preventDefault();  
        msg.classList.add('error-message');
        msg.textContent = 'ID 只能包含英文、數字與 -';
        idInput.focus();
        return;
    }
    const ProjectName = document.getElementById('new_name').value;
    const ProjectStatus = document.getElementById('new_status').value;
    const ProjectNote = document.getElementById('new_note').value;
    const checkboxes = document.querySelectorAll('input[name="new_dataType"]:checked');
    

	const dataType = Array.from(checkboxes).map(cb => cb.value).join(',');

    var modalTitle = document.getElementById('Modal_addProject_title').innerText;

    
    var type = idInput.readOnly ? "update" : "new";
    
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


var ModalmemberManage = document.getElementById('Modal_memberManage');

var ModalInstance = bootstrap.Modal.getOrCreateInstance(ModalmemberManage);



const addMemberform = document.getElementById('addMemberForm');
const addMembermsg = document.getElementById('addMember_message');

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

var searchInput = document.getElementById('searchInput');
var container = document.getElementById('item_member');

var allMembers = [];
var selectedIds = new Set();

function renderMembers(keyword = "") {
    container.innerHTML = "";

    keyword = keyword.trim().toLowerCase();

    var filteredMembers = allMembers.filter(item => {
        return (
            String(item.id).toLowerCase().includes(keyword) ||
            String(item.full_name).toLowerCase().includes(keyword) ||
            String(item.email).toLowerCase().includes(keyword)
        );
    });

    filteredMembers.forEach(item => {
        var itemId = String(item.id);

        container.innerHTML += `
            <div>
                <label>
                    <input 
                        type="checkbox"
                        name="assistant_ids"
                        value="${item.id}"
                        ${selectedIds.has(itemId) ? "checked" : ""}
                    >
                    ${item.full_name} (${item.role})
                </label>
            </div>
        `;
    });
}

ModalmemberManage.addEventListener('show.bs.modal', function (event) {
    var button = event.relatedTarget;

    var input_data = button.getAttribute('data-bs-member');
    var proid_data = button.getAttribute('data-bs-ProID');

    var members = JSON.parse(input_data);

    var proidEl = document.getElementById('item_proid');
    if (proidEl) proidEl.value = proid_data;

    allMembers = members;

    selectedIds = new Set(
        allMembers
            .filter(item => item.selected)
            .map(item => String(item.id))
    );

    if (searchInput) {
        searchInput.value = "";
    }

    renderMembers();
});

container.addEventListener("change", function (e) {
    if (e.target.name === "assistant_ids") {
        var id = String(e.target.value);

        if (e.target.checked) {
            selectedIds.add(id);
        } else {
            selectedIds.delete(id);
        }
    }
});

searchInput.addEventListener("input", function () {
    renderMembers(this.value);
});