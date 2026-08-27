# Etapas Oficiales del MINERD para Recuperación/Promoción y Módulo Centralizado

## 0. Corrección importante sobre la normativa vigente

En el documento anterior referencié la Ordenanza 1-96. Investigando más a fondo, **la normativa vigente hoy es la Ordenanza 04-2023** (Sistema de Evaluación de los Aprendizajes, aplicable a Inicial, Primario y Secundario, sector público y privado), que actualiza y sustituye en la práctica buena parte de la 1-96. Esto cambia algunos datos importantes que te había dado:

- **La nota mínima de aprobación NO es única para todo el centro**: es **65 puntos en Primaria** y **70 puntos en Secundaria**. Tu sistema hoy tiene un solo `ConfiguracionCentro.nota_minima_aprobacion` para todo el centro — esto es un gap real que detallo en la sección 3.
- La Ordenanza 04-2023 define **tres instancias distintas** de evaluación cuando un estudiante no alcanza la nota mínima, no solo una. Es justo lo que necesitas centralizar, y hoy tu sistema solo tiene construida la segunda de las tres.

---

## 1. Las 3 etapas oficiales (y una 4ta pieza documental) según Ordenanza 04-2023

### Etapa 1 — Recuperación pedagógica (dentro del año, entre periodo y periodo)
Es un acompañamiento **continuo**, no un examen final. Cuando un estudiante saca menos del mínimo en una competencia/asignatura **dentro de un periodo**, el centro debe ofrecerle actividades complementarias o tutorías **antes de cerrar ese periodo**, y la nueva valoración obtenida se suma a la calificación. No es algo que pase una vez al año al cerrar — pasa **período a período**, mientras el año está en curso.

**Esto es completamente distinto** al estado `'recuperacion'` que ya tienes programado (que en tu sistema significa "terminó el año con al menos una materia reprobada" — es más parecido a la Etapa 2). Hoy no tienes ningún mecanismo para registrar "este estudiante recibió recuperación pedagógica en el Periodo 2 y subió de 58 a 68" — solo ves el resultado consolidado al final.

### Etapa 2 — Evaluación completiva (fin de año)
Es el "completivo" que ya tienes construido: para estudiantes que, después de los periodos regulares (y en teoría después de haber pasado por recuperación pedagógica dentro de cada periodo), siguen con asignaturas por debajo del mínimo. Se les da una evaluación final de esas asignaturas específicas.

Tu implementación actual (`Periodo.es_completivo`, `resultado_completivo_estudiante`) cubre exactamente esta etapa, y está bien hecha.

### Etapa 3 — Evaluación extraordinaria (segunda convocatoria / casos especiales)
Para quienes **no pudieron presentarse** a la evaluación completiva por enfermedad, fuerza mayor, o situaciones similares — o (en años anteriores del MINERD) para quienes quedaron con materias pendientes de convocatorias previas. Es, en la práctica, una "segunda vuelta" del completivo, con su propia convocatoria y fechas.

**Esta etapa no existe en tu sistema hoy.** No hay ningún mecanismo para decir "este estudiante no pudo presentarse al completivo por justificación médica, dale una segunda oportunidad" — hoy, si no calificó en el completivo, `resultado_completivo_estudiante` simplemente no encuentra notas y el estudiante queda como reprobado por defecto, sin distinguir "reprobó" de "no se pudo presentar".

### Pieza documental — Registro de Grado
La Ordenanza 04-2023 define el **Registro de Grado** como el documento oficial matriz **por grado y sección** (no por estudiante individual) que consolida: datos de los estudiantes, asistencia, calificaciones parciales y finales por asignatura, **y los resultados de recuperación pedagógica, evaluación completiva y evaluación extraordinaria**, junto con estadísticas finales de promoción de la sección.

Hoy tu modelo `Acta` es **por estudiante**, no por sección — no tienes el equivalente al "Registro de Grado" consolidado que probablemente te van a pedir en una inspección o auditoría del MINERD.

### Dato adicional relevante: asistencia mínima del 80%
La misma ordenanza exige un mínimo de 80% de asistencia. Ya tienes esto calculado en tu proyecto (`asistencia/services.py: calcular_promedio_inscripcion`), **pero confirmé en el código que este cálculo nunca se cruza con el flujo de boletines ni de promoción** — hoy un estudiante con 40% de asistencia y buenas notas se promueve sin ninguna alerta.

---

## 2. Tabla resumen: qué exige el MINERD vs. qué tienes construido

| Etapa / requisito MINERD | ¿Existe en tu código? | Dónde |
|---|---|---|
| Nota mínima diferenciada por nivel (65 primaria / 70 secundaria) | ❌ No — es un solo valor por centro | `core.ConfiguracionCentro.nota_minima_aprobacion` |
| Recuperación pedagógica intra-periodo | ❌ No existe ningún registro de esto | — |
| Evaluación completiva (fin de año) | ✅ Sí, bien implementada | `Periodo.es_completivo`, `resultado_completivo_estudiante` |
| Evaluación extraordinaria (2da convocatoria / ausentes justificados) | ❌ No existe | — |
| Límite de asignaturas para ir a completivo vs. repetir directo | ❌ No se valida cantidad, solo "si tiene alguna" | `generar_boletines` |
| Registro de Grado (documento oficial por sección) | ❌ No existe (`Acta` es por estudiante) | `administracion.Acta` |
| Asistencia mínima 80% como condición de promoción | ⚠️ El dato existe pero no se usa en la decisión | `asistencia.services.calcular_promedio_inscripcion` (no conectado) |
| Estados operativos (aprobado/reprobado/recuperación/sin_calificación) | ✅ Sí | `Inscripcion.estado_final` |
| Matrícula automática de promovidos | ✅ Sí | `academico.services.cierre` |

---

## 3. Diseño del módulo centralizado, ahora con las 3 etapas MINERD como pasos reales

Actualizo el diseño de `/promociones/` del documento anterior para que **modele las 3 etapas oficiales como pasos explícitos del flujo**, no solo el completivo.

```
/promociones/
├── dashboard/                         ← semáforo con TODAS las etapas MINERD
├── recuperacion-pedagogica/           ← NUEVO: por periodo, intra-año
│   └── <periodo_id>/seccion/<id>/     ← tabla: quién bajó del mínimo en este periodo
├── completivo/
│   ├── pendientes/                    ← (ya diseñado antes) quién debe qué asignatura
│   └── cerrar/                        ← existente (administracion.cerrar_completivo)
├── extraordinaria/                    ← NUEVO: segunda convocatoria
│   ├── convocar/                      ← marcar quién entra (ausentes justificados / rezagados)
│   └── cerrar/                        ← mismo mecanismo que cerrar_completivo, reutilizado
├── registro-grado/<grado_id>/<seccion_id>/  ← NUEVO: documento consolidado por sección
├── anio/cerrar/                       ← existente
└── promocion/                         ← existente
```

### 3.1 Recuperación pedagógica intra-periodo (Etapa 1) — lo más nuevo de este diseño

No necesita modelo nuevo complejo: se puede modelar como **otro periodo especial**, igual que hiciste con el completivo, pero con una semántica distinta:

```python
# Nuevo campo en Periodo (reutilizando el mismo patrón que es_completivo)
es_recuperacion_pedagogica = models.BooleanField(default=False)
periodo_asociado = models.ForeignKey(
    'self', null=True, blank=True,
    help_text="A qué periodo regular pertenece esta recuperación (ej. recuperación del P2)"
)
```

La vista `calificar_tabla` (misma que ya filtras para completivo, sección 3.4 del documento anterior) se reutiliza aquí también: cuando el periodo activo es de recuperación pedagógica, mostrar solo a los estudiantes que quedaron bajo el mínimo **en ese periodo específico** (no en el año completo), para esa asignatura puntual. El resultado de esa recuperación se suma/reemplaza la nota del periodo original, tal como indica la norma.

Esto es opcional de implementar de inmediato — es la pieza más nueva y la que más cambia tu ciclo de trabajo actual (implica que cada periodo, antes de cerrarse, tenga su propia mini-ventana de recuperación). Te recomiendo decidir con tu coordinación académica si quieren activarla desde ya o dejarla para una segunda fase, ya que operativamente implica más trabajo para los docentes cada periodo.

### 3.2 Evaluación extraordinaria (Etapa 3) — reutiliza el mecanismo del completivo

Técnicamente, la forma más barata de implementarla es **tratarla igual que un segundo completivo**:

```python
# Periodo con es_completivo=True, pero marcado como "segunda convocatoria"
es_extraordinaria = models.BooleanField(default=False)
```

Y una vista `/promociones/extraordinaria/convocar/` que, en vez de tomar automáticamente a todos los `estado_final='recuperacion'`, permita a Dirección **seleccionar manualmente** quiénes entran (los que no se presentaron al completivo por justificación, o los que el MINERD reconvoca). El cálculo de aprobación reutiliza `resultado_completivo_estudiante()` casi tal cual, apuntando a este nuevo periodo en vez del completivo regular.

### 3.3 Registro de Grado — documento nuevo, pero de solo lectura

No requiere modelo nuevo: es un **reporte imprimible/PDF por grado y sección** que agrega en una sola vista lo que ya tienes disperso: lista de estudiantes de esa sección + asistencia (ya calculada) + notas por periodo + resultado de completivo + resultado de extraordinaria (si aplica) + estado final. Es prácticamente un `SELECT` grande sobre datos existentes, formateado como el MINERD lo pide. Aquí sí tiene sentido usar tu skill de generación de PDF para dejarlo descargable/imprimible en el formato oficial.

### 3.4 Nota mínima por nivel (corrección de configuración)

```python
# En Nivel (academico/models.py) en vez de (o además de) ConfiguracionCentro
nota_minima_aprobacion = models.DecimalField(
    max_digits=5, decimal_places=2, null=True, blank=True,
    help_text="Si se deja vacío, se usa el valor general del centro."
)
```

Y en `generar_boletines`, resolver la nota mínima según `inscripcion.grado.nivel.nota_minima_aprobacion or configuracion.nota_minima_aprobacion` — fallback al valor de centro si el nivel no tiene uno específico. Esto es un cambio pequeño pero importante para que Primaria (65) y Secundaria (70) no compartan el mismo umbral por error.

### 3.5 Asistencia como condición (opcional, a definir con coordinación)

Agregar al dashboard de recuperación/promoción una columna de `% asistencia` (ya calculable con `calcular_promedio_inscripcion`), y opcionalmente un flag de advertencia (no bloqueo automático, porque las excepciones de asistencia normalmente las autoriza Dirección caso por caso) cuando un estudiante está por debajo del 80% aunque sus notas den para promover.

---

## 4. Priorización sugerida (de más a menos urgente para lo que pediste: centralizar)

1. **Dashboard `/promociones/dashboard/`** con las 3 etapas visibles (aunque la Etapa 1 y 3 aún no tengan pantallas propias, mostrar su estado ayuda a visualizar el proceso completo).
2. **Vista de completivo pendientes** (ya diseñada en el documento anterior) — más impacto inmediato, cero riesgo, no toca reglas de negocio.
3. **Nota mínima por nivel** (3.4) — corrige un desalineamiento real con la norma vigente, cambio acotado.
4. **Registro de Grado** (3.3) — reporte de solo lectura, buen valor para auditorías/inspecciones del MINERD.
5. **Evaluación extraordinaria** (3.2) — más trabajo, pero reutiliza casi todo el mecanismo del completivo.
6. **Recuperación pedagógica intra-periodo** (3.1) — la de mayor esfuerzo y mayor cambio de proceso para tus docentes; sugiero conversarla primero con tu coordinación académica antes de construirla, porque cambia cómo trabajan los maestros cada periodo, no solo al final del año.

---

## 5. Siguiente paso

¿Empezamos por el punto 1 y 2 (dashboard + vista de completivo pendientes), que no tocan ninguna regla de negocio y dan valor inmediato? El resto (nota mínima por nivel, extraordinaria, recuperación pedagógica) los dejamos como siguientes iteraciones, en el orden de la sección 4, para no meter demasiado cambio de una vez.
