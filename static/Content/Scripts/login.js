
const form = document.getElementById('loginForm');
const msg = document.getElementById('message');

form.addEventListener('submit', async function (e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    msg.classList.remove('error-message', 'success-message');
    if (!email || !password) {
        msg.textContent = '請填寫帳號與密碼！';
        msg.classList.add('error-message');
        return;
    }

    const response = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });

    const result = await response.json();
    if (result.success) {
        msg.textContent = '登入成功，正在跳轉...';
        msg.classList.add('success-message');
        setTimeout(() => {
            window.location.href = result.redirect;
        }, 500);
    } else {
        msg.textContent = result.message;
        msg.classList.add('error-message');
    }
});
document.addEventListener("DOMContentLoaded", function () {
    const reason = document.getElementById("logoutReason")?.dataset.reason;

    const messages = {
        timeout: "您已超過 30 分鐘未操作，系統已自動登出",
        login_elsewhere: "此帳號已在其他裝置登入，您已被登出",
        password_reset: "您的密碼已被重設，請重新登入",
        permission_changed: "您的帳號權限已被修改，請重新登入",
        disabled: "您的帳號已停權，請聯絡管理員",
        deleted: "您的帳號已被刪除，請聯絡管理員",
        invalid: "登入狀態已失效，請重新登入"
    };

    if (reason && messages[reason]) {
        alert(messages[reason]);
    }
});