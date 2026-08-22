/* Copy button text reset */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-copy-reset]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var original = btn.dataset.copyReset || 'Copiar';
      setTimeout(function () { btn.textContent = original; }, 2000);
    });
  });
});
