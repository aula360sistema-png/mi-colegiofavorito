/* ============================================================
   shared.js — Funciones compartidas (CSP-safe, sin inline)
   ============================================================ */

/* --- CSRF helper (for fetch POST) --- */
function getCookie(name) {
  for (const cookie of document.cookie.split(';')) {
    const [key, val] = cookie.trim().split('=');
    if (key === name) return decodeURIComponent(val);
  }
  return null;
}

/* --- Filter helpers --- */
function removeFilter(param, resetPage) {
  const url = new URL(window.location.href);
  url.searchParams.delete(param);
  if (resetPage !== false) url.searchParams.delete('page');
  window.location.href = url.toString();
}

function debounce(fn, ms) {
  let t;
  return function () { clearTimeout(t); t = setTimeout(() => fn.apply(this, arguments), ms); };
}

/* --- Tab switching ---
   Soporta dos convenciones de markup:
   A) botones con id="tab-<nombre>" y paneles id="panel-<nombre>" (.tab-content)
   B) botones con data-tab="<nombre>" y paneles id="tab-<nombre>" (.tab-panel)
*/
function switchTab(nombre) {
  document.querySelectorAll('.tab-content, .tab-panel').forEach(function (el) {
    el.classList.add('hidden');
  });

  var panel = document.getElementById('panel-' + nombre) ||
              document.getElementById('tab-' + nombre);
  if (!panel) return;
  panel.classList.remove('hidden');

  var activo = null;
  document.querySelectorAll('.tab-btn').forEach(function (b) {
    if (b.id === 'tab-' + nombre || b.dataset.tab === nombre) activo = b;
    b.classList.remove('border-blue-600', 'text-blue-600', 'text-blue-700');
    b.classList.add('border-transparent', 'text-gray-500');
  });

  if (activo) {
    activo.classList.remove('border-transparent', 'text-gray-500');
    activo.classList.add('border-blue-600', 'text-blue-700');
  }
}

/* --- Accordion / Acordeon toggle --- */
function toggleAcordeon(btn) {
  var content = btn.nextElementSibling;
  var icon = btn.querySelector('.fa-chevron-down, .fa-chevron-up');
  if (content) {
    content.classList.toggle('hidden');
    if (icon) {
      icon.classList.toggle('fa-chevron-down');
      icon.classList.toggle('fa-chevron-up');
    }
  }
}
function toggleAccordion(id) {
  var el = document.getElementById(id);
  if (el) el.classList.toggle('hidden');
}

/* --- SweetAlert2 confirm helper --- */
function confirmDeleteSwal(options) {
  var title = options.title || 'Eliminar registro';
  var text = options.text || 'Esta accion no se puede deshacer';
  var confirmText = options.confirmText || 'Si, eliminar';
  var onConfirm = options.onConfirm;

  Swal.fire({
    title: title,
    html: text,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#d33',
    confirmButtonText: confirmText,
    cancelButtonText: 'Cancelar',
  }).then(function (result) {
    if (result.isConfirmed && typeof onConfirm === 'function') onConfirm();
  });
}

/* --- Sidebar toggle --- */
function toggleSidebar() {
  const layout = document.querySelector('.dashboard-layout');
  layout.classList.toggle('sidebar-collapsed');
  const collapsed = layout.classList.contains('sidebar-collapsed');
  localStorage.setItem('sidebar-collapsed', collapsed ? '1' : '0');
  updateToggleIcon(collapsed);
}

function updateToggleIcon(collapsed) {
  const icon = document.querySelector('#sidebar-toggle i');
  if (!icon) return;
  icon.classList.toggle('fa-angles-left', !collapsed);
  icon.classList.toggle('fa-angles-right', collapsed);
}

/* --- Sidebar submenu toggle --- */
function toggleMenu(id) {
  const menu = document.getElementById(id);
  const button = document.querySelector('[data-menu-toggle="' + id + '"]');
  const collapsed = document.querySelector('.dashboard-layout').classList.contains('sidebar-collapsed');
  if (collapsed) return;
  menu.classList.toggle('hidden');
  if (button) button.classList.toggle('open');
}

/* --- Profile dropdown --- */
function togglePerfilMenu(event) {
  if (event) event.stopPropagation();
  const menu = document.getElementById('perfil-menu');
  const btn = document.getElementById('perfil-btn');
  if (!menu || !btn) return;

  if (!menu.classList.contains('hidden')) {
    closePerfilMenu();
    return;
  }

  const rect = btn.getBoundingClientRect();
  const menuWidth = menu.offsetWidth || 268;
  const left = Math.max(8, Math.min(rect.left, window.innerWidth - menuWidth - 8));
  menu.style.left = left + 'px';
  menu.style.top = (rect.bottom + 8) + 'px';
  menu.classList.remove('hidden');
  btn.setAttribute('aria-expanded', 'true');
}

function closePerfilMenu() {
  const menu = document.getElementById('perfil-menu');
  if (!menu || menu.classList.contains('hidden')) return;
  menu.classList.add('hidden');
  const btn = document.getElementById('perfil-btn');
  if (btn) btn.setAttribute('aria-expanded', 'false');
}

/* --- Sidebar active link highlight --- */
function highlightActiveLink() {
  const path = window.location.pathname;
  document.querySelectorAll('.sidebar-link, .sidebar-sublink').forEach(function (link) {
    const href = link.getAttribute('href');
    if (!href) return;
    const url = new URL(href, window.location.origin);
    if (path === url.pathname) link.classList.add('active');
  });
  document.querySelectorAll('.submenu').forEach(function (menu) {
    if (menu.querySelector('.sidebar-sublink.active')) {
      menu.classList.remove('hidden');
      const button = document.querySelector('[data-menu-toggle="' + menu.id + '"]');
      if (button) button.classList.add('open');
    }
  });
}

/* --- Oculta submenus cuyos enlaces fueron filtrados por permisos --- */
function hideEmptySubmenus() {
  document.querySelectorAll('.submenu').forEach(function (menu) {
    if (!menu.children.length) return;
    if (menu.querySelector('.sidebar-sublink')) return;
    const button = document.querySelector('[data-menu-toggle="' + menu.id + '"]');
    if (button) button.style.display = 'none';
    menu.style.display = 'none';
  });
}

/* --- DOMContentLoaded --- */
document.addEventListener('DOMContentLoaded', function () {
  /* --- Init sidebar collapsed state --- */
  var layout = document.querySelector('.dashboard-layout');
  if (layout) {
    var collapsed = localStorage.getItem('sidebar-collapsed') === '1';
    if (collapsed) {
      layout.classList.add('sidebar-collapsed');
      updateToggleIcon(true);
    }
    hideEmptySubmenus();
    highlightActiveLink();
  }

  /* --- Profile menu close on click/escape --- */
  document.addEventListener('click', function (e) {
    var menu = document.getElementById('perfil-menu');
    var btn = document.getElementById('perfil-btn');
    if (!menu || menu.classList.contains('hidden')) return;
    if (menu.contains(e.target) || (btn && btn.contains(e.target))) return;
    closePerfilMenu();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closePerfilMenu();
  });

  /* --- Event delegation for data-action --- */
  document.addEventListener('click', function (e) {
    var target = e.target.closest('[data-action]');
    if (!target) return;
    var action = target.dataset.action;

    switch (action) {
      case 'remove-filter':
        removeFilter(target.dataset.param, target.dataset.resetPage !== 'false');
        break;
      case 'toggle-menu':
        toggleMenu(target.dataset.target);
        break;
      case 'toggle-perfil-menu':
        togglePerfilMenu(e);
        break;
      case 'toggle-sidebar':
        toggleSidebar();
        break;
      case 'toggle-acordeon':
        toggleAcordeon(target);
        break;
      case 'toggle-accordion':
        toggleAccordion(target.dataset.target);
        break;
      case 'switch-tab':
        switchTab(target.dataset.target);
        break;
      case 'print':
        window.print();
        break;
      case 'copy-clipboard':
        navigator.clipboard.writeText(target.dataset.value).then(function () {
          target.textContent = '\u2713 Copiado';
          var original = target.dataset.copyReset || 'Copiar';
          setTimeout(function () { target.textContent = original; }, 2000);
        });
        break;
      case 'confirm-delete-fetch':
        confirmDeleteSwal({
          title: target.dataset.confirmTitle || 'Eliminar registro',
          text: target.dataset.confirmText || 'Esta accion no se puede deshacer',
          confirmText: target.dataset.confirmBtn || 'Si, eliminar',
          onConfirm: function () {
            fetch(target.dataset.url, {
              method: 'POST',
              headers: { 'X-CSRFToken': getCookie('csrftoken') },
            }).then(function (r) {
              if (r.redirected) window.location.href = r.url;
              else window.location.reload();
            });
          },
        });
        break;
      case 'confirm-delete-redirect':
        confirmDeleteSwal({
          title: target.dataset.confirmTitle || 'Eliminar registro',
          text: target.dataset.confirmText || 'Esta accion no se puede deshacer',
          confirmText: target.dataset.confirmBtn || 'Si, eliminar',
          onConfirm: function () {
            window.location.href = target.dataset.url;
          },
        });
        break;
      case 'confirm-delete-post':
        confirmDeleteSwal({
          title: target.dataset.confirmTitle || 'Eliminar registro',
          text: target.dataset.confirmText || 'Esta accion no se puede deshacer',
          confirmText: target.dataset.confirmBtn || 'Si, eliminar',
          onConfirm: function () {
            var form = document.createElement('form');
            form.method = 'POST';
            form.action = target.dataset.url;
            var csrf = document.createElement('input');
            csrf.type = 'hidden';
            csrf.name = 'csrfmiddlewaretoken';
            csrf.value = getCookie('csrftoken');
            form.appendChild(csrf);
            document.body.appendChild(form);
            form.submit();
          },
        });
        break;
      case 'confirm-action':
        confirmDeleteSwal({
          title: target.dataset.confirmTitle || 'Confirmar',
          text: target.dataset.confirmText || '',
          confirmText: target.dataset.confirmBtn || 'Confirmar',
          onConfirm: function () {
            var actionUrl = target.dataset.url;
            var method = target.dataset.method || 'POST';
            if (actionUrl) {
              fetch(actionUrl, {
                method: method,
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
              }).then(function (r) {
                if (r.redirected) window.location.href = r.url;
                else window.location.reload();
              });
            }
          },
        });
        break;
    }
  });

  /* --- Auto-print pages with class="auto-print" on body --- */
  if (document.body && document.body.classList.contains('auto-print')) {
    window.print();
  }

  /* --- Auto-submit forms on select[data-auto-submit] change --- */
  document.querySelectorAll('select[data-auto-submit]').forEach(function (sel) {
    sel.addEventListener('change', function () { this.form.submit(); });
  });

  /* --- Auto-submit filter forms on input (debounced) --- */
  document.querySelectorAll('form[data-auto-filter]').forEach(function (form) {
    form.querySelectorAll('input[type="search"], input[name="q"]').forEach(function (input) {
      input.addEventListener('input', debounce(function () { form.submit(); }, 450));
    });
  });

  /* --- Confirm on submit for forms with data-confirm --- */
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      var msg = form.dataset.confirm || 'Esta seguro de realizar esta accion?';
      e.preventDefault();
      var self = this;
      Swal.fire({
        title: 'Confirmar',
        html: msg,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        confirmButtonText: 'Si, continuar',
        cancelButtonText: 'Cancelar',
      }).then(function (result) {
        if (result.isConfirmed) self.submit();
      });
    });
  });

  /* --- Confirm links with data-confirm-link --- */
  document.querySelectorAll('a[data-confirm-link]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var msg = a.dataset.confirmLink || 'Esta seguro?';
      var self = this;
      Swal.fire({
        title: 'Confirmar',
        html: msg,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        confirmButtonText: 'Si, continuar',
        cancelButtonText: 'Cancelar',
      }).then(function (result) {
        if (result.isConfirmed) window.location.href = self.href;
      });
    });
  });
});


/* ============================================================
   Mini tarjeta de persona (popover estilo Odoo)
   El avatar brilla al pasar el mouse y la tarjeta se abre al
   hacer clic en cualquier elemento con data-persona-card:
     <button data-persona-card data-tipo="estudiante|docente|usuario" data-id="5">
   ============================================================ */
(function () {
  'use strict';
  if (window.__personaCardInit) return;
  window.__personaCardInit = true;

  var URL_CARD = '/ajax/persona-card/';

  var cache = new Map();
  var card = null;
  var triggerActual = null;

  function clave(t) { return t.dataset.tipo + ':' + t.dataset.id; }

  function asegurarCard() {
    if (card) return card;
    card = document.createElement('div');
    card.className = 'persona-card';
    card.setAttribute('role', 'dialog');
    document.body.appendChild(card);
    return card;
  }

  function obtenerDatos(trigger) {
    var key = clave(trigger);
    if (!cache.has(key)) {
      cache.set(key, fetch(
        URL_CARD + '?tipo=' + encodeURIComponent(trigger.dataset.tipo) +
        '&id=' + encodeURIComponent(trigger.dataset.id),
        { headers: { 'X-Requested-With': 'fetch' } }
      ).then(function (resp) {
        if (!resp.ok) throw new Error('persona-card: HTTP ' + resp.status);
        return resp.json();
      }));
    }
    return cache.get(key);
  }

  /* Construye el contenido usando textContent (CSP/seguro, sin HTML crudo) */
  function pintar(datos) {
    var c = asegurarCard();
    c.textContent = '';

    var fila = document.createElement('div');
    fila.className = 'persona-card-cuerpo';

    var foto;
    if (datos.foto_url) {
      foto = document.createElement('img');
      foto.className = 'persona-card-foto bg-gradient-to-br ' + datos.color;
      foto.src = datos.foto_url;
      foto.alt = datos.nombre;
    } else {
      foto = document.createElement('div');
      foto.className = 'persona-card-foto bg-gradient-to-br ' + datos.color;
      foto.textContent = datos.iniciales || '?';
    }
    fila.appendChild(foto);

    var textos = document.createElement('div');
    textos.className = 'persona-card-textos';

    var nombre = document.createElement('p');
    nombre.className = 'persona-card-nombre';
    nombre.textContent = datos.nombre;
    textos.appendChild(nombre);

    if (datos.subtitulo) {
      var sub = document.createElement('p');
      sub.className = 'persona-card-subtitulo';
      sub.textContent = datos.subtitulo;
      textos.appendChild(sub);
    }
    fila.appendChild(textos);
    c.appendChild(fila);

    if (datos.perfil_url) {
      var boton = document.createElement('a');
      boton.href = datos.perfil_url;
      boton.className = 'persona-card-boton';
      boton.textContent = 'Ver perfil';
      boton.addEventListener('click', function (ev) {
        ev.stopPropagation();
        ocultarInmediato();
      });
      c.appendChild(boton);
    }
  }

  function posicionar(trigger) {
    var c = asegurarCard();
    var r = trigger.getBoundingClientRect();
    var ancho = c.offsetWidth || 240;
    var alto = c.offsetHeight || 120;

    /* Debajo del avatar; si no cabe, encima. */
    var arriba = (r.bottom + 10 + alto > window.innerHeight) && (r.top - alto - 10 >= 0);
    var top = arriba ? (r.top - alto - 10) : (r.bottom + 10);

    /* Centrada sobre el trigger y sujeta a los bordes de la ventana. */
    var left = r.left + r.width / 2 - ancho / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - ancho - 8));

    c.style.top = top + 'px';
    c.style.left = left + 'px';
  }

  /* Abre la tarjeta del trigger (o la cierra si ya esta abierta en el) */
  function abrir(trigger) {
    var c = asegurarCard();
    if (triggerActual === trigger && c.classList.contains('persona-card-visible')) {
      ocultarInmediato();
      return;
    }
    triggerActual = trigger;
    c.classList.remove('persona-card-visible');
    obtenerDatos(trigger).then(function (datos) {
      if (triggerActual !== trigger) return;   /* cerraron antes de responder */
      pintar(datos);
      posicionar(trigger);                     /* medir con contenido */
      requestAnimationFrame(function () { c.classList.add('persona-card-visible'); });
    }).catch(function () { /* sin tarjeta si falla */ });
  }

  function ocultarInmediato() {
    triggerActual = null;
    if (card) card.classList.remove('persona-card-visible');
  }

  /* --- Delegacion global (funciona en tablas que se re-renderizan) --- */

  /* Clic en el avatar: abre/cierra. Clic fuera: cierra. */
  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-persona-card]');
    if (t) {
      e.preventDefault();
      abrir(t);
      return;
    }
    if (card && card.contains(e.target)) return;   /* dejan interactuar con la tarjeta */
    ocultarInmediato();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') ocultarInmediato();
  });

  /* Si hacen scroll o cambian el tamano, la tarjeta queda mal ubicada: cerrar */
  window.addEventListener('scroll', function () {
    if (triggerActual) ocultarInmediato();
  }, true);
  window.addEventListener('resize', function () {
    if (triggerActual) ocultarInmediato();
  });
})();
