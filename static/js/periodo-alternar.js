/* Periodo alternar (abrir/cerrar) btn handler */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.btn-alternar').forEach(function (btn) {
    btn.addEventListener('click', function () {
      fetch(btn.dataset.url, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
      })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.success) {
            location.reload();
          } else {
            Swal.fire('Error', data.error || 'No se pudo cambiar el estado', 'error');
          }
        });
    });
  });
});
