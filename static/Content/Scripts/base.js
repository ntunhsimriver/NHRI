document.addEventListener("click", function(e) {
  const btn = e.target.closest(".tw-collapse-toggle");
  if (!btn) return;


  const target = document.querySelector(btn.dataset.target);
  alert(target);
  if (!target) return;

  target.classList.toggle("hidden");
});

document.querySelectorAll('.btn-back').forEach(btn => {
    btn.addEventListener('click', function () {
        history.back();
    });
});

const userMenu = document.getElementById("userMenu");
  const userAvatar = document.getElementById("userAvatar");

  userAvatar.addEventListener("click", function (e) {
    e.stopPropagation();
    userMenu.classList.toggle("active");
  });

  document.addEventListener("click", function () {
    userMenu.classList.remove("active");
  });

document.addEventListener("DOMContentLoaded", function () {
    const projectSelect = document.getElementById("projectSelect");

    if (projectSelect) {
        projectSelect.addEventListener("change", function () {
            const selectedOption = this.options[this.selectedIndex];
            const url = selectedOption.getAttribute("data-url");

            if (url) {
                window.location.href = url;
            }
        });
    }
});