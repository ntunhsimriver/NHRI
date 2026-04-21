document.querySelectorAll('.project-btn').forEach(btn => {
    btn.addEventListener('click', function () {
        alert(this.dataset.url);
        window.location.href = this.dataset.url;
    });
});
