# Mi Colegio Favorito — Documentación

> Índice de la documentación del sistema completo y de los manuales por rol.
> Este conjunto de documentos refleja el código tal como está al día de hoy
> (rama `main`) e incluye los módulos nuevos (Reportes, Promociones, Caja,
> Facturación, Nómina, Comunicaciones, Asistencia, Seguridad, Audit, etc.).

## 1. Documentación del proyecto

| Documento | Contenido |
|-----------|-----------|
| [01-vision-general.md](01-vision-general.md) | Stack, arquitectura, instalación, despliegue, seguridad y datos demo |
| [02-roles-y-permisos.md](02-roles-y-permisos.md) | Roles del sistema, matriz de permisos por página y cómo se controla el acceso |
| [03-catalogo-modulos.md](03-catalogo-modulos.md) | Catálogo de módulos y pantallas con sus rutas |

## 2. Manuales por rol

| Rol | Manual | Público objetivo |
|-----|--------|------------------|
| Superadministrador | [manual-superadmin.md](manual-superadmin.md) | Administrador global del sistema |
| Director | [manual-director.md](manual-director.md) | Dirección del centro |
| Secretaría | [manual-secretaria.md](manual-secretaria.md) | Secretaría / registro y matrícula |
| Docente | [manual-docente.md](manual-docente.md) | Docentes y tutores de grado |
| Estudiante | [manual-estudiante.md](manual-estudiante.md) | Estudiantes |
| Tutor / padre | [manual-tutor.md](manual-tutor.md) | Padres, madres y tutores legales |
| Cajero | — | Acceso al módulo de Caja (ver catálogo de módulos; el flujo de caja se explica en el manual de la dirección) |

## 3. Documentos técnicos específicos (referencia)

Estos análisis profundizan en módulos o decisiones puntuales y viven en `md/`:

- `analisis-cierre-promocion-real.md`, `etapas-minerd-modulo-promociones.md`,
  `implementacion-dashboard-promociones.md`, `independencia-modulo-promociones.md`,
  `flujo-auto-promocion.md`, `proceso-recuperacion-modulo-promociones.md`,
  `gaps-pendientes-cupo-periodos.md`, `evaluacion-sistema-centralizacion.md`
  → Módulo de Promociones y cierre de año.
- `README-selector-correo.md`, `selector-proveedor-correo-hibrido.md`,
  `render-smtp-bloqueado-solucion.md` → Envío de correo (proveedores mixtos).
- `ENDPOINTS.md` → Referencia de rutas/endpoints del sistema.

## Notas

- Artefactos `md/parche-usuario-sidebar/` y `md/parche-usuario-sidebar.zip` son
  temporales y **no** forman parte de la documentación.