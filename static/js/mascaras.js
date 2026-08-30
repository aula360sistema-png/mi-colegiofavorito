/* ============================================================
   mascaras.js — Máscaras de formato de RD
   input[data-mascara="telefono"] -> 000-000-0000
   input[data-mascara="cedula"]   -> 000-0000000-0
   ============================================================ */
(function () {
  'use strict';
  if (window.__mascarasInit) return;
  window.__mascarasInit = true;

  function soloDigitos(v, max) {
    return v.replace(/\D/g, '').slice(0, max);
  }

  function formatearTelefono(v) {
    var s = soloDigitos(v, 10);
    var salida = '';
    if (s.length > 3) { salida = s.slice(0, 3) + '-'; s = s.slice(3); }
    if (s.length > 3) { salida += s.slice(0, 3) + '-'; s = s.slice(3); }
    return salida + s;
  }

  function formatearCedula(v) {
    var s = soloDigitos(v, 11);
    var salida = '';
    if (s.length > 3) { salida = s.slice(0, 3) + '-'; s = s.slice(3); }
    if (s.length > 7) { salida += s.slice(0, 7) + '-'; s = s.slice(7); }
    return salida + s;
  }

  function aplicar(entrada) {
    var fn = entrada.dataset.mascara === 'cedula'
      ? formatearCedula : formatearTelefono;

    if (entrada.value) entrada.value = fn(entrada.value);

    entrada.addEventListener('input', function () {
      var pos = entrada.selectionStart || 0;
      var antes = entrada.value;
      entrada.value = fn(entrada.value);
      if (entrada.value !== antes) {
        var cursor = pos + (entrada.value.length - antes.length);
        try { entrada.setSelectionRange(cursor, cursor); } catch (e) {}
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('input[data-mascara]').forEach(aplicar);
  });
})();