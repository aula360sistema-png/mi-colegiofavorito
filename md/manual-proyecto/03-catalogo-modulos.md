# 3. Catálogo de módulos y pantallas

Referencia de los módulos del sistema, sus pantallas y rutas principales.
Los roles que ven cada pantalla se definen con permisos por página
(ver `02-roles-y-permisos.md`).

## 3.1 Acceso y sesión (`usuarios`)

| Pantalla | Ruta | Bloqueo |
|----------|------|---------|
| Login | `/login/` | Público (con 2FA) |
| Configurar 2FA | `/2fa/configurar/` | Autenticado |
| Verificar 2FA | `/2fa/verificar/` | — |
| Crear usuario/miembro | `/usuarios/crear/` | admin, superadmin |
| Cerrar sesión | `/usuarios/logout/` | — |

## 3.2 Núcleo (`core`)

| Pantalla | Ruta | Notas |
|----------|------|-------|
| Inicio (home) | `/home/` | Sidebar según rol y módulos del centro |
| Seleccionar centro | `/seleccionar-centro/` | Usuarios multi-centro |
| Centros educativos | `/centros/` | Solo superadmin |
| Configuración del centro | `/configuracion-centro/` | admin, superadmin; enciende/apaga módulos |
| Permisos de Página | `/permisos-pagina/` | admin, superadmin |
| Tema del centro | `/tema-centro/` | director, admin, superadmin |
| Logo del centro | `/logo-centro/` | director, admin, superadmin |
| Admin Django | `/admin/` | superusuario |

> `ConfiguracionCentro` permite activar cada módulo: `modulo_asistencia`,
> `modulo_caja`, `permitir_facturacion`, `modulo_nomina`, `modulo_mensajeria`,
> `modulo_certificados`, `permitir_qr_asistencia`, `usar_biometrico`,
> `precio_certificado`, etc.

## 3.3 Estudiantes (`estudiantes`)

| Pantalla | Ruta |
|----------|------|
| Portal del estudiante | `/estudiantes/inicio/` |
| Listado de estudiantes | `/estudiantes/` |
| Nuevo estudiante | `/estudiantes/nuevo/` |
| Detalle (kardex, notas, pagos, observaciones) | `/estudiantes/<pk>/` |
| Editar / Eliminar | `/estudiantes/<pk>/editar/` · `eliminar/` |
| Inscribir (matrícula avanzada) | `/estudiantes/<id>/inscribir/` |
| Asignaturas de la inscripción | `/estudiantes/inscripcion/<id>/asignaturas/` |
| AJAX cascada grado → secciones | `/estudiantes/ajax/cargar-secciones/?grado=` |
| Historial de matrículas | `/estudiantes/historial/` |
| Constancias | `/estudiantes/constancias/` (+ `constancia/<pk>/`) |
| Disciplina y conducta | `/estudiantes/disciplina/` |
| Solicitudes de certificados (panel) | `/estudiantes/solicitudes-certificados/` |
| Solicitudes (portal estudiante) | `/estudiantes/inicio/solicitudes/` |
| Historial clínico (portal estudiante) | `/estudiantes/inicio/historial-clinico/` |
| Kardex imprimible | `/estudiantes/<pk>/kardex/imprimir/` |

## 3.4 Docentes (`docentes`)

| Pantalla | Ruta |
|----------|------|
| Listado de docentes | `/docentes/` |
| Nuevo docente | `/docentes/crear/` |
| Detalle / Editar | `/docentes/detalle/<pk>/` · `editar/<pk>/` |
| Panel del docente | `/docentes/dashboard/` |
| Estudiantes de la asignación | `/docentes/asignacion/<id>/estudiantes/` |
| Calificar (tabla por competencias) | `/docentes/asignacion/<id>/calificar/` |
| Guardar notas (AJAX) | `/docentes/asignacion/<id>/guardar-notas/` |

## 3.5 Tutores (`tutores`)

| Pantalla | Ruta |
|----------|------|
| Listado de tutores | `/tutores/` |
| Nuevo tutor | `/tutores/crear/` |
| Portal del tutor | `/tutores/inicio/` |
| Detalle de estudiante a cargo | `/tutores/estudiante/<id>/` |
| Solicitudes de certificados (portal tutor) | `/tutores/inicio/solicitudes/` |
| Historial clínico (portal tutor) | `/tutores/inicio/historial-clinico/` |

## 3.6 Académico (`academico`)

| Pantalla | Ruta |
|----------|------|
| Currículo | `/academico/curriculo/` |
| Niveles (estructura MINERD) | `/academico/niveles/` (+ CRUD, `estructura-minerd`) |
| Grados | `/academico/grados/` (+ CRUD) |
| Secciones | `/academico/secciones/` (+ CRUD) |
| Áreas | `/academico/areas/` (+ CRUD) |
| Asignaturas de un grado | `/academico/grados/<id>/asignaturas/` |
| Estudiantes de un grado | `/academico/grados/<id>/estudiantes/` |
| Cambiar sección de inscripción | `/academico/inscripciones/<pk>/cambiar-seccion/` |
| Cierre de año / reapertura / crear año siguiente / respaldo | comandos de Dashboard Académico |
| Acta de sección | `acta_seccion` |
| Asignaciones docente-materia | `docentemateria_list` (+ CRUD) |
| Competencias | `competencia_list` (+ CRUD) |

## 3.7 Administración (`administracion`)

| Pantalla | Ruta | Rol |
|----------|------|-----|
| Dashboard administrativo | `/administracion/dashboard/` | director, secretaria, admin, superadmin |
| Seguimiento académico | `/administracion/seguimiento-estudiantes/` | director, secretaria |
| Boletines oficiales | `/administracion/boletines/` | director, secretaria |
| Listado de personal | `/administracion/personal/` | admin, superadmin |
| Mantenimiento | `/administracion/mantenimiento/` | director, secretaria, admin, superadmin |
| Años escolares | CRUD en Dashboard Académico | director, admin, superadmin |

## 3.8 Reportes (`reportes`) — hub con pestañas

Acceso: director, secretaria, admin, superadmin y docente (con alcance a sus
secciones). Página principal: `/reportes/` con tres pestañas
(`?tab=disponibles|consultas|metricas`) y KPIs generales.

| Reporte | Ruta |
|---------|------|
| Hub de reportes | `/reportes/` |
| Reporte de asistencia | `/reportes/asistencia/` |
| Calificaciones por grado y sección (planilla) | `/reportes/calificaciones/` |
| Boleta del período de un estudiante | `/reportes/boleta/<estudiante_id>/<periodo_id>/` |
| Impresión planilla de calificaciones | `/reportes/calificaciones/imprimir/` |
| Impresión boleta | `/reportes/boleta/imprimir/` |
| Carga académica de docentes | `/reportes/carga-academica/` |
| Listado imprimible de sección | `print_listado_seccion` |

Detalles técnicos en `ENDPOINTS.md`.

## 3.9 Promociones y cierre (`promociones`)

| Pantalla | Ruta |
|----------|------|
| Dashboard de cierre y promociones | `/promociones/` |
| Recuperación | `/promociones/recuperacion/` |
| Extraordinario | `/promociones/extraordinario/` |

## 3.10 Asistencia (`asistencia`)

| Pantalla | Ruta | Notas |
|----------|------|-------|
| Tomar asistencia | `/asistencia/tomar/` | |
| Resumen de asistencia | `/asistencia/resumen/` | |
| Días de no docencia | `/asistencia/dias-no-docencia/` | |
| Asistencia por QR | `/asistencia/qr/` | si `permitir_qr_asistencia` |
| Asistencia biométrica | `/asistencia/biometrico/` | si `usar_biometrico` |

## 3.11 Caja (`caja`)

| Pantalla | Ruta |
|----------|------|
| Inicio de caja (apertura/cierre) | `/caja/` |
| Registrar pago (entrada) | `/caja/pagos/registrar/` |
| Registrar salida (egreso) | `/caja/egresos/registrar/` |
| Cuentas por cobrar | `/caja/cuentas-por-cobrar/` |
| Historial de pagos | `/caja/pagos/` |
| Historial de salidas | `/caja/egresos/` |
| Reporte diario | `/caja/reporte-diario/` |
| Aperturas y cierres | `/caja/sesiones/` |
| Conceptos | `/caja/conceptos/` |
| Asignar conceptos a estudiantes | `/caja/asignaciones/` |
| Gestionar cajas | `/caja/cajas/` (director/admin/superadmin) |

## 3.12 Facturación (`facturacion`)

| Pantalla | Ruta |
|----------|------|
| Inicio de facturación | `/facturacion/` |
| Crear factura | `/facturacion/crear/` |
| Facturas emitidas | `/facturacion/facturas/` |
| Secuencias NCF | `/facturacion/secuencias/` |
| Tipos de comprobante | `/facturacion/comprobantes/` |

## 3.13 Nómina (`nomina`)

| Pantalla | Ruta |
|----------|------|
| Panel de nómina | `/nomina/` |
| Configuración | `/nomina/configuracion/` |
| Períodos de pago | `/nomina/periodos/` |
| Historial de nómina | `/nomina/historial/` |
| Cargos | `/nomina/cargos/` |
| AFP | `/nomina/afp/` |
| ARS | `/nomina/ars/` |
| Tipos de ingreso / descuento | `/nomina/tipos-ingreso/` · `/nomina/tipos-descuento/` |

## 3.14 Comunicaciones (`comunicaciones`)

| Pantalla | Ruta | Rol |
|----------|------|-----|
| Centro de correo (campañas) | `/comunicaciones/campanas/` | director, admin, superadmin |
| Nueva campaña | `/comunicaciones/campanas/nueva/` | director, admin, superadmin |
| Comunicados (gestión) | `/comunicaciones/comunicados/` | director, admin, superadmin |
| Nuevo comunicado | `/comunicaciones/comunicados/nuevo/` | director, admin, superadmin |
| Comunicados (portal estudiante) | `comunicaciones:estudiante_comunicados` | estudiante |
| Comunicados (portal tutor) | `comunicaciones:tutor_comunicados` | tutor |

## 3.15 Seguridad, Auditoría y Automatizaciones

| Pantalla | Ruta |
|----------|------|
| Seguridad de Datos | `/seguridad/` (cifrado, expiración de claves) |
| Bitácora | `/auditoria/` (auditoría del sistema) |
| Alertas / automatizaciones | `/automatizaciones/` (tablero de alertas) |

## 3.16 Otros

- **Entrenamiento** (`entrenamiento`): material y espacio de formación.
- **Orientación** (`orientacion`): registros de orientación vinculados a los estudiantes.
- **IA** (`ia`): utilidades complementarias (integración opcional vía `OPENAI_API_KEY`).