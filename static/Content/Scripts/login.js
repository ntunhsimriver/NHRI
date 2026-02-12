// 先宣告
const form = document.getElementById('loginForm');
const msg = document.getElementById('message');

form.addEventListener('submit', async function (e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    // 清除前一次樣式
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
