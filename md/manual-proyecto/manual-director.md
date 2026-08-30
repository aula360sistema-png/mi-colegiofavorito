# Manual del Director

> Rol: **`director`** — dirección del centro educativo.
> Tu menú es la sección **Dirección** del menú lateral. Lo que ves depende de
> los **módulos contratados** por el centro y de tus permisos.

## Inicio de sesión

1. Entra a la URL del sistema.
2. Escribe usuario y contraseña; confirma el **código 2FA** si lo tienes (o
   configúralo la primera vez).
3. Verás el **Dashboard administrativo** con el resumen del centro
   (estudiantes, asistencia, pagos, rendimiento, etc.).

## Menú principal

| Opción | Para qué sirve |
|--------|----------------|
| **Dashboard** | Resumen del centro con KPIs |
| **Reportes** | Hub de reportes: pestaña "Disponibles" (reportes listos para imprimir), "Consulta de estudiantes" (buscar boleta por estudiante/periodo), "Métricas" (estadísticas). KPIs de matrícula/aprobación siempre visibles |
| **Estudiantes** | Listado · Tutores · Constancias · Solicitudes de certificados · Disciplina y conducta · Historial clínico |
| **Matrícula** | Historial de matrículas por año escolar |
| **Docentes** | Listado de docentes del centro |
| **Sistema** | Mantenimiento · Bitácora · Seguridad de Datos · Alertas |
| **Comunicaciones** | Campañas · Nueva campaña · Comunicados · Nuevo comunicado |

Además, según los módulos contratados aparecen más secciones
(asistencia, caja, facturación, nómina, calificaciones, apariencia).

## Tareas principales

### Revisar reportes académicos
1. Ve a **Reportes**.
2. En **Disponibles**: elige el reporte (asistencia, calificaciones por grado y
   sección, carga académica) y filtra por año, grado, sección y periodo.
   Usa **Imprimir/PDF** para la planilla o la boleta.
3. En **Consulta de estudiantes**: busca un estudiante y abre su boleta de
   período (verás todas sus notas) o su kardex.
4. En **Métricas**: compara grados, secciones y periodos (promedios, aprobados,
   reprobados) y exporta.

### Seguimiento académico, boletines y cierre
1. **Seguimiento académico**: estado de calificaciones por grado/sección.
2. **Boletines oficiales**: listado de boletines emitidos por período.
3. **Cierre y Promociones** (menú Calificaciones): vista de quiénes aprueban,
   quiénes van a recuperación y quiénes a extraordinario, con auto-promoción y
   acta de sección antes de cerrar el año.

### Revisar cuentas por cobrar
1. Ve a **Caja → Cuentas por cobrar** (si el centro tiene caja).
2. Filtra por grado/estudiante para ver saldos, pagos y facturación.

### Enviar un comunicado o campaña
1. **Comunicaciones → Nuevo comunicado**: redacta la noticia (visible en los
   portales de estudiantes/tutores).
2. **Nueva campaña**: envío de correo/WhatsApp a un grupo (campañas).

### Ver quién hace qué
1. **Sistema → Bitácora**: auditoría de acciones por usuario.
2. **Sistema → Seguridad de Datos**: políticas de contraseñas y cifrado.
3. **Sistema → Alertas**: automatizaciones y avisos del sistema.

### Personalizar el centro
1. En **Módulos → Apariencia**: cambia el **tema** (colores) y el **logo** del
   centro. Se aplican a todos los portales del centro.

## Reglas importantes

- El director **no** crea usuarios ni gestiona otros centros (eso es de
  admin/superadmin).
- Los docentes solo ven **sus secciones**; los reportes que abres tú abarcan
  todo el centro.
- Los módulos apagados en la configuración del centro no se muestran.
- Si un docente no reporta asistencia, se refleja en el **Resumen de
  asistencia** del módulo de asistencia.