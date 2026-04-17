document.querySelectorAll('.project-btn').forEach(btn => {
    btn.addEventListener('click', function () {
        window.location.href = this.dataset.url;
    });
});
