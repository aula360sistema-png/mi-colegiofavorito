# Análisis del Flujo Real de Cierre y Promoción — Mi Colegio Favorito

> Basado en el código real del repo `aula360sistema-png/mi-colegiofavorito` (Django 6).
> Complementa (no reemplaza) el documento genérico anterior: aquí todo está mapeado a modelos, servicios y vistas reales.

## 0. Buena noticia primero

Gran parte de lo que describiste **ya está implementado**, y con buen criterio (doble paso calcular→ejecutar, bitácora de cierre, reapertura auditada). No estás empezando de cero: lo que falta es cerrar unos huecos puntuales y unir mejor las piezas. Abajo te explico el flujo real tal como está hoy, y luego los gaps concretos.

---

## 1. Modelo de datos real (lo que ya existe)

| Concepto que mencionaste | Modelo real | Dónde vive |
|---|---|---|
| Año escolar | `core.AnioEscolar` (`activo`, `cerrado`) | `core/models.py` |
| Bitácora de cierre | `core.CierreAnio` (usuario, fecha, `totales` JSON, `deudores` JSON, reapertura auditada) | `core/models.py` |
| Periodo (catálogo) | `academico.Periodo` (reutilizable por centro, con `es_completivo`) | `academico/models.py` |
| Estado del periodo *por año* | `academico.PeriodoAnio` (`cerrado`, `fecha_cierre`) | `academico/models.py` |
| Grado | `academico.Grado` — **ojo:** pertenece a `Nivel` → `Centro`, **no** al año escolar. Los grados son catálogo permanente, no se recrean cada año. | `academico/models.py` |
| Sección | `academico.Seccion` — pertenece al `Centro`, se vincula a uno o varios grados vía M2M `Grado.secciones`. Tampoco es por año. | `academico/models.py` |
| Docente-asignatura-sección | `academico.DocenteMateria` — este sí es **por año escolar** (`anio_escolar` FK) | `academico/models.py` |
| Matrícula (tu "listado por año/grado/sección") | `estudiantes.Inscripcion` (`estudiante`, `anio_escolar`, `grado`, `seccion`, `estado_final`, `promedio_final`) — `unique_together = (estudiante, anio_escolar)` | `estudiantes/models.py` |
| Calificación | `academico.Calificacion` (por `inscripcion` + `asignatura` + `competencia` + `periodo`) | `academico/models.py` |
| Configuración de nota mínima / completivo | `core.ConfiguracionCentro` (`nota_minima_aprobacion`, `permite_completivo`) | `core/models.py` |
| Listado maestro de estudiante | `estudiantes.Estudiante` (vive para siempre, independiente del año) | `estudiantes/models.py` |
| Histórico de trayectoria | `estudiantes.HistorialAcademico` (por año/grado/sección/estado) | `estudiantes/models.py` |

**Corrección importante respecto a mi primer documento:** como `Grado` y `Seccion` no están atados al año escolar, **no hace falta "crear el grado en el año siguiente"** — el grado ya existe como catálogo del nivel. Lo único que sí depende del año es: (a) que exista el `AnioEscolar` destino, y (b) que la `Seccion` elegida esté vinculada a ese `Grado` (vía el M2M). No hay concepto de "cupo/capacidad" en `Seccion` — si quieres controlar cupo, es una mejora a agregar (ver sección 5).

---

## 2. El flujo real, paso a paso (con nombres de función reales)

### Paso 1 — Cerrar periodos
`academico.views.cerrar_todos_los_periodos` → cierra todos los `PeriodoAnio` abiertos del año activo.
También existe `alternar_periodo_anio` para cerrar/abrir uno a la vez.

### Paso 2 — Generar boletines (aquí se calcula `estado_final`)
`administracion.views.generar_boletines`:
- Bloquea si hay periodos no-completivos abiertos.
- Por cada `Inscripcion`, llama a `construir_boletin_estudiante()` (en `administracion/services/boletin.py`), que arma el boletín leyendo `Calificacion` por asignatura/competencia/periodo.
- Calcula `promedio_general` y decide `estado_final`:
  - `sin_calificacion` → si ninguna asignatura tiene promedio.
  - `recuperacion` → si tiene al menos una asignatura por debajo de `nota_minima_aprobacion`.
  - `aprobado` / `reprobado` → según el promedio general vs. la nota mínima.
- Guarda `Inscripcion.promedio_final` y `Inscripcion.estado_final`, y genera/actualiza un `Acta` (snapshot JSON oficial del boletín).

### Paso 3 — Completivo (flujo aparte, tal como pediste)
`administracion.views.cerrar_completivo`:
- Requiere que el periodo de completivo esté cerrado.
- Toma solo las `Inscripcion` con `estado_final = 'recuperacion'`.
- Evalúa si aprobaron **todas** las asignaturas que tenían reprobadas, vía `resultado_completivo_estudiante()`.
- Actualiza `estado_final` a `aprobado` o `reprobado` según el resultado.

### Paso 4 — Cerrar año escolar
`academico.views.cerrar_anio_escolar`:
- Bloquea si hay algún `PeriodoAnio` abierto.
- Bloquea si hay `Inscripcion` con `estado_final` en `('pendiente', 'sin_calificacion')` — te muestra el listado en `request.session['pendientes_cierre']`.
- Genera reporte de deudores (`academico/services/cierre.py: deudores_del_anio`) si el módulo de caja está activo.
- Marca el `AnioEscolar.cerrado = True` y crea el registro `CierreAnio` (bitácora con totales y deudores).

### Paso 5 — Crear año siguiente (asistente, paso 1 de 3)
`academico.views.crear_anio_siguiente`:
- Sugiere nombre (`2025-2026` → `2026-2027`) y fechas basadas en el año origen.
- Al guardar, llama a `sincronizar_periodos_anio(nuevo)` para crear automáticamente los `PeriodoAnio` del nuevo año a partir del catálogo de `Periodo` del centro.
- Redirige directo a `promocion_preview`.

### Paso 6 — Vista previa de promoción (paso 2 de 3) — **esta es tu "tabla con todos"**
`academico.views.promocion_preview` + `academico/services/cierre.py: calcular_promociones()`:
- Recorre todas las `Inscripcion` del año que se cerró.
- Reglas actuales:
  ```python
  PROMUEVE = ('aprobado',)
  REPITE = ('reprobado', 'recuperacion', 'sin_calificacion')
  ```
  - `aprobado` → busca el siguiente grado por `orden` dentro del mismo `Nivel` (`grado_siguiente()`). Si no hay siguiente → `accion = 'egresado'`.
  - `reprobado` / `recuperacion` / `sin_calificacion` → `accion = 'repetir'`, mismo grado.
  - `retirado` → `accion = 'omitir'`.
- Muestra un resumen por acción (`promover`, `repetir`, `egresado`, `omitir`) y te deja **elegir la sección destino por cada grado** antes de ejecutar (no matricula todavía).

### Paso 7 — Ejecutar promoción (paso 3 de 3)
`academico.views.promocion_ejecutar` + `ejecutar_promocion()`:
- Crea las nuevas `Inscripcion` en el año destino, respetando las secciones elegidas.
- Evita duplicados (ya matriculado) y permite ejecutar solo para una selección de estudiantes (`solo_estudiantes`).
- Es transaccional (`@transaction.atomic`): o se aplica todo el lote elegido, o nada.

### Extras ya construidos
- `respaldo_anio`: exporta JSON completo del año (inscripciones, historial, calificaciones) — útil como respaldo antes de cerrar.
- `acta_seccion`: acta consolidada imprimible por grado/sección.
- `reabrir_anio_escolar`: reapertura supervisada, exige motivo (mín. 10 caracteres) y queda en la bitácora `CierreAnio` con usuario y fecha.
- `estudiantes.utils.validar_promocion_estudiante`: valida, al momento de una **matrícula manual**, a qué grado puede entrar un estudiante según su última inscripción cerrada (repite si reprobó/sin nota, avanza si aprobó). Esto es lo que evita que secretaría matricule mal a alguien "a mano" fuera del flujo automático.

---

## 3. Gaps reales encontrados (esto es lo que de verdad vale la pena arreglar)

### 🔴 Gap 1 — "Docente sin calificar" no se valida explícitamente
No existe ningún reporte tipo *"Docente X / Asignatura Y / Sección Z: N estudiantes sin nota"*. Lo que sí existe es indirecto: si a un estudiante le faltan notas, su asignatura queda excluida del promedio o su `estado_final` termina en `sin_calificacion` — pero eso se detecta a nivel de **estudiante**, no de **docente**, y sólo cuando corres `generar_boletines`.

Peor aún: en `construir_boletin_estudiante()`, si una competencia no tiene `Calificacion` cargada, simplemente **se excluye del promedio** (no cuenta como 0). Es decir, hoy en día, si un docente olvida calificar una asignatura completa a un estudiante, ese estudiante puede terminar con `estado_final = 'aprobado'` promediando solo las asignaturas que sí tienen nota — exactamente el escenario que querías evitar con tu regla de "al menos debe tener 0".

**Recomendación concreta:**
- Agregar una vista/reporte `validar_cierre_periodo(periodo_anio)` que, antes de permitir cerrar un `PeriodoAnio`, recorra `DocenteMateria` de ese periodo/año y verifique que cada estudiante matriculado en esa sección tenga `Calificacion` para cada competencia de esa asignatura. Bloquear el cierre del periodo (no solo del año) si faltan notas, o exigir confirmación explícita de Dirección para forzar con ceros.
- Decidir la regla de negocio: ¿se generan ceros automáticos al cerrar el periodo (con `origen='sistema'` para auditoría), o se bloquea hasta que el docente complete? Tu mensaje original sugiere que quieres ceros automáticos — hoy el sistema no hace eso, simplemente excluye la nota del cálculo.

### 🟡 Gap 2 — Orden de completivo vs. promoción no está forzado
`calcular_promociones()` trata `'recuperacion'` como `REPITE` (repetir grado) sin verificar si el completivo ya se resolvió. Si Dirección corre el asistente de promoción (`crear_anio_siguiente` → `promocion_preview`) **antes** de correr `cerrar_completivo`, cualquier estudiante que hubiera podido aprobar el completivo quedará marcado para repetir en vez de promoverse.

**Recomendación:** agregar una validación en `cerrar_anio_escolar` (o antes de habilitar el botón de promoción) que bloquee o al menos advierta si existen `Inscripcion` con `estado_final = 'recuperacion'` y el módulo de completivo está activo (`ConfiguracionCentro.permite_completivo = True`) pero el `cerrar_completivo` nunca se ejecutó para ese año.

### 🟡 Gap 3 — Sin control de cupo por sección
`Seccion` no tiene campo de capacidad. En `promocion_preview` puedes elegir cualquier sección destino sin límite. Si quieres control real de cupo (como mencionaste), habría que:
- Agregar `capacidad_max` a `Seccion` (o a una relación `Grado`–`Seccion`–`AnioEscolar` si el cupo cambia por año).
- Validar en `ejecutar_promocion()` antes de crear la `Inscripcion`.

### 🟢 Gap 4 (menor) — `cerrar_anio_escolar` no valida periodos de completivo por separado
La validación de periodos abiertos en `cerrar_anio_escolar` es genérica (cualquier `PeriodoAnio.cerrado=False`), mientras que `generar_boletines` sí distingue `es_completivo=False`. Vale la pena revisar que el orden de cierre (periodos normales → boletines → completivo → cierre de año) quede forzado en la UI y no dependa de que el usuario siga el orden correcto manualmente.

---

## 4. Respuesta directa a tu pregunta original

> "¿Debería haber un botón de auto-promover que arme una tabla y luego, al confirmar, verifique año/grado/sección para matricular?"

Sí, y **ya existe**, casi exactamente como lo planteaste:
`crear_anio_siguiente` (verifica/crea el año) → `promocion_preview` (la tabla que pediste, con acción por estudiante) → `promocion_ejecutar` (matricula de verdad, transaccional).

La única pieza que falta para que el flujo sea 100% robusto según tu descripción original es la validación de **notas faltantes por docente antes del cierre de periodo** (Gap 1) — ese es el hueco real entre "lo que ya construyeron" y "lo que tú describiste que necesitas".

---

## 5. Plan de acción sugerido (orden de esfuerzo/impacto)

1. **(Alto impacto, esfuerzo medio)** Construir el reporte/validación de "docentes con notas pendientes" antes de poder cerrar un `PeriodoAnio`, con la decisión de negocio: ¿bloquear o rellenar con 0 auditado?
2. **(Alto impacto, esfuerzo bajo)** Agregar validación: no permitir iniciar el asistente de promoción si quedan `Inscripcion` en `'recuperacion'` sin pasar por `cerrar_completivo` (cuando el centro tiene completivo activo).
3. **(Medio impacto, esfuerzo bajo)** Dashboard de estado de cierre por año: periodos cerrados / boletines generados / completivo procesado / año cerrado / promoción ejecutada — un semáforo visual para Dirección, reutilizando los datos que ya existen en `PeriodoAnio`, `Inscripcion.estado_final` y `CierreAnio`.
4. **(Opcional, si de verdad necesitas control de cupo)** Agregar capacidad a `Seccion` y validarla en `ejecutar_promocion`.

---

## 6. Nota sobre el acceso al sistema

Para este análisis usé el código fuente del repositorio (clonado directo desde GitHub), no la sesión web con las credenciales que compartiste — mis herramientas no manejan formularios de login con sesión en sitios externos. Si en algún momento quieres que revise datos reales cargados en la base (no solo el código), tendría que ser a través de algo que yo pueda leer directamente (un export, un dump, o dándome acceso a la shell de Django del servicio en Render).

También te recomiendo, ahora que compartiste el repo en este chat: **rotar el `SECRET_KEY`/`ENCRYPTION_KEY` y sobre todo la API key de OpenAI que según tu propio `PENDIENTES.md` quedó filtrada en el historial de git** — es un pendiente marcado en tu propio checklist y vale la pena resolverlo pronto.
