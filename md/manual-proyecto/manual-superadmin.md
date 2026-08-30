# Manual del Superadministrador

> Rol: **`superadmin`** — administrador global del sistema (y superusuario).
> Es el único que puede gestionar **todos los centros educativos**, crear
> usuarios, ajustar permisos y configurar la plataforma completa.

## Inicio de sesión

1. Entra a la URL del sistema y usa tu usuario y contraseña.
2. Si tienes **2FA** activo, escribe el código de 6 dígitos de tu app de
   autenticación (Google Authenticator, Authy, etc.).
3. Si **no** lo tienes activo, el sistema te llevará a **Configurar 2FA**:
   escanea el código QR o copia la clave secreta y confirma con un código.
4. Si perteneces a más de un centro, elige el centro de trabajo
   (puedes cambiarlo después en **Configuración global → Seleccionar centro**).

## Menú "Administración"

Cuando entras ves la sección **Administración** del menú lateral:

| Opción | Para qué sirve |
|--------|----------------|
| **Inicio** | Resumen general del sistema |
| **Reportes** | Hub de reportes del centro seleccionado (disponibles, consultas, métricas) |
| **Estudiantes** | Listado · Tutores · Matrícula · Constancias · Disciplina · Solicitudes de certificados · Historial clínico |
| **Docentes** | Listado de docentes |
| **Personal** | Personal del centro y Nómina de los centros que la tengan contratada |
| **Crear usuario** | Alta de usuarios/miembros del sistema |
| **Centros educativos** | Gestión de centros (solo superadmin) |
| **Mantenimiento** | Configuración de mantenimiento del centro |
| **Bitácora** | Auditoría: registro de todo lo que hace cada usuario |
| **Seguridad de Datos** | Cifrado, expiración de claves y políticas de seguridad |
| **Alertas** | Tablero de alertas y automatizaciones |
| **Permisos de Página** | Qué roles y qué usuarios pueden entrar a cada pantalla |
| **Configuración global** | Seleccionar centro · Configuración del centro · Admin Django |

## Tareas principales

### Crear un usuario
1. Ve a **Administración → Crear usuario**.
2. Completa los datos (usuario, contraseña, datos personales) y elige el **rol**:
   - `superadmin`/`admin` → administración del sistema.
   - `director`, `secretaria`, `cajero`, `docente`, `tutor`, `estudiante` según corresponda.
3. Guarda. El usuario podrá iniciar sesión y el sistema le pedirá configurar 2FA.

### Crear o gestionar un centro educativo
1. Ve a **Centros educativos**.
2. "Nuevo centro": nombre, dirección, RNC/código, contacto, etc.
3. Para cada centro puedes definir su **Configuración del centro**
   (módulos contratados: Caja, Facturación, Nómina, Asistencia, Comunicaciones,
   Certificados; precio de certificado; asistencia QR o biométrica).
4. Asigna usuarios al nuevo centro con su rol.

### Gestionar permisos por página
1. Ve a **Permisos de Página**.
2. Busca la pantalla (por ejemplo `reportes:reportes`) y edita:
   - marcar/desmarcar **roles permitidos**,
   - agregar **usuarios individuales** con acceso extra.
3. Al guardar se refresca el permiso. Preferible activar **2FA** a todo usuario
   con permisos de administración.

### Revisar la auditoría
1. Entra a **Bitácora**: aquí queda quién hizo qué, en qué módulo, desde qué IP.
2. Filter por usuario, módulo o rango de fechas para investigar cualquier cosa.

### Seguridad de datos
1. Entra a **Seguridad de Datos**.
2. Revisa el panel: expiración de contraseñas, política de passwords, cierre
   por inactividad y cifrado de datos sensibles.
3. Si un usuario no puede entrar, revisa que su contraseña no esté expirada.

## Reglas importantes

- **Solo `superadmin`** ve "Centros educativos" y puede operar entre centros;
  `admin` administra el centro actual pero no crea centros.
- La **configuración por centro** define qué módulos se usan; un módulo
  apagado oculta sus menús a todos los roles.
- Las pantallas sin permiso configurado quedan **abiertas a cualquier usuario
  autenticado**: revísalo periódicamente en "Permisos de Página".
- En producción, el **Admin Django** (`/admin/`) solo debe usarse con
  superusuario y siempre con 2FA.
- Reportes, Caja, Nómina y demás ven **solo el centro que está seleccionado**
  en ese momento (cámbialo en "Seleccionar centro").