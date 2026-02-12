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
    
    const id = document.getElementById('new_id').value;
    const name = document.getElementById('new_name').value;
    const PraId = document.getElementById('new_PraId').value;
    const checkboxes = document.querySelectorAll('input[name="new_dataType"]:checked');
    // const role = document.getElementById('newUser_role').value;

	const selectedValues = Array.from(checkboxes).map(cb => cb.value);

	// 3. 現在你可以看到具體的結果了
	alert("選中的值有: " + selectedValues.join(", "));

    // // 清除前一次樣式
    // msg.classList.remove('error-message', 'success-message');
    // if (!full_name || !email) {
    //     msg.textContent = '請填寫帳號與密碼！';
    //     msg.classList.add('error-message');
    //     return;
    // }

    // const response = await fetch('/register', {
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify({ full_name, email, organization, role, fhir_practitioner_id })
    // });

    // const result = await response.json();
    // if (result.success) {
    //     msg.textContent = result.message;
    //     msg.classList.add('success-message');
    //     setTimeout(() => {
    //         location.reload();
    //     }, 500);
    // } else {
    //     msg.textContent = result.message;
    //     msg.classList.add('error-message');
    // }
});
