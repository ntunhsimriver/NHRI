    $(document).ready(function (e) {
        $("#status").removeClass("custom-visibility-visible")
        $("#preloader").removeClass("custom-visibility-visible")
        $("#status").addClass("custom-visibility-hidden");
        $("#preloader").addClass("custom-visibility-hidden");
    });

// 寫在這裡不知道為啥沒用
document.addEventListener("click", function(e) {
  const btn = e.target.closest(".tw-collapse-toggle");
  if (!btn) return;


  const target = document.querySelector(btn.dataset.target);
  alert(target);
  if (!target) return;

  target.classList.toggle("hidden");
});