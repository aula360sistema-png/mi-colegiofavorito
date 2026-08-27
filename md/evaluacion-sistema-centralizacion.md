# Evaluación Completa del Sistema — Centralización de Flujos

## 0. Resumen ejecutivo

Revisé las 17 apps del proyecto buscando el mismo patrón de dispersión que encontramos en Promociones y en Correo. **Buena noticia:** el sistema, en general, ya sigue una convención consistente de centralización — casi cada módulo tiene su propia "puerta de entrada" (`app_inicio` o `dashboard`) desde donde se accede a todo lo demás de ese módulo. **Promociones es la excepción real, no la regla** — es el único flujo transversal que quedó repartido entre dos apps (`academico` y `administracion`) sin una puerta de entrada propia.

Esto cambia el enfoque: no hace falta reorganizar el sistema completo, sino **completar el patrón que ya existe** en el único punto donde se rompió.

---

## 1. Inventario: cómo está centralizado (o no) cada módulo hoy

| Módulo (app) | Punto de entrada único | Estado |
|---|---|---|
| Caja | `caja:caja_inicio` | ✅ Bien centralizado |
| Facturación | `facturacion:facturacion_inicio` | ✅ Bien centralizado |
| Estudiantes | `estudiantes:estudiante_inicio` | ✅ Bien centralizado |
| Nómina | `nomina:dashboard` | ✅ Bien centralizado |
| Docentes (vista del propio docente) | `docentes:dashboard_docente` | ✅ Bien centralizado |
| Seguridad | `seguridad:dashboard` | ✅ Bien centralizado |
| Administración general | `administracion:dashboard_admin` (con métricas cacheadas) | ✅ Bien centralizado |
| Comunicaciones | `comunicaciones:campania_list` | ✅ Centralizado (aunque simple) |
| Asistencia | `asistencia:tomar_asistencia` + `resumen_asistencia` | 🟡 Dos entradas, pero relacionadas y con sentido (tomar vs. consultar) |
| **Cierre de año / Boletines / Completivo / Promoción** | **No existe** — repartido entre `academico:anio_escolar_list`, `administracion:mantenimiento`, `administracion:lista_boletines` | 🔴 **Único módulo sin puerta de entrada propia** |
| Auditoría | 1 sola vista | ⚪ Módulo pequeño, no necesita hub |
| IA / Orientación | 1 sola vista cada uno | ⚪ Módulos pequeños, no necesitan hub |
| Tutores | Vistas dentro de `estudiantes` en su mayoría | 🟡 Aceptable, tutores es secundario a estudiantes |

**Conclusión del inventario:** confirma lo que ya sospechabas — el problema no es "todo el sistema está desorganizado", es específicamente el flujo de cierre/boletines/completivo/promoción, que es también el más crítico del calendario escolar (una vez al año, alto impacto, varios pasos obligatorios en orden). Tiene sentido que sea el primero en resolver.

---

## 2. Por qué Promociones quedó así (diagnóstico, no crítica)

Mirando el historial de construcción del código, tiene lógica: cada pieza se fue agregando donde "naturalmente" encajaba en el momento —
- `generar_boletines` y `cerrar_completivo` se agregaron a `administracion` porque ahí ya vivía `Acta` y el resto de reportes académicos.
- `cerrar_anio_escolar` y la promoción se agregaron a `academico` porque ahí ya vivía `AnioEscolar`, `Periodo` y `Grado`.

Es un crecimiento orgánico normal — no es un error de diseño, es lo que pasa en cualquier sistema real cuando un flujo cruza varios dominios (año escolar + calificaciones + matrícula). El patrón `app_inicio` que sí lograron mantener en el resto del sistema es señal de buen criterio; solo faltó aplicarlo aquí porque este flujo específico nació repartido entre dos apps desde el principio.

---

## 3. Otras oportunidades de centralización menores (para tu radar, no urgentes)

Además de Promociones, encontré dos cosas más pequeñas que vale la pena que tengas anotadas, aunque no son prioritarias:

### 3.1 Reportes dispersos
Vi `administracion:reportes` como una vista aparte del dashboard general. Vale la pena, en algún momento, revisar si esa pantalla y el futuro dashboard de Promociones deberían compartir componentes (ej. el mismo componente de "tarjeta de métrica") para que la nueva UI de promociones se sienta parte del mismo sistema, no un anexo visual distinto.

### 3.2 Tutores dentro de Estudiantes
No es un problema — es una decisión de diseño razonable (un tutor casi siempre se gestiona en el contexto de un estudiante) — pero si en el futuro creces en funcionalidad de tutores (portal de padres, por ejemplo), podría justificar su propio hub. Por ahora no hace falta tocarlo.

---

## 4. Plan de centralización de Promociones (resumen ejecutable)

Esto es lo que vamos a construir, siguiendo exactamente el patrón `app_inicio` que ya usa el resto del sistema — no una app nueva, sino una **vista hub** dentro de `administracion` (donde ya vive `dashboard_admin`, `mantenimiento_home`, `lista_boletines`), que:

1. Consulta el estado real de cada paso (reutilizando datos que ya existen: `PeriodoAnio`, `Inscripcion.estado_final`, `CierreAnio`, `Acta`).
2. Muestra un semáforo de las 6 etapas del cierre (periodos → boletines → recuperación/completivo → cierre de año → año siguiente → promoción).
3. Enlaza directamente a las vistas que **ya existen y funcionan** (`generar_boletines`, `cerrar_completivo`, `cerrar_anio_escolar`, `crear_anio_siguiente`, `promocion_preview`) — no las reemplaza.
4. Agrega la única vista que realmente falta: **"Estudiantes en recuperación"**, el detalle de quién debe qué asignatura a quién.

El detalle técnico completo (URLs, queries, templates) está en el documento `implementacion-dashboard-promociones.md` que te dejo junto a este.

---

## 5. Por qué esto no es "empezar de cero"

Vale la pena que quede explícito: de los 61+280 tests que ya corren en verde en el proyecto, ninguno se toca con este plan. Todo lo que se construye es:
- Una vista nueva de solo lectura (el dashboard).
- Una vista nueva de solo lectura (recuperación pendientes).
- Un par de links agregados al menú lateral (`core/context_processors.py`, dentro del bloque `'Calificaciones'` que ya existe).

No se modifica `cerrar_anio_escolar`, `calcular_promociones`, `cerrar_completivo` ni `generar_boletines` en esta primera iteración — eso queda para cuando aborden los puntos 3-6 de la sección 4 del documento `etapas-minerd-modulo-promociones.md` (nota mínima por nivel, extraordinaria, recuperación pedagógica), que sí tocan reglas de negocio y requieren tu confirmación previa con coordinación académica.
