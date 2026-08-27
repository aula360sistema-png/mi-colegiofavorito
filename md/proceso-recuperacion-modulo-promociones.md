# Proceso de Recuperación (Completivo) y Centralización del Módulo de Promociones

## 0. Primero, contexto real: así maneja esto el MINERD

Buscando la normativa dominicana para asegurarme de que el diseño encaje con lo que exige el ministerio, esto es lo relevante (Ordenanza 1-96, Sistema de Evaluación del Sistema Educativo Dominicano):

- La nota mínima de aprobación es **65 puntos** — que ya coincide con lo que tienes parametrizado en `ConfiguracionCentro.nota_minima_aprobacion` (bien, eso ya está alineado).
- Los estudiantes que reprueban **hasta 3 asignaturas** pasan a **Pruebas/Período Completivo** (lo que tu sistema llama `es_completivo`). Después de esa convocatoria, <cite index="2-1,3-1">quienes reprueben al menos una asignatura repiten el grado</cite>.
- El MINERD incluso maneja **convocatorias extraordinarias** adicionales para quienes no pudieron presentarse al completivo por enfermedad u otra causa de fuerza mayor — algo que tu modelo hoy no contempla (no hay "segunda vuelta" de completivo).

**Punto importante para tu sistema:** tu lógica actual (`administracion/services/boletin.py`) marca a un estudiante como `'recuperacion'` si tiene **cualquier cantidad** de asignaturas reprobadas, sin importar si son 1 o 6. La norma real dice que el límite son **3 asignaturas**; por encima de eso, en teoría debería ir directo a repitente, no a completivo. Esto es una decisión de negocio que hoy no está capturada en tu código — más detalle en la sección 3.

---

## 1. Cómo funciona hoy tu sistema, paso a paso (código real)

### 1.1 Los 4 estados de `Inscripcion.estado_final`
Confirmado en `administracion/views.py: generar_boletines`:

```python
if not promedios:
    estado = "sin_calificacion"
elif tiene_materia_reprobada:      # cualquier asignatura con pf < nota_minima
    estado = "recuperacion"
elif promedio_general >= nota_minima:
    estado = "aprobado"
else:
    estado = "reprobado"
```

Es decir: `reprobado` en tu sistema hoy significa "promedio general por debajo de la mínima" (no necesariamente relacionado a cuántas materias reprobó), y `recuperacion` significa "tiene al menos una materia por debajo, pero el promedio general da bien". Esto es un poco distinto al criterio MINERD (que es por cantidad de asignaturas, no por promedio general) — vale la pena que lo revises con tu coordinación académica.

### 1.2 El período de completivo (`Periodo.es_completivo`)
- Es un `Periodo` más del catálogo del centro, con la bandera `es_completivo=True`.
- Como no está atado a `AnioEscolar` directamente (recuerda: `Periodo` es catálogo, `PeriodoAnio` es el estado por año), se activa/cierra como cualquier otro periodo, vía `PeriodoAnio`.
- `construir_boletin_estudiante()` **excluye explícitamente** los periodos de completivo del promedio base — correcto, no debe contaminar la nota regular.

### 1.3 Cómo se califica el completivo hoy
Aquí está el hueco más importante. `docentes/views.py: calificar_tabla` (la pantalla donde el docente pone notas):

```python
periodos = Periodo.objects.filter(
    estados__anio_escolar=asignacion.anio_escolar,
    estados__activo=True
).order_by('orden')
```

Esto trae **todos los periodos activos, incluyendo el completivo si está abierto**, y muestra la tabla para **todos los estudiantes de la sección**, sin filtrar por quién realmente está en `recuperacion` ni por qué asignaturas reprobó. Funciona (no es un bug que rompa nada), pero es confuso: el docente ve una columna de "completivo" para estudiantes que ya aprobaron normal, sin ninguna señal de "estos son los que realmente deben presentarse". No hay una pantalla dedicada tipo "Estudiantes pendientes de completivo" — eso es justo lo que describes que "aún no tienes".

### 1.4 Cómo se resuelve el completivo (`cerrar_completivo`)
`administracion/views.py: cerrar_completivo` + `resultado_completivo_estudiante()`:

1. Bloquea si algún `PeriodoAnio` de completivo sigue abierto.
2. Toma **solo** las `Inscripcion` con `estado_final = 'recuperacion'`.
3. Por cada una, recalcula el boletín base para saber qué asignaturas reprobó.
4. Busca, entre **todas** las asignaturas de `DocenteMateria` de esa sección, las calificaciones registradas en el/los periodo(s) de completivo, y promedia.
5. El estudiante aprueba el completivo **solo si TODAS** las asignaturas que había reprobado alcanzan la nota mínima en el completivo.
6. Actualiza `estado_final` a `aprobado` o `reprobado` (ya no queda "recuperacion" después de esto), y deja registro dentro del `Acta.datos['completivo']` (JSON).

Este mecanismo en sí está bien diseñado — es correcto y ya cumple el espíritu de "todas las materias reprobadas deben aprobarse en el completivo". El problema no es el cálculo, es todo lo que rodea al cálculo (visibilidad, orden, reportes).

### 1.5 Dónde vive cada pieza hoy (por eso se siente disperso)

| Pieza del proceso | App | Archivo |
|---|---|---|
| Cerrar periodos normales | `academico` | `views.py: cerrar_todos_los_periodos` |
| Generar boletines (calcula estado_final) | `administracion` | `views.py: generar_boletines` |
| Calificar (incluye completivo si está abierto) | `docentes` | `views.py: calificar_tabla` |
| Cerrar completivo | `administracion` | `views.py: cerrar_completivo` |
| Dashboard de boletines (con resumen por estado) | `administracion` | `views.py: lista_boletines` |
| Cerrar año escolar | `academico` | `views.py: cerrar_anio_escolar` |
| Vista previa y ejecución de promoción | `academico` | `views.py: promocion_preview / promocion_ejecutar` |

Tienes razón en que esto está repartido en 3 apps distintas sin una "casa" común — de ahí tu pedido de centralizarlo.

---

## 2. La "excepción" que preguntabas: ¿qué pasa realmente al presionar el botón?

No es una excepción de Python que truene — es un **hueco de flujo/UX**, no de código roto. Concretamente, hoy nada te impide (ni te avisa) de estos dos escenarios:

**Escenario A — Presionas "Generar boletines" con el completivo aún sin resolver de un ciclo anterior**
No hay conflicto técnico (cada año escolar es independiente), pero tampoco hay ninguna alerta cruzada. No es realmente un problema, lo menciono para descartarlo.

**Escenario B — Presionas "Ejecutar promoción" sin haber corrido `cerrar_completivo` primero**
Este es el real. `calcular_promociones()` en `academico/services/cierre.py`:

```python
PROMUEVE = ('aprobado',)
REPITE = ('reprobado', 'recuperacion', 'sin_calificacion')
```

Si todavía hay estudiantes en `'recuperacion'` (porque nunca se corrió `cerrar_completivo`, o porque el completivo aún está en curso), **la promoción los trata como repitentes** — se pierde la oportunidad de que aprueben el completivo antes de decidir su destino. No hay ningún bloqueo, warning, ni siquiera un aviso visual que diga "ojo, todavía hay N estudiantes en recuperación sin resolver". El botón simplemente ejecuta con lo que haya en ese momento.

**Esto es justo el "aún no lo tengo" que mencionas** — no existe ese candado.

---

## 3. Diseño propuesto: Módulo centralizado de "Promociones"

### 3.1 Estructura general

Propongo crear una app nueva (o al menos un namespace de URLs y un menú propio) llamada `promociones`, que **no reemplaza** la lógica ya construida (sigue viviendo donde está, funciona bien) sino que la **organiza y le agrega las piezas que faltan**:

```
/promociones/
├── dashboard/                    ← NUEVO: semáforo de todo el proceso
├── recuperacion/                 ← NUEVO: listado detallado de quién debe qué
├── recuperacion/notificar/       ← NUEVO: avisar a docentes/tutores (reusa "comunicaciones")
├── periodos/                     ← existente (academico.cerrar_todos_los_periodos)
├── boletines/                    ← existente (administracion.generar_boletines, lista_boletines)
├── completivo/cerrar/            ← existente (administracion.cerrar_completivo)
├── anio/cerrar/                  ← existente (academico.cerrar_anio_escolar)
└── promocion/                    ← existente (academico.promocion_preview / ejecutar)
```

Técnicamente, la forma más barata de lograr esto sin reescribir nada: dejar las vistas donde están (para no romper permisos/tests/urls ya probados) y crear una vista `promociones/dashboard` que simplemente **consulta el estado de todas las piezas y linkea a las URLs ya existentes**. Es un "panel de control", no una reescritura.

### 3.2 Dashboard central (`/promociones/dashboard/`) — el semáforo

Reutiliza datos que **ya existen** en tu modelo, no requiere cálculos nuevos pesados:

```
┌─────────────────────────────────────────────────────────┐
│  Cierre de Año Escolar 2025-2026                         │
├─────────────────────────────────────────────────────────┤
│  1. Periodos regulares cerrados        ✅ 4/4            │
│  2. Boletines generados                ✅ 320/320        │
│  3. Estudiantes en recuperación        ⚠️ 18 pendientes  │
│     → Periodo de completivo            🟡 Abierto         │
│  4. Completivo procesado               ⬜ No iniciado     │
│  5. Año escolar cerrado                ⬜ Bloqueado       │
│  6. Promoción ejecutada                ⬜ Bloqueado       │
└─────────────────────────────────────────────────────────┘
```

Cada fila es un link directo a la vista que ya existe. Los pasos 5 y 6 aparecen bloqueados (grises, sin link activo) mientras el paso 3 tenga pendientes — así resolvemos el Escenario B de la sección 2 sin tocar la lógica de `calcular_promociones`, solo agregando el candado en la UI (y opcionalmente también a nivel de vista, ver 3.5).

### 3.3 Vista "Estudiantes en recuperación" (`/promociones/recuperacion/`) — lo que de verdad falta

Esta es la pieza central de tu pedido. Una tabla nueva, construida sobre datos que **ya se calculan** en `resultado_completivo_estudiante` pero que hoy no se muestran en ningún lado antes de cerrar el completivo:

| Estudiante | Grado/Sección | Asignaturas a recuperar | Docente responsable | Notas de completivo | Estado |
|---|---|---|---|---|---|
| Juan Pérez | 8vo A | Matemática, Ciencias | Prof. Gómez, Prof. Díaz | Matemática: 70 ✅ / Ciencias: — | Pendiente |
| Ana Ruiz | 8vo B | Lengua Española | Prof. Fernández | 58 ❌ | Reprobará completivo |

**Cómo se construye (reutilizando código existente):**
```python
inscripciones = Inscripcion.objects.filter(
    centro=centro, anio_escolar=anio, estado_final='recuperacion'
)
for ins in inscripciones:
    boletin = construir_boletin_estudiante(ins, centro, anio)  # ya existe
    reprobadas = [a for a in boletin["asignaturas"] if a["pf"] < nota_minima]
    # cruzar con DocenteMateria para saber el docente de cada una
```

No requiere modelo nuevo — es una vista de solo lectura sobre datos existentes. El valor que agrega es que por fin **alguien (coordinador/dirección) puede ver, antes de cerrar el completivo, exactamente quién debe qué y a quién le falta calificar**, en vez de descubrirlo indirectamente después de correr `cerrar_completivo`.

### 3.4 Filtrar `calificar_tabla` cuando el periodo activo es completivo

Cambio quirúrgico en `docentes/views.py: calificar_tabla`: cuando el periodo que se está calificando tiene `es_completivo=True`, filtrar `inscripciones` para mostrar **solo** a los estudiantes que:
1. Tienen `estado_final = 'recuperacion'`, y
2. Reprobaron específicamente la asignatura que ese docente dicta (no todas).

```python
if periodo_activo_es_completivo:
    ids_pendientes = [
        ins.id for ins in inscripciones
        if ins.estado_final == 'recuperacion'
        and asignatura_reprobada_por(ins, asignacion.asignatura)  # helper nuevo, reusa construir_boletin_estudiante
    ]
    inscripciones = inscripciones.filter(id__in=ids_pendientes)
```

Esto resuelve la confusión de que hoy el docente ve a toda la sección en la columna de completivo — con este cambio, solo ve a quien realmente le corresponde recuperar con él.

### 3.5 Candado real (no solo visual) antes de promover

Agregar la validación en `academico/views.py`, antes de permitir entrar a `promocion_preview` (o como advertencia bloqueante con opción de "continuar de todas formas" para casos especiales):

```python
pendientes_recuperacion = Inscripcion.objects.filter(
    centro=centro, anio_escolar=anio_que_cierra, estado_final='recuperacion'
).count()

if pendientes_recuperacion and configuracion.permite_completivo:
    # bloquear o mostrar advertencia con link directo a /promociones/recuperacion/
    ...
```

### 3.6 Notificaciones a docentes (reutilizando tu módulo de comunicaciones)

Como ya tienes el módulo `comunicaciones` funcionando (con el selector de proveedor de correo que acabamos de implementar), tiene sentido reutilizarlo aquí: cuando se abre el periodo de completivo, disparar un correo/notificación a cada docente que tenga estudiantes pendientes de calificar, con el listado exacto de quiénes y qué asignatura. Esto es una extensión natural del módulo que ya existe, no algo nuevo que construir desde cero.

### 3.7 Parametrizar el límite de asignaturas para ir a completivo (opcional, pero importante)

Dado el hallazgo de la sección 0 (MINERD limita a 3 asignaturas), sugiero agregar a `ConfiguracionCentro`:

```python
maximo_asignaturas_completivo = models.PositiveIntegerField(
    default=3,
    help_text="Máximo de asignaturas reprobadas para ir a completivo. "
              "Por encima de este número, el estudiante repite directo."
)
```

Y ajustar `generar_boletines` para que, si `len(reprobadas) > maximo_asignaturas_completivo`, el estado sea `reprobado` (repite directo) en vez de `recuperacion`. Esto es una decisión académica que deberías confirmar con tu coordinación antes de tocarla — lo dejo como recomendación, no lo implementé, porque cambia el comportamiento de negocio actual y no quiero tocar reglas de evaluación sin que lo confirmes explícitamente.

---

## 4. Resumen: qué es código nuevo vs. qué es reutilizar lo que ya existe

| Pieza | Tipo de trabajo |
|---|---|
| Dashboard `/promociones/dashboard/` | Vista nueva, pero solo lee datos existentes (`PeriodoAnio`, `Inscripcion.estado_final`, `CierreAnio`) |
| Vista `/promociones/recuperacion/` | Vista nueva, reutiliza `construir_boletin_estudiante()` y `DocenteMateria` tal cual existen |
| Filtro de `calificar_tabla` para completivo | Cambio quirúrgico en una vista existente |
| Candado antes de `promocion_preview` | Validación nueva, pequeña, en una vista existente |
| Notificación a docentes | Reutiliza 100% el módulo `comunicaciones` ya construido |
| Límite de asignaturas para completivo (MINERD) | Cambio de regla de negocio — requiere tu confirmación antes de tocar `generar_boletines` |

No hace falta reescribir `cerrar_completivo`, `resultado_completivo_estudiante`, ni `calcular_promociones` — esa lógica de cálculo ya está bien hecha. Lo que falta es la **capa de visibilidad y orquestación** alrededor de ella, que es exactamente lo que este módulo centralizado resuelve.

---

## 5. Siguiente paso

Si quieres, implemento esto igual que hicimos con el selector de correo: por partes, empezando por el dashboard y la vista de "Estudiantes en recuperación" (que es la de mayor impacto y no toca lógica de negocio existente, solo la expone), y dejamos el punto 3.7 (límite MINERD de 3 asignaturas) para cuando confirmes esa regla con tu coordinación académica.
