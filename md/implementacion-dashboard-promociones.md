# Implementación: Dashboard de Promociones + Estudiantes en Recuperación

> Especificación lista para implementar en la próxima sesión, siguiendo el patrón `app_inicio` confirmado en `evaluacion-sistema-centralizacion.md`. Vive dentro de `administracion` (mismo lugar que `dashboard_admin`, `mantenimiento_home`, `lista_boletines`) — no es una app nueva.

## 1. Alcance de esta entrega

✅ Incluido:
- Vista `administracion:promociones_dashboard` — semáforo de las 6 etapas del cierre.
- Vista `administracion:promociones_recuperacion` — detalle de estudiantes en recuperación, qué asignatura deben, y con qué docente.
- Entradas nuevas en el menú lateral (`core/context_processors.py`).
- Templates nuevos, reusando el estilo Tailwind ya usado en `mantenimiento.html` y `dashboard.html`.

❌ No incluido (para siguientes iteraciones, ver `etapas-minerd-modulo-promociones.md` sección 4):
- Filtro de `calificar_tabla` para completivo (punto 3.4 del doc anterior).
- Candado real antes de `promocion_preview` (punto 3.5).
- Notificación a docentes vía `comunicaciones` (punto 3.6).
- Nota mínima por nivel, evaluación extraordinaria, recuperación pedagógica intra-periodo.

Nada de esta entrega toca `cerrar_anio_escolar`, `calcular_promociones`, `cerrar_completivo` ni `generar_boletines` — son vistas 100% nuevas y de solo lectura sobre datos existentes.

---

## 2. Vista 1 — Dashboard de Promociones

### 2.1 URL
```python
# administracion/urls.py
path('promociones/', promociones_dashboard, name='promociones_dashboard'),
```

### 2.2 Lógica (nueva función en `administracion/views.py`, o en un `administracion/services/promociones.py` nuevo si prefieres mantener `views.py` más liviano)

```python
from core.utils.anio import obtener_anio_activo
from academico.models import PeriodoAnio
from estudiantes.models import Inscripcion
from core.models import CierreAnio, AnioEscolar, ConfiguracionCentro


def estado_cierre_anio(centro):
    """Arma el semáforo de las 6 etapas del cierre para el año activo.

    Reutiliza datos ya existentes: PeriodoAnio, Inscripcion.estado_final,
    CierreAnio, AnioEscolar. No hace ningún cálculo nuevo de negocio.
    """
    anio = obtener_anio_activo(centro)
    if not anio:
        return None

    periodos = PeriodoAnio.objects.filter(
        anio_escolar=anio, periodo__es_completivo=False
    )
    periodos_total = periodos.count()
    periodos_cerrados = periodos.filter(cerrado=True).count()

    completivo_periodos = PeriodoAnio.objects.filter(
        anio_escolar=anio, periodo__es_completivo=True
    )
    completivo_abierto = completivo_periodos.filter(cerrado=False).exists()
    completivo_existe = completivo_periodos.exists()

    inscripciones = Inscripcion.objects.filter(centro=centro, anio_escolar=anio)
    total_inscripciones = inscripciones.count()
    con_boletin = inscripciones.exclude(estado_final='pendiente').count()

    en_recuperacion = inscripciones.filter(estado_final='recuperacion').count()

    cierre = CierreAnio.objects.filter(anio_escolar=anio).first()
    anio_siguiente_existe = AnioEscolar.objects.filter(
        centro=centro, fecha_inicio__gt=anio.fecha_fin
    ).exists()

    # Un año se considera "con promoción ejecutada" si existen inscripciones
    # en el año siguiente que referencian matrícula_origen de este año.
    # (Este campo ya existe en Inscripcion según el diseño de trayectoria).
    promocion_ejecutada = Inscripcion.objects.filter(
        matricula_origen__anio_escolar=anio
    ).exists() if hasattr(Inscripcion, 'matricula_origen') else None

    return {
        'anio': anio,
        'periodos_total': periodos_total,
        'periodos_cerrados': periodos_cerrados,
        'periodos_ok': periodos_total > 0 and periodos_cerrados == periodos_total,

        'boletines_total': total_inscripciones,
        'boletines_generados': con_boletin,
        'boletines_ok': total_inscripciones > 0 and con_boletin == total_inscripciones,

        'en_recuperacion': en_recuperacion,
        'completivo_existe': completivo_existe,
        'completivo_abierto': completivo_abierto,
        'completivo_ok': en_recuperacion == 0,  # ya no quedan en 'recuperacion'

        'anio_cerrado': anio.cerrado,
        'cierre': cierre,

        'anio_siguiente_existe': anio_siguiente_existe,
        'promocion_ejecutada': promocion_ejecutada,
    }


@login_required
@centro_required
@role_required('director', 'admin', 'superadmin')
def promociones_dashboard(request):
    centro = request.centro
    estado = estado_cierre_anio(centro)
    return render(request, 'administracion/promociones/dashboard.html', {
        'estado': estado,
    })
```

**Nota sobre `matricula_origen`:** en el documento genérico inicial (`flujo-auto-promocion.md`) yo había sugerido ese campo para trazabilidad, pero **no confirmé si ya existe en tu modelo real `Inscripcion`** — hay que verificarlo al implementar. Si no existe, el indicador "promoción ejecutada" se puede aproximar de otra forma (ej. contar `Inscripcion` del año siguiente con `estado_final` distinto de vacío para los mismos estudiantes), o simplemente omitir ese indicador en esta primera versión y agregarlo después.

### 2.3 Template — `administracion/templates/administracion/promociones/dashboard.html`

Estructura (reusa clases Tailwind del proyecto, mismo estilo que `mantenimiento.html`):

```html
{% extends 'base.html' %}
{% block content %}
<div class="max-w-5xl mx-auto py-8 px-4">
  <h2 class="text-2xl font-bold text-gray-800 mb-1">Cierre de Año Escolar y Promociones</h2>
  <p class="text-sm text-gray-500 mb-6">{{ estado.anio }}</p>

  {% if not estado %}
    <div class="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-4">
      No hay año escolar activo.
    </div>
  {% else %}
  <div class="space-y-3">

    <!-- Paso 1: Periodos -->
    <div class="flex items-center justify-between bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
      <div>
        <span class="{% if estado.periodos_ok %}text-green-600{% else %}text-amber-600{% endif %} font-semibold">
          {% if estado.periodos_ok %}✅{% else %}⬜{% endif %} 1. Periodos regulares cerrados
        </span>
        <p class="text-xs text-gray-400 mt-0.5">{{ estado.periodos_cerrados }}/{{ estado.periodos_total }}</p>
      </div>
      <a href="{% url 'periodo_list' %}" class="text-sm text-indigo-600 hover:underline">Ver periodos</a>
    </div>

    <!-- Paso 2: Boletines -->
    <div class="flex items-center justify-between bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
      <div>
        <span class="{% if estado.boletines_ok %}text-green-600{% else %}text-amber-600{% endif %} font-semibold">
          {% if estado.boletines_ok %}✅{% else %}⬜{% endif %} 2. Boletines generados
        </span>
        <p class="text-xs text-gray-400 mt-0.5">{{ estado.boletines_generados }}/{{ estado.boletines_total }}</p>
      </div>
      <a href="{% url 'administracion:lista_boletines' %}" class="text-sm text-indigo-600 hover:underline">Ver boletines</a>
    </div>

    <!-- Paso 3: Recuperación / Completivo -->
    <div class="flex items-center justify-between bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
      <div>
        <span class="{% if estado.completivo_ok %}text-green-600{% else %}text-amber-600{% endif %} font-semibold">
          {% if estado.completivo_ok %}✅{% else %}⚠️{% endif %} 3. Estudiantes en recuperación
        </span>
        <p class="text-xs text-gray-400 mt-0.5">
          {{ estado.en_recuperacion }} pendiente{{ estado.en_recuperacion|pluralize }}
          {% if estado.completivo_abierto %} · Periodo de completivo abierto{% endif %}
        </p>
      </div>
      <a href="{% url 'administracion:promociones_recuperacion' %}" class="text-sm text-indigo-600 hover:underline">Ver detalle</a>
    </div>

    <!-- Paso 4: Cierre de año -->
    <div class="flex items-center justify-between bg-white rounded-xl border border-gray-100 p-4 shadow-sm {% if not estado.completivo_ok %}opacity-50{% endif %}">
      <div>
        <span class="{% if estado.anio_cerrado %}text-green-600{% else %}text-gray-500{% endif %} font-semibold">
          {% if estado.anio_cerrado %}✅{% else %}⬜{% endif %} 4. Año escolar cerrado
        </span>
      </div>
      <a href="{% url 'anio_escolar_list' %}" class="text-sm text-indigo-600 hover:underline">Ir a cierre</a>
    </div>

    <!-- Paso 5 y 6: Año siguiente + Promoción -->
    <div class="flex items-center justify-between bg-white rounded-xl border border-gray-100 p-4 shadow-sm {% if not estado.anio_cerrado %}opacity-50{% endif %}">
      <div>
        <span class="{% if estado.promocion_ejecutada %}text-green-600{% else %}text-gray-500{% endif %} font-semibold">
          {% if estado.promocion_ejecutada %}✅{% else %}⬜{% endif %} 5-6. Año siguiente y promoción
        </span>
      </div>
      <a href="{% url 'anio_escolar_list' %}" class="text-sm text-indigo-600 hover:underline">Ir a promoción</a>
    </div>

  </div>
  {% endif %}
</div>
{% endblock %}
```

---

## 3. Vista 2 — Estudiantes en recuperación

### 3.1 URL
```python
path('promociones/recuperacion/', promociones_recuperacion, name='promociones_recuperacion'),
```

### 3.2 Lógica

```python
from administracion.services.boletin import construir_boletin_estudiante
from academico.models import DocenteMateria

@login_required
@centro_required
@role_required('director', 'admin', 'superadmin')
def promociones_recuperacion(request):
    centro = request.centro
    anio = obtener_anio_activo(centro)
    if not anio:
        return redirect('administracion:promociones_dashboard')

    configuracion, _ = ConfiguracionCentro.objects.get_or_create(centro=centro)
    nota_minima = float(configuracion.nota_minima_aprobacion)

    inscripciones = Inscripcion.objects.filter(
        centro=centro, anio_escolar=anio, estado_final='recuperacion'
    ).select_related('estudiante', 'grado', 'seccion')

    filas = []
    for ins in inscripciones:
        boletin = construir_boletin_estudiante(ins, centro, anio)
        reprobadas = [
            a for a in boletin['asignaturas']
            if a.get('pf') is not None and a['pf'] < nota_minima
        ]

        # Cruzar cada asignatura reprobada con su docente responsable
        detalle = []
        for a in reprobadas:
            docente_materia = DocenteMateria.objects.filter(
                grado=ins.grado, seccion=ins.seccion,
                anio_escolar=anio, asignatura_id=a['asignatura_id']
            ).select_related('docente').first()
            detalle.append({
                'asignatura': a['asignatura'],
                'nota': a['pf'],
                'docente': docente_materia.docente if docente_materia else None,
            })

        filas.append({
            'inscripcion': ins,
            'asignaturas_pendientes': detalle,
        })

    return render(request, 'administracion/promociones/recuperacion.html', {
        'anio': anio,
        'filas': filas,
    })
```

**Nota de rendimiento:** esta vista hace una consulta por estudiante en recuperación (vía `construir_boletin_estudiante`) más una consulta por cada asignatura reprobada de cada uno. Para un centro con pocas decenas de estudiantes en recuperación (lo normal), es totalmente aceptable. Si en algún centro grande esto llegara a ser lento, se puede optimizar precargando todas las `Calificacion` del año en un solo query y agrupando en memoria — pero no vale la pena esa complejidad hasta que se demuestre necesaria.

### 3.3 Template — `administracion/templates/administracion/promociones/recuperacion.html`

Tabla simple:

```html
{% extends 'base.html' %}
{% block content %}
<div class="max-w-6xl mx-auto py-8 px-4">
  <div class="flex items-center justify-between mb-6">
    <h2 class="text-2xl font-bold text-gray-800">Estudiantes en recuperación — {{ anio }}</h2>
    <a href="{% url 'administracion:promociones_dashboard' %}" class="text-sm text-indigo-600 hover:underline">
      ← Volver al panel de cierre
    </a>
  </div>

  {% if not filas %}
    <div class="bg-green-50 border border-green-200 text-green-700 rounded-xl p-4">
      ✅ No hay estudiantes pendientes de recuperación.
    </div>
  {% else %}
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
    <table class="w-full text-sm">
      <thead class="bg-gray-50 text-gray-600">
        <tr>
          <th class="text-left px-4 py-3">Estudiante</th>
          <th class="text-left px-4 py-3">Grado/Sección</th>
          <th class="text-left px-4 py-3">Asignaturas a recuperar</th>
          <th class="text-left px-4 py-3">Docente(s)</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-gray-100">
        {% for fila in filas %}
        <tr>
          <td class="px-4 py-3">{{ fila.inscripcion.estudiante }}</td>
          <td class="px-4 py-3">{{ fila.inscripcion.grado }} - {{ fila.inscripcion.seccion }}</td>
          <td class="px-4 py-3">
            {% for d in fila.asignaturas_pendientes %}
              <span class="inline-block bg-amber-50 text-amber-700 rounded px-2 py-0.5 text-xs mr-1 mb-1">
                {{ d.asignatura }} ({{ d.nota }})
              </span>
            {% endfor %}
          </td>
          <td class="px-4 py-3 text-gray-500">
            {% for d in fila.asignaturas_pendientes %}
              {{ d.docente|default:"Sin asignar" }}{% if not forloop.last %}, {% endif %}
            {% endfor %}
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}
</div>
{% endblock %}
```

---

## 4. Menú lateral (`core/context_processors.py`)

Agregar dentro del bloque `'Calificaciones'` ya existente (línea ~269), junto a "Seguimiento académico" y "Boletines oficiales":

```python
if request.user.rol != 'docente':
    links.append({
        'etiqueta': 'Cierre y Promociones',
        'href': reverse('administracion:promociones_dashboard'),
        'icono': 'fa-graduation-cap',
    })
```

Esto lo pone junto a lo que ya es conceptualmente afín (boletines, seguimiento académico), sin crear un menú nuevo — sigue el mismo patrón que usa el resto del sistema.

---

## 5. Checklist de implementación (para la próxima sesión)

1. Verificar si `Inscripcion` tiene campo `matricula_origen` (o equivalente) — ajustar el indicador de "promoción ejecutada" según lo que exista realmente.
2. Agregar las 2 vistas a `administracion/views.py` (o extraerlas a `administracion/services/promociones.py` si prefieres mantener el archivo de vistas más corto — ya está bastante largo).
3. Agregar las 2 URLs a `administracion/urls.py`.
4. Crear los 2 templates en `administracion/templates/administracion/promociones/`.
5. Agregar el link al menú en `core/context_processors.py`.
6. Escribir 3-4 tests nuevos (siguiendo el estilo de `core/tests.py` / `administracion` tests existentes): dashboard con año sin datos, dashboard con datos parciales, vista de recuperación vacía, vista de recuperación con estudiantes.
7. Correr la suite completa (`python manage.py test`) antes de dar por cerrada la entrega, igual que hicimos con el selector de correo.

Cuando quieras, lo implemento directamente en el repo local como hicimos con el correo (código + tests + verificación en verde), y te dejo el zip con los archivos nuevos/modificados.
