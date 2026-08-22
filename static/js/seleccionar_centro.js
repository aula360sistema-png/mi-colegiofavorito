document.addEventListener('DOMContentLoaded', function () {
  var busqueda = document.getElementById('buscar-centro');
  if (!busqueda) return;
  busqueda.addEventListener('input', function () {
    var termino = busqueda.value.trim().toLowerCase();
    var visibles = 0;
    document.querySelectorAll('.centro-item').forEach(function (item) {
      var nombre = item.querySelector('.centro-nombre').textContent.toLowerCase();
      var coincide = termino === '' || nombre.includes(termino);
      item.classList.toggle('hidden', !coincide);
      if (coincide) visibles++;
    });
    document.getElementById('sin-resultados').classList.toggle('hidden', visibles > 0);
  });
});
