
// 新增使用者
var ModaladdUser = document.getElementById('Modal_addUser');
// 等等要關閉這個彈跳視窗用的
var ModalInstance = bootstrap.Modal.getOrCreateInstance(ModaladdUser);

ModaladdUser.addEventListener('show.bs.modal', function (event) {
    var button = event.relatedTarget; // 取得被點擊的按鈕
    var input_data = button.getAttribute('data-bs-value')
    var data = JSON.parse(input_data);
    if (input_data){
        document.getElementById('Modal_addUser_title').textContent = '修改使用者';
    }else{
        document.getElementById('Modal_addUser_title').textContent = '新增使用者';
    };

    var modelfull_name = document.getElementById('newUser_name');
    if (modelfull_name) modelfull_name.value = data.full_name;

    var modelemail = document.getElementById('newUser_email');
    if (modelemail) modelemail.value = data.email;

    var modelorg = document.getElementById('newUser_org');
    if (modelorg) modelorg.value = data.org;

    var modelpra_id = document.getElementById('newUser_PraId');
    if (modelpra_id) modelpra_id.value = data.pra_id;

    var modelroleName = document.getElementById('newUser_role');
    if (modelroleName) modelroleName.value = data.roleName;

    var modelroleActive = document.getElementById('newUser_active');
    if (modelroleActive) modelroleActive.value = data.status;

});


// 當 Modal 關閉時自動重置表單
document.getElementById('Modal_addUser').addEventListener('hidden.bs.modal', function () {
    form.reset();
    msg.textContent = '';
    msg.className = 'message';
    if (modalEl.contains(document.activeElement)) {
        document.activeElement.blur();
      }

});


// 先宣告
const form = document.getElementById('registerForm');
const msg = document.getElementById('message');

form.addEventListener('submit', async function (e) {
    e.preventDefault();
    
    const full_name = document.getElementById('newUser_name').value;
    const email = document.getElementById('newUser_email').value;
    const organization = document.getElementById('newUser_org').value;
    const fhir_practitioner_id = document.getElementById('newUser_PraId').value;
    const role = document.getElementById('newUser_role').value;
    const active = document.getElementById('newUser_active').value;

    const type =
        document.getElementById('Modal_addUser_title').textContent === '新增使用者'
        ? 'new'
        : 'update';

    // 清除前一次樣式
    msg.classList.remove('error-message', 'success-message');
    if (!full_name || !email) {
        msg.textContent = '請填寫帳號與密碼！';
        msg.classList.add('error-message');
        return;
    }

    const response = await fetch('/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name, email, organization, role, active, fhir_practitioner_id, type })
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


document.addEventListener('DOMContentLoaded', function() {

    const statusSelect = document.getElementById('statusSelect');
    const searchInput = document.getElementById('searchInput');
    const caseRows = document.querySelectorAll('.case-row');

    function filterRows() {
        const searchText = searchInput.value.toLowerCase();

        caseRows.forEach(row => {
            const name = row.getAttribute('data-user-name').toLowerCase();
            const email = row.getAttribute('data-user-email').toLowerCase();

            const matchSearch =
                name.includes(searchText)|| 
                email.includes(searchText);

            if (matchSearch) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }

        });
    }


    if (searchInput) {
        searchInput.addEventListener('input', filterRows);
    }


});
