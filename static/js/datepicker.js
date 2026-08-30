/* ============================================================
   datepicker.js — Calendario de fechas sin dependencias
   Oculta el input nativo (input.js-datepicker) y muestra un
   botón que abre un calendario. Guarda el valor en ISO (YYYY-MM-DD).
   Respeta los atributos min/max del input; si existe max, las
   fechas posteriores quedan deshabilitadas.
   ============================================================ */
(function () {
  'use strict';
  if (window.__datepickerInit) return;
  window.__datepickerInit = true;

  var DIAS = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa', 'Do'];
  var MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

  function desdeISO(v) {
    if (!v) return null;
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(v);
    return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null;
  }

  function aISO(f) {
    var mm = String(f.getMonth() + 1).padStart(2, '0');
    var dd = String(f.getDate()).padStart(2, '0');
    return f.getFullYear() + '-' + mm + '-' + dd;
  }

  function mismoDia(a, b) {
    return a && b &&
      a.getFullYear() === b.getFullYear() &&
      a.getMonth() === b.getMonth() &&
      a.getDate() === b.getDate();
  }

  function textoBonito(f) {
    if (!f) return '';
    return f.toLocaleDateString('es-DO', { day: 'numeric', month: 'long', year: 'numeric' });
  }

  function crear(entrada) {
    var valor = desdeISO(entrada.value);
    var vista = valor ? new Date(valor.getFullYear(), valor.getMonth(), 1) : new Date();
    var min = desdeISO(entrada.getAttribute('min')) || null;
    var max = desdeISO(entrada.getAttribute('max')) || null;

    entrada.classList.add('dp-hidden');

    var envoltura = document.createElement('div');
    envoltura.className = 'dp-envoltura';
    entrada.parentNode.insertBefore(envoltura, entrada);
    envoltura.appendChild(entrada);

    var boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'dp-boton';
    boton.setAttribute('aria-haspopup', 'dialog');

    var texto = document.createElement('span');
    texto.className = 'dp-boton-texto';
    texto.dataset.placeholder = 'Seleccione una fecha';
    texto.textContent = textoBonito(valor);

    var icono = document.createElement('i');
    icono.className = 'fas fa-calendar-days dp-boton-icono';

    boton.appendChild(texto);
    boton.appendChild(icono);
    envoltura.appendChild(boton);

    var pop = document.createElement('div');
    pop.className = 'dp-pop';
    pop.setAttribute('role', 'dialog');
    pop.setAttribute('aria-label', 'Calendario');
    pop.hidden = true;

    function navBtn(iconoClase, fn) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'dp-nav';
      var i = document.createElement('i');
      i.className = 'fas ' + iconoClase;
      b.appendChild(i);
      b.addEventListener('click', function (e) { e.stopPropagation(); fn(); });
      return b;
    }

    var cabecera = document.createElement('div');
    cabecera.className = 'dp-pop-cab';
    var titulo = document.createElement('div');
    titulo.className = 'dp-pop-titulo';
    cabecera.appendChild(navBtn('fa-angles-left', function () {
      vista = new Date(vista.getFullYear() - 1, vista.getMonth(), 1);
      pintar();
    }));
    cabecera.appendChild(navBtn('fa-chevron-left', function () {
      vista = new Date(vista.getFullYear(), vista.getMonth() - 1, 1);
      pintar();
    }));
    cabecera.appendChild(titulo);
    cabecera.appendChild(navBtn('fa-chevron-right', function () {
      vista = new Date(vista.getFullYear(), vista.getMonth() + 1, 1);
      pintar();
    }));
    cabecera.appendChild(navBtn('fa-angles-right', function () {
      vista = new Date(vista.getFullYear() + 1, vista.getMonth(), 1);
      pintar();
    }));
    pop.appendChild(cabecera);

    var semana = document.createElement('div');
    semana.className = 'dp-semana';
    DIAS.forEach(function (d) {
      var s = document.createElement('span');
      s.className = 'dp-dia-semana';
      s.textContent = d;
      semana.appendChild(s);
    });
    pop.appendChild(semana);

    var rejilla = document.createElement('div');
    rejilla.className = 'dp-rejilla';
    pop.appendChild(rejilla);

    var pie = document.createElement('div');
    pie.className = 'dp-pie';
    var hoyBtn = document.createElement('button');
    hoyBtn.type = 'button';
    hoyBtn.className = 'dp-pie-btn dp-pie-hoy';
    hoyBtn.textContent = 'Hoy';
    var limpBtn = document.createElement('button');
    limpBtn.type = 'button';
    limpBtn.className = 'dp-pie-btn dp-pie-limpiar';
    limpBtn.textContent = 'Limpiar';
    pie.appendChild(hoyBtn);
    pie.appendChild(limpBtn);
    pop.appendChild(pie);

    document.body.appendChild(pop);

    function pintar() {
      var anio = vista.getFullYear();
      var mes = vista.getMonth();
      titulo.textContent = MESES[mes] + ' ' + anio;

      var primero = new Date(anio, mes, 1);
      var inicio = (primero.getDay() + 6) % 7;
      var diasEnMes = new Date(anio, mes + 1, 0).getDate();
      var hoy = new Date();

      rejilla.textContent = '';

      var i, v;
      for (i = 0; i < inicio; i++) {
        v = document.createElement('span');
        v.className = 'dp-vacio';
        rejilla.appendChild(v);
      }

      var d, fecha;
      for (d = 1; d <= diasEnMes; d++) {
        fecha = new Date(anio, mes, d);
        (function (dia) {
          var b = document.createElement('button');
          b.type = 'button';
          b.className = 'dp-dia';
          b.textContent = dia.getDate();
          b.setAttribute('aria-label', textoBonito(dia));
          if (mismoDia(dia, valor)) b.classList.add('dp-dia-seleccion');
          if (mismoDia(dia, hoy)) b.classList.add('dp-dia-hoy');
          if ((min && dia.getTime() < min.getTime()) || (max && dia.getTime() > max.getTime())) {
            b.classList.add('dp-dia-deshab');
            b.disabled = true;
          }
          b.addEventListener('click', function () { elegir(dia); });
          rejilla.appendChild(b);
        })(fecha);
      }
    }

    function posicionar() {
      var r = boton.getBoundingClientRect();
      var ancho = pop.offsetWidth || 292;
      var alto = pop.offsetHeight || 330;
      var izquierda = window.scrollX + Math.max(8, Math.min(r.left, document.documentElement.clientWidth - ancho - 8));
      var arriba = window.scrollY + r.bottom + 6;
      if (arriba + alto > window.scrollY + document.documentElement.clientHeight - 8) {
        arriba = window.scrollY + r.top - alto - 6;
      }
      pop.style.left = izquierda + 'px';
      pop.style.top = Math.max(window.scrollY + 8, arriba) + 'px';
    }

    function abrir() {
      pintar();
      pop.hidden = false;
      posicionar();
    }

    function cerrar() {
      pop.hidden = true;
    }

    function elegir(fecha) {
      valor = fecha;
      vista = new Date(fecha.getFullYear(), fecha.getMonth(), 1);
      entrada.value = aISO(fecha);
      texto.textContent = textoBonito(fecha);
      cerrar();
    }

    boton.addEventListener('click', function (e) {
      e.stopPropagation();
      if (pop.hidden) abrir();
      else cerrar();
    });

    hoyBtn.addEventListener('click', function () { elegir(new Date()); });
    limpBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      entrada.value = '';
      texto.textContent = '';
      valor = null;
      cerrar();
    });

    document.addEventListener('click', function (e) {
      if (!pop.hidden && !pop.contains(e.target) && !envoltura.contains(e.target)) cerrar();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !pop.hidden) cerrar();
    });
    window.addEventListener('scroll', function () { cerrar(); }, true);
    window.addEventListener('resize', function () { cerrar(); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('input.js-datepicker').forEach(crear);
  });
})();