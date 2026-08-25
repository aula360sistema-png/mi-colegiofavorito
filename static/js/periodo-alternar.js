/* Periodo alternar (abrir/cerrar) btn handler.
   Al cerrar con notas pendientes, la API responde 400 con el detalle
   y ofrece forzar (solo si el usuario puede: respuesta.puede_forzar). */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.btn-alternar').forEach(function (btn) {
    btn.addEventListener('click', function () {
      fetch(btn.dataset.url, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
      })
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, data: data };
          });
        })
        .then(function (resultado) {
          var data = resultado.data;
          if (data.success) {
            location.reload();
            return;
          }

          if (data.bloqueado && data.pendientes && data.pendientes.length) {
            var filas = data.pendientes.slice(0, 8).map(function (p) {
              return '<tr>' +
                '<td style="padding:4px 10px">' + p.asignatura + '</td>' +
                '<td style="padding:4px 10px;white-space:nowrap">' + p.grado + ' · ' + p.seccion + '</td>' +
                '<td style="padding:4px 10px;text-align:center"><b>' + p.faltantes + '</b></td>' +
                '</tr>';
            }).join('');
            if (data.pendientes.length > 8) {
              filas += '<tr><td colspan="3" style="padding:4px 10px;color:#92400e">… y ' +
                (data.pendientes.length - 8) + ' asignatura(s) más</td></tr>';
            }

            var html =
              '<p style="text-align:left;margin-bottom:8px">' + data.error + '</p>' +
              '<table style="margin:0 auto;border-collapse:collapse;font-size:13px;width:100%">' +
              '<thead><tr style="color:#92400e">' +
              '<th style="text-align:left;padding:4px 10px">Asignatura</th>' +
              '<th style="padding:4px 10px">Grado-Sección</th>' +
              '<th style="padding:4px 10px">Sin nota</th>' +
              '</tr></thead><tbody>' + filas + '</tbody></table>';

            if (!data.puede_forzar) {
              Swal.fire({
                icon: 'warning',
                title: 'Notas pendientes',
                html: html,
                confirmButtonText: 'Entendido',
                confirmButtonColor: '#d33',
              });
              return;
            }

            Swal.fire({
              icon: 'warning',
              title: 'Notas pendientes',
              html: html,
              showCancelButton: true,
              confirmButtonText: 'Forzar con 0 automáticos',
              confirmButtonColor: '#d97706',
              cancelButtonText: 'Cancelar',
              focusCancel: true,
            }).then(function (r) {
              if (!r.isConfirmed) return;
              fetch(btn.dataset.url, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
                body: new URLSearchParams({ forzar: '1' }),
              })
                .then(function (res2) { return res2.json(); })
                .then(function (data2) {
                  if (data2.success) {
                    location.reload();
                  } else {
                    Swal.fire('Error', data2.error || 'No se pudo cerrar', 'error');
                  }
                });
            });
            return;
          }

          Swal.fire('Error', data.error || 'No se pudo cambiar el estado', 'error');
        });
    });
  });
});
