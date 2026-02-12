// 這個是為了保持，我在哪個分頁底下，那個sidenav就要有選取框框
document.addEventListener("DOMContentLoaded", function() {
    // 1. 取得目前網址的路徑
    const currentPath = window.location.pathname;

    // 2. 找到所有導覽列連結
    const navLinks = document.querySelectorAll('.sidenav-item a');

    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        
        // 3. 如果目前路徑包含這個連結的 href (且 href 不是空的 / )
        if (currentPath.startsWith(href) && href !== '/') {
            link.parentElement.classList.add('active');
        }
    });
});