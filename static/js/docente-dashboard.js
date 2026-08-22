/* Docente dashboard greeting */
document.addEventListener('DOMContentLoaded', function () {
  var el = document.getElementById('saludo-fecha');
  if (!el) return;
  var h = new Date().getHours();
  var saludo = h < 12 ? 'Buenos días' : h < 18 ? 'Buenas tardes' : 'Buenas noches';
  var opciones = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
  var fecha = new Date().toLocaleDateString('es-DO', opciones);
  el.innerHTML = '<span class="text-xl font-bold text-white">' + saludo + '</span>' +
    '<br><span class="text-sm text-blue-100">' + fecha.charAt(0).toUpperCase() + fecha.slice(1) + '</span>';
});
