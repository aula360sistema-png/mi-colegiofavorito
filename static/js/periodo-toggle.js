/* Periodo open/close toggle */
function togglePeriodo(periodoId, abrir) {
  var accion = abrir ? 'abrir' : 'cerrar';
  Swal.fire({
    title: '¿' + (abrir ? 'Abrir' : 'Cerrar') + ' período?',
    text: 'Se ' + accion + 'á el período escolar.',
    icon: 'question',
    showCancelButton: true,
    confirmButtonText: 'Sí, ' + accion,
    cancelButtonText: 'Cancelar',
  }).then(function (result) {
    if (!result.isConfirmed) return;
    fetch('/academico/api/periodos/' + periodoId + '/alternar/', {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok) {
          Swal.fire({ icon: 'success', title: 'Listo', text: data.mensaje, timer: 1500, showConfirmButton: false });
          setTimeout(function () { location.reload(); }, 1200);
        } else {
          Swal.fire('Error', data.error || 'No se pudo actualizar', 'error');
        }
      })
      .catch(function () { Swal.fire('Error', 'No se pudo conectar con el servidor', 'error'); });
  });
}
