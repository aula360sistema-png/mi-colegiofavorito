# Manual de la Secretaría

> Rol: **`secretaria`** — atención al público, registro y matrícula.
> Tu menú es la sección **Secretaría** del menú lateral.

## Inicio de sesión

1. Entra a la URL del sistema.
2. Escribe tu usuario y contraseña; confirma el **código 2FA** (o configúralo
   la primera vez).
3. Verás el **Dashboard** de la institución.

## Menú principal

| Opción | Para qué sirve |
|--------|----------------|
| **Inicio** | Resumen del centro |
| **Reportes** | Hub de reportes (Disponibles, Consulta de estudiantes, Métricas) |
| **Estudiantes** | Listado · Matrícula · Constancias · Disciplina · Solicitudes de certificados · Historial clínico |
| **Docentes** | Listado de docentes · Nuevo docente |
| **Tutores** | Listado de tutores/padres |
| **Mantenimiento** | Configuración de mantenimiento |
| **Bitácora** | Auditoría de acciones |
| **Seguridad de Datos** | Políticas de seguridad |
| **Alertas** | Tablero de alertas |

Según los módulos contratados del centro también puedes ver **Caja**,
**Asistencia** o **Calificaciones** (seguimiento académico, boletines y cierre).

## Tareas principales

### Inscribir / matricular un estudiante
1. **Estudiantes → Nuevo estudiante**: registra los datos personales
   (matrícula, nombres, apellidos, cédula, nacimiento, datos del tutor).
2. Guarda y luego **Inscribir**: elige año escolar, grado y sección.
   Las asignaturas se cargan según el currículo del grado.
3. Si el estudiante quiere cambiar de sección: en el detalle se usa
   **Cambiar sección**.

### Matrícula y listado
- **Listado**: busca por matrícula, nombres o apellidos.
- **Matrícula (historial)**: consulta las matrículas de cada año escolar y su
  estado.

### Constancias
1. Ve a **Estudiantes → Constancias**.
2. Busca al estudiante y genera la **constancia de estudios** (imprimible).
3. También puedes imprimir el **kardex** del estudiante desde su detalle.

### Solicitudes de certificados
1. **Estudiantes → Solicitudes de certificados**: aquí llegan las solicitudes
   hechas desde el portal del estudiante o tutor.
2. Aprueba, cobra (si la caja está activa) y entrega el certificado.
3. Regla: no se aprueba si el estudiante tiene **deuda pendiente** con el
   centro (a menos que la caja esté apagada: entonces es gratuito y
   auto-aprobado).

### Disciplina y conducta
1. **Estudiantes → Disciplina**: registra faltas/observaciones de conducta.
2. Vincula el registro al estudiante y añade la descripción del incidente.

### Historial clínico
1. **Estudiantes → Historial clínico**: registra datos médicos/emergencia del
   estudiante (visibles también para estudiantes/tutores en su portal).

### Crear un docente
1. **Docentes → Nuevo docente**: datos personales, código, área, salario y las
   asignaturas que imparte.
2. Guarda; el sistema crea la cuenta de usuario del docente.

### Caja (si el centro la tiene)
- **Caja → Registrar pago**: cobra mensualidades u otros conceptos.
- **Caja → Cuentas por cobrar**: consulta saldos de los estudiantes.
- **Caja → Reporte diario**: cierre del día.

## Reglas importantes

- La secretaría **no** crea usuarios (eso es admin/superadmin), pero puede dar
  de alta un docente (el sistema crea su usuario).
- No se inscriben estudiantes en grados sin **cupo** o sin año escolar activo:
  el sistema lo avisa al intentarlo.
- Las **impresiones** de constancias, kardex y boletas se generan en PDF desde
  el botón Imprimir de cada pantalla.