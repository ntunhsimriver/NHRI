document.addEventListener("DOMContentLoaded", function () {
  const toggleButtons = document.querySelectorAll(".toggle-password");

  toggleButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      const targetId = button.getAttribute("data-target");
      const input = document.getElementById(targetId);


      if (!input) return;

      if (input.type === "password") {
        input.type = "text";
        button.innerHTML = '<i class="bi bi-eye-slash"></i>';
        button.setAttribute("aria-label", "隱藏密碼");
      } else {
        input.type = "password";
        button.innerHTML = '<i class="bi bi-eye"></i>';
        button.setAttribute("aria-label", "顯示密碼");
      }
    });
  });
});

// 先宣告
const form = document.getElementById('changepwForm');
const msg = document.getElementById('message');

form.addEventListener('submit', async function (e) {
    e.preventDefault();
    
    const old_password = document.getElementById('old_password').value;
    const new_password = document.getElementById('new_password').value;

    const regex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d]).+$/;

    if (!regex.test(new_password)) {
      // alert("密碼需包含：大小寫英文、數字、符號");
        msg.textContent = "密碼需包含：大小寫英文、數字、符號";
        msg.classList.add('error-message');
        return;
    }

    // 清除前一次樣式
    msg.classList.remove('error-message', 'success-message');
    if (!old_password || !new_password) {
        msg.textContent = '請填寫帳號與密碼！';
        msg.classList.add('error-message');
        return;
    }

    const response = await fetch('/api/change_password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_password, new_password })
    });

    const result = await response.json();
    if (result.success) {
        msg.textContent = '密碼修改成功，請重新登入!';
        msg.classList.add('success-message');
        setTimeout(() => {
            window.location.href = result.redirect;
        }, 500);
    } else {
        msg.textContent = result.message;
        msg.classList.add('error-message');
    }
});
