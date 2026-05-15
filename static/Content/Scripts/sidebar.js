
document.addEventListener("DOMContentLoaded", function() {
    
    const currentPath = window.location.pathname;

    
    const navLinks = document.querySelectorAll('.sidenav-item a');

    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        
        
        if (currentPath.startsWith(href) && href !== '/') {
            link.parentElement.classList.add('active');
        }
    });
});