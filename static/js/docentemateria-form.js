/* DocenteMateria form enhancements */
document.addEventListener('DOMContentLoaded', function () {
  if (typeof TomSelect === 'undefined') return;

  var selects = ['#id_asignatura', '#id_grado', '#id_seccion', '#id_docente', '#id_anio_escolar'];
  selects.forEach(function (sel) {
    var el = document.querySelector(sel);
    if (el) {
      new TomSelect(el, {
        maxOptions: null,
        render: {
          option: function (data, escape) {
            var sub = data.extra_sub ? '<div class="text-xs text-gray-500">' + escape(data.extra_sub) + '</div>' : '';
            return '<div class="py-1 px-2"><div class="font-medium">' + escape(data.text) + '</div>' + sub + '</div>';
          },
          item: function (data, escape) {
            var sub = data.extra_sub ? ' <span class="text-xs text-gray-500">(' + escape(data.extra_sub) + ')</span>' : '';
            return '<div>' + escape(data.text) + sub + '</div>';
          }
        }
      });
    }
  });

  /* Auto-submit on grado change */
  var grado = document.querySelector('#id_grado');
  if (grado) {
    grado.addEventListener('change', function () { this.form.submit(); });
  }

  /* Live summary */
  var resumen = document.getElementById('resumen-seleccion');
  if (!resumen) return;

  function actualizarResumen() {
    var vals = [];
    selects.forEach(function (sel) {
      var el = document.querySelector(sel);
      if (el && el.value) {
        var txt = el.options[el.selectedIndex] ? el.options[el.selectedIndex].text : el.value;
        vals.push(txt);
      }
    });
    resumen.textContent = vals.length ? vals.join(' → ') : 'Seleccione los campos';
  }

  selects.forEach(function (sel) {
    var el = document.querySelector(sel);
    if (el) el.addEventListener('change', actualizarResumen);
  });

  actualizarResumen();
});
