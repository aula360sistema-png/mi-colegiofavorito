/* Campaña form: toggle fields by alcance */
document.addEventListener('DOMContentLoaded', function () {
  var selectAlcance = document.getElementById('id_alcance') || document.getElementById('select-alcance');
  var campoGrado = document.getElementById('campo-grado');
  var campoTutores = document.getElementById('campo-tutores');
  if (!selectAlcance) return;

  function actualizarCampos() {
    var valor = selectAlcance.value;
    if (campoGrado) campoGrado.classList.toggle('hidden', valor !== 'grado');
    if (campoTutores) campoTutores.classList.toggle('hidden', valor !== 'seleccion');
  }

  selectAlcance.addEventListener('change', actualizarCampos);
  actualizarCampos();
});
