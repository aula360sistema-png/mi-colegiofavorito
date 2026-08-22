/* Grado → Asignaturas cascade (ajax) */
document.addEventListener('DOMContentLoaded', function () {
  var gradoSelect = document.getElementById('id_grado');
  var asignaturaSelect = document.getElementById('id_asignatura');
  if (!gradoSelect || !asignaturaSelect) return;

  var URL_AJAX = '/academico/ajax/asignaturas-por-grado/';

  gradoSelect.addEventListener('change', function () {
    var gradoId = this.value;
    asignaturaSelect.innerHTML = '<option value="">Cargando...</option>';

    if (!gradoId) {
      asignaturaSelect.innerHTML = '<option value="">---------</option>';
      return;
    }

    fetch(URL_AJAX + gradoId + '/')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        asignaturaSelect.innerHTML = '<option value="">---------</option>';
        data.forEach(function (item) {
          var opt = document.createElement('option');
          opt.value = item.id;
          opt.textContent = item.nombre;
          asignaturaSelect.appendChild(opt);
        });
      })
      .catch(function () {
        asignaturaSelect.innerHTML = '<option value="">Error al cargar</option>';
      });
  });
});
