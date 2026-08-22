/* Asistencia filtros: grado → seccion sync + radio styling */
document.addEventListener('DOMContentLoaded', function () {
  var gradoSel = document.getElementById('id_grado');
  var seccionSel = document.getElementById('id_seccion');
  if (!gradoSel || !seccionSel) return;

  var todasSecciones = [];
  Array.from(seccionSel.options).forEach(function (opt) {
    if (opt.value) todasSecciones.push({ value: opt.value, text: opt.text, grado: opt.dataset.grado || '' });
  });

  function sincronizarSecciones() {
    var gradoId = gradoSel.value;
    seccionSel.innerHTML = '<option value="">Todas</option>';
    todasSecciones.forEach(function (s) {
      if (!gradoId || s.grado === gradoId) {
        var opt = document.createElement('option');
        opt.value = s.value;
        opt.textContent = s.text;
        seccionSel.appendChild(opt);
      }
    });
    if (typeof TomSelect !== 'undefined' && seccionSel.tomselect) {
      seccionSel.tomselect.sync();
    }
  }

  gradoSel.addEventListener('change', sincronizarSecciones);
  sincronizarSecciones();

  /* Radio active styling */
  document.querySelectorAll('.asistencia-radio').forEach(function (radio) {
    radio.addEventListener('change', function () {
      document.querySelectorAll('.asistencia-option').forEach(function (opt) {
        opt.classList.remove('ring-2', 'ring-blue-500', 'bg-blue-50');
      });
      if (this.checked) {
        this.closest('.asistencia-option').classList.add('ring-2', 'ring-blue-500', 'bg-blue-50');
      }
    });
  });
});
