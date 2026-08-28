# Gaps Pendientes Tras la Actualización — Cupo de Sección y Validación de Periodos

## 0. Contexto

De los gaps que señalé en `analisis-cierre-promocion-real.md`, la actualización nueva (commit `de209df`) resolvió **Gap 1** (docentes sin calificar) y **Gap 2** (orden completivo/promoción) de forma sólida y con buen criterio — incluso mejor de lo que yo había especificado en algunos puntos (ver nota al final). **Gap 3 y Gap 4 siguen sin implementar.** Aquí el detalle actualizado de cada uno, verificado directo en el código de hoy.

---

## 1. Gap 3 — Sin control de cupo por sección (sigue igual)

### Estado actual (confirmado en código)
```python
# academico/models.py
class Seccion(models.Model):
    centro = models.ForeignKey('core.CentroEducativo', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=5)

    class Meta:
        ordering = ['nombre']
        unique_together = ('centro', 'nombre')
```

`Seccion` **no tiene ningún campo de capacidad**. Esto sigue exactamente igual que cuando lo señalé la primera vez — no se tocó en esta actualización (tiene sentido, no era parte del alcance de "recuperación/completivo" que estaban resolviendo).

### Por qué importa ahora más que antes
Con la llegada de `promocion_condicional` y el flujo de extraordinario, hay **más puntos del sistema que matriculan gente en una sección sin validar cupo**:
- `promocion_ejecutar` (promoción masiva de aprobados)
- El cambio manual de sección que agregaron en el commit `e1765cf` ("Cambio de sección por estudiante tras la promoción")
- Cualquier matrícula manual nueva de secretaría

Ninguno de estos tres puntos valida capacidad, porque el dato ni siquiera existe en el modelo.

### Recomendación (sin cambios respecto a la original)
```python
capacidad_max = models.PositiveIntegerField(null=True, blank=True,
    help_text="Dejar vacío para sin límite.")
```
Y validar en los 3 puntos de entrada mencionados arriba, idealmente centralizado en un solo helper (`hay_cupo_disponible(seccion, grado, anio)`) para no repetir la validación tres veces con lógica ligeramente distinta en cada lugar — ese tipo de duplicación es donde después aparecen bugs de "en un flujo sí valida y en otro no".

---

## 2. Gap 4 — Validación de periodos no distingue tipo (empeoró ligeramente, no por regresión sino por crecimiento)

### Estado actual (confirmado en código, `academico/views.py`)
```python
def cerrar_anio_escolar(request, pk):
    ...
    if PeriodoAnio.objects.filter(
        anio_escolar=anio,
        cerrado=False
    ).exists():
        messages.error(request, "No se puede cerrar el año escolar. Existen períodos abiertos.")
        return redirect('anio_escolar_list')
```

Esta validación sigue siendo **genérica**: cuenta cualquier `PeriodoAnio` abierto, sin distinguir si es un periodo regular, de completivo o de extraordinario — y sin decir **cuál** está abierto en el mensaje de error.

### Por qué esto es más relevante ahora que antes
Cuando señalé este gap por primera vez, solo existían 2 tipos de periodo (`regular`, `completivo`). Ahora, con `es_extraordinario` agregado en esta actualización, **hay 3 tipos**, y el mensaje sigue siendo el mismo genérico: *"Existen períodos abiertos."* Un director que ya cerró todos los periodos regulares y el completivo, pero se le olvidó cerrar el extraordinario, va a recibir el mismo mensaje ambiguo que si hubiera dejado abierto un periodo regular del primer trimestre — no hay forma de saber cuál es, sin ir a revisar manualmente `periodo_list`.

Esto es justo el tipo de detalle que la nueva vista de dashboard-semáforo (que sí distingue los tres tipos, según revisé en `_estado_cierre_anio`) resuelve **para el dashboard**, pero **el mensaje de error dentro de `cerrar_anio_escolar` no se actualizó para aprovechar esa misma distinción** — son dos piezas de código que deberían decir lo mismo y hoy no lo dicen.

### Recomendación actualizada
```python
periodos_abiertos = PeriodoAnio.objects.filter(
    anio_escolar=anio, cerrado=False
).select_related('periodo')

if periodos_abiertos.exists():
    detalle = ', '.join(
        f"{p.periodo.nombre} ({'completivo' if p.periodo.es_completivo else 'extraordinario' if p.periodo.es_extraordinario else 'regular'})"
        for p in periodos_abiertos
    )
    messages.error(request, f"No se puede cerrar el año escolar. Períodos abiertos: {detalle}.")
    return redirect('anio_escolar_list')
```
Cambio pequeño, bajo riesgo, mejora real de UX para quien está cerrando el año.

---

## 3. Hallazgo adicional (no es Gap 3 ni 4, pero es de esta misma revisión y es más urgente que ambos)

Ya te lo mencioné en el análisis anterior, lo dejo documentado aquí formalmente para que quede junto con el resto de pendientes: **`calcular_promociones()` no reconoce el estado `promocion_condicional`.**

```python
# academico/services/cierre.py
PROMUEVE = ('aprobado',)
REPITE = ('reprobado', 'recuperacion', 'sin_calificacion')
# 'promocion_condicional' no está en ninguna de las dos listas
```

Un estudiante que `cerrar_extraordinario` marca como `promocion_condicional` (según el propio comentario del código: *"promueve pero con asignaturas pendientes"*) cae en el `else` de `calcular_promociones` → `accion = 'omitir'` → **no se promueve, no repite, queda fuera del plan por completo**, sin ningún aviso.

**Prioridad relativa:** a diferencia de los Gaps 3 y 4 (mejoras de robustez), esto es un **bug funcional activo** en una feature recién agregada — si algún estudiante llega a ese estado y corren la promoción, se pierde silenciosamente. Sugiero resolverlo antes que los Gaps 3 y 4, que son mejoras y no bugs.

```python
# Fix mínimo
PROMUEVE = ('aprobado', 'promocion_condicional')
```
Con la salvedad de que probablemente quieras que el registro de matrícula del año siguiente para un `promocion_condicional` quede marcado de alguna forma (ej. copiar el estado a `HistorialAcademico` o dejar una nota en la nueva `Inscripcion`) para que el coordinador del año siguiente sepa que ese estudiante tiene asignaturas pendientes de arrastre — eso es una decisión de UX/negocio que vale la pena confirmar antes de aplicar el fix mínimo de una línea.

---

## 4. Resumen de prioridad

| # | Hallazgo | Tipo | Prioridad |
|---|---|---|---|
| — | `promocion_condicional` no incluido en `PROMUEVE`/`REPITE` | Bug funcional activo | 🔴 Alta — corregir antes de la próxima promoción real |
| Gap 4 | Mensaje de periodos abiertos no distingue tipo | Robustez / UX | 🟡 Media |
| Gap 3 | Sin control de cupo por sección | Robustez / feature faltante | 🟢 Baja — solo si de verdad necesitas limitar matrícula por sección |

Ninguno de los tres requiere tocar `estudiantes.Inscripcion` a nivel de modelo (ya tiene todo lo necesario) ni migraciones nuevas para el fix del bug — es el más barato de resolver de los tres, y el más importante.
