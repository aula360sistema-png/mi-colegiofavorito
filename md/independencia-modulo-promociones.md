# Independencia Real del Módulo de Promociones — Plan de Extracción a App Dedicada

## 0. Contexto

Confirmé en el código (commit `de209df`) que el módulo nuevo de promociones quedó implementado dentro de `administracion` y `academico`, no como app independiente. Es una decisión pragmática válida para la primera entrega, pero no resuelve el problema de acoplamiento cruzado que discutimos: `administracion` importa de `academico`, `academico` importa de `estudiantes`, y el flujo de promoción en sí no es dueño de ningún dato — solo orquesta datos de tres dominios distintos.

Este documento es el plan concreto para, cuando decidas pagar ese costo, extraer todo a una app `promociones` dedicada — sin romper nada de lo que ya funciona.

---

## 1. Evidencia actual del acoplamiento (ya no es teoría, está en el código)

```python
# administracion/views.py — 1764 líneas, y sigue creciendo
from academico.models import (...)
from academico.services.periodos import abrir_periodos_anio, sincronizar_periodos_anio, sincronizar_periodos_centro
```

Las funciones nuevas viven así hoy:

| Función | App actual | Depende de |
|---|---|---|
| `promociones_dashboard` | `administracion` | `academico.PeriodoAnio`, `estudiantes.Inscripcion`, `core.CierreAnio`, `core.AnioEscolar` |
| `promociones_recuperacion` | `administracion` | `estudiantes.Inscripcion`, `academico.DocenteMateria`, `administracion.services.boletin` |
| `promociones_extraordinario` / `cerrar_extraordinario` | `administracion` | `academico.PeriodoAnio`, `estudiantes.Inscripcion`, `administracion.Acta` |
| `cerrar_anio_escolar` / `calcular_promociones` / `pendientes_por_docente` | `academico` | `estudiantes.Inscripcion`, `core.ConfiguracionCentro`, `core.CierreAnio` |

**Ninguna de estas funciones es dueña de un modelo propio** — todas leen y escriben sobre `Inscripcion` (de `estudiantes`), `PeriodoAnio`/`Periodo` (de `academico`) y `Acta`/`ConfiguracionCentro` (de `administracion`/`core`). Eso es exactamente el patrón de "proceso transversal viviendo dentro de un dominio que no le pertenece" que anticipé.

---

## 2. Qué NO cambia en la extracción (importante para que no te asustes con el alcance)

- **Ningún modelo se mueve.** `Inscripcion` sigue en `estudiantes`, `Periodo`/`PeriodoAnio` siguen en `academico`, `Acta` sigue en `administracion`. La app nueva no es dueña de datos, es dueña de **proceso**.
- **Las migraciones ya aplicadas no se tocan.** `estudiantes.0020_promocion_condicional`, `academico.0020_periodo_extraordinario`, etc. quedan donde están — son cambios de esquema en los dominios correctos.
- **Las URLs públicas pueden mantenerse** (`/administracion/promociones/...`) mientras migras, usando un namespace de app nueva pero manteniendo el prefijo de URL si quieres evitar romper bookmarks/enlaces guardados.

---

## 3. Qué SÍ se mueve

Solo las vistas/servicios que son puro **proceso de orquestación**, no dueños de modelo:

```
promociones/
├── apps.py
├── urls.py
├── views.py              ← promociones_dashboard, promociones_recuperacion,
│                            promociones_extraordinario
├── services/
│   ├── dashboard.py       ← _estado_cierre_anio (hoy en administracion/views.py)
│   ├── recuperacion.py    ← lógica de "quién debe qué" (hoy en administracion/views.py)
│   └── extraordinario.py  ← resultado_extraordinario_estudiante, cerrar_extraordinario
└── templates/
    └── promociones/
        ├── dashboard.html
        ├── recuperacion.html
        └── extraordinario.html
```

**Lo que se queda donde está** (porque sí pertenece a esos dominios):
- `cerrar_anio_escolar`, `calcular_promociones`, `promocion_preview`, `promocion_ejecutar`, `pendientes_por_docente`, `rellenar_ceros_periodo` → se quedan en `academico`, porque operan directamente sobre `AnioEscolar` y `Periodo`, que sí son de ese dominio. (Aquí hay un matiz: técnicamente también podrían migrar a `promociones`, pero el costo/beneficio es menor porque ya están bien ubicados — su dueño natural es `academico`).
- `generar_boletines`, `cerrar_completivo`, `resultado_completivo_estudiante`, `Acta` → se quedan en `administracion`, mismo razonamiento.

**Es decir: la extracción es parcial y deliberada.** Solo se mueve lo que es puramente "panel de control" sin dueño de dato (dashboard, recuperación, extraordinario) — no una migración total de todo lo relacionado a evaluación.

---

## 4. Plan de migración paso a paso (sin downtime, sin romper tests)

### Paso 1 — Crear la app vacía
```bash
python manage.py startapp promociones
```
Agregar a `INSTALLED_APPS`. Cero riesgo, no toca nada existente.

### Paso 2 — Mover código, no reescribirlo
Copiar (no reescribir) `_estado_cierre_anio`, `promociones_dashboard`, `promociones_recuperacion`, `promociones_extraordinario`, `cerrar_extraordinario` y `resultado_extraordinario_estudiante` tal cual están, a los nuevos archivos de `promociones/`. Ajustar únicamente los imports (`from academico.models import ...`, `from estudiantes.models import Inscripcion`, etc. — mismos imports, nueva ubicación).

### Paso 3 — Redirigir URLs con compatibilidad hacia atrás
```python
# administracion/urls.py — mantener temporalmente
from django.views.generic import RedirectView
path('promociones/', RedirectView.as_view(pattern_name='promociones:dashboard', permanent=True)),
```
Esto evita romper cualquier link guardado, favorito, o entrada de menú que apunte a la URL vieja, mientras el nuevo namespace ya está activo.

### Paso 4 — Actualizar el menú lateral
Cambiar el `reverse('administracion:promociones_dashboard')` en `core/context_processors.py` por `reverse('promociones:dashboard')`.

### Paso 5 — Mover los tests
Los tests de estas vistas (si ya existen) se mueven junto con el código a `promociones/tests.py`, sin reescribirlos — mismo patrón de "mover, no reescribir".

### Paso 6 — Eliminar el código viejo de `administracion`/`academico`
Solo después de confirmar que la suite completa sigue en verde con el código ya viviendo en `promociones`.

### Paso 7 — Verificación final
```bash
python manage.py test
```
Debe seguir dando el mismo resultado (389 tests, todos en verde) — la extracción es un refactor puro, no debería cambiar comportamiento observable.

---

## 5. Cuándo vale la pena pagar este costo (criterio objetivo, no solo estético)

Te doy una señal concreta en vez de una opinión: **hazlo cuando `administracion/views.py` se acerque a las 2500 líneas** (hoy está en 1764) **o cuando agregues la siguiente pieza pendiente** (recuperación pedagógica intra-periodo, del documento `etapas-minerd-modulo-promociones.md`), porque esa sí introduce un modelo nuevo genuino (`RecuperacionPedagogica` o similar) que no encaja limpiamente en ningún dominio existente — sería el primer caso real de "modelo propio del proceso de promoción", momento en que la independencia deja de ser solo arquitectónica y se vuelve necesaria por el propio dato.

Si prefieres no tocarlo todavía porque el sistema funciona bien así, es una decisión razonable — el costo de NO extraerlo hoy es acoplamiento y un archivo grande, no bugs ni riesgo funcional. No es urgente, es una mejora de mantenibilidad a mediano plazo.
