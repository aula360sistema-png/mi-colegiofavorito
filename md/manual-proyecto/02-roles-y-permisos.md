# 2. Roles del sistema y permisos por página

## 2.1 Cómo funciona el control de acceso

- Existe un modelo **`PermisoPagina`** (app `core`) que asocia a cada **URL
  (`url_name`)** la lista de **roles permitidos**.
- El **`PermisoPaginaMiddleware`** valida cada petición:
  - Si el usuario está autenticado y tiene rol permitido → entra.
  - Si no tiene rol → **403**.
  - Si la página **no tiene registro** de permiso → está **abierta a todo
    usuario autenticado**.
- En las plantillas, el tag `{% has_perm_page 'url_name' %}` decide si un enlace
  del menú se muestra (por eso el sidebar muestra solo lo que el rol puede usar).
- El panel **Permisos de Página** (módulo Administración) permite a
  admin/superadmin ajustar cada URL: qué roles entran y qué *usuarios
  individuales* extra tienen acceso. Cuidado: los permisos se cachean; al
  guardar desde el panel se invalida esa URL.
- Los roles base viven en **`RolCentro`**; cada centro asigna a cada usuario un
  rol en `UsuarioCentro`.

## 2.2 Roles del sistema

| Rol | Descripción | Portal principal |
|-----|-------------|------------------|
| `superadmin` | Administrador global; ve todos los centros y la administración completa | Inicio general + Administración |
| `admin` | Administrador del centro; igual que superadmin pero sin gestión de los otros centros ni "Centros educativos" | Inicio general + Administración |
| `director` | Dirección del centro; dashboard, todo lo estudiantil y reportes | Dashboard administrativo |
| `secretaria` | Secretaría; registro, matrícula, constancias, disciplina, docentes, tutores, soporte | Dashboard administrativo |
| `docente` | Califica sus asignaciones, toma asistencia, ve reportes de sus secciones | Inicio / Mis asignaciones |
| `estudiante` | Portal del estudiante | Portal del estudiante |
| `tutor` | Padre/madre/tutor legal | Portal del tutor |
| `cajero` | Caja del centro (según módulos contratados) | Caja |

## 2.3 Matriz de permisos por defecto

Fuente: `core/management/commands/seed_permisos.py`. Esta matriz se aplica con
`seed_permisos` (o `seed_inicial`) y se puede ajustar desde el panel.

| Página (`url_name`) | Roles permitidos por defecto |
|---------------------|------------------------------|
| `dashboard_docente` | docente |
| `estudiante_inicio` | estudiante |
| `estudiante_solicitudes` | estudiante |
| `estudiante_historial_clinico` | estudiante |
| `comunicaciones:estudiante_comunicados` | estudiante |
| `tutores:tutor_inicio` | tutor |
| `tutores:tutor_solicitudes` | tutor |
| `tutores:tutor_historial_clinico` | tutor |
| `comunicaciones:tutor_comunicados` | tutor |
| `administracion:dashboard_admin` | director, secretaria, admin, superadmin |
| `reportes:reportes`, `reportes:reporte_asistencia`, `reportes:reporte_calificaciones`, `reportes:boleta_periodo`, `reportes:print_calificaciones`, `reportes:print_boleta`, `reportes:reporte_carga_academica` | director, secretaria, admin, superadmin, **docente** (docente solo ve sus secciones) |
| `administracion:mantenimiento` | director, secretaria, admin, superadmin |
| `auditoria:bitacora` | director, secretaria, admin, superadmin |
| `seguridad:dashboard` | director, secretaria, admin, superadmin |
| `estudiante_list`, `estudiante_create`, `historial_estudiantes`, `constancias`, `disciplina`, `solicitudes_certificados`, `historial_clinico_list` | director, secretaria, admin, superadmin |
| `tutores:tutor_list`, `docente_list` | director, secretaria, admin, superadmin |
| `docente_create` | secretaria, admin, superadmin |
| `comunicaciones:campania_list`, `comunicaciones:campania_create`, `comunicaciones:comunicado_list`, `comunicaciones:comunicado_create` | director, admin, superadmin |
| `nomina:dashboard` | director, admin, superadmin |
| `core:home` | admin, superadmin |
| `usuarios:crear_miembro` | admin, superadmin |
| `administracion:listado_personal` | admin, superadmin |
| `core:configuracion_centro` | admin, superadmin |
| `core:centro_list` | superadmin |

## 2.4 Módulos con acceso por configuración y rol

Además de los permisos de página, algunos módulos solo aparecen si **el centro
los tiene contratados y el rol está en la lista del módulo**
(`core/context_processors.py`):

| Módulo | Cómo se activa | Roles con acceso |
|--------|----------------|------------------|
| **Asistencia** | `modulo_asistencia` | docente, secretaria, director, admin, superadmin (+ QR si `permitir_qr_asistencia`, biométrico si `usar_biometrico`) |
| **Caja** | `modulo_caja` | director, admin, superadmin, cajero, secretaria ("Gestionar cajas" solo director/admin/superadmin) |
| **Facturación** | `permitir_facturacion` | director, admin, superadmin, cajero, secretaria |
| **Nómina** | `modulo_nomina` | director, admin, superadmin, secretaria |
| **Comunicaciones (correo)** | `modulo_mensajeria` | director, admin, superadmin, secretaria |
| **Calificaciones** | siempre (roles fijos) | docente ("Mis asignaciones"), director/secretaria (seguimiento, boletines, cierre y promociones) |
| **Apariencia** | siempre (roles fijos) | director, admin, superadmin |

## 2.5 Reglas especiales de alcance de datos

Aunque un rol "entre" a una página, el sistema limita los **datos** que ve:

- **Docente en `reportes:*`**: solo sus secciones/asignaciones
  (`secciones_de_grado`, `inscripciones_visibles`, `carga_academica(user=...)`).
  Si intenta abrir una sección ajena → **403**. El AJAX de cascada de secciones
  (`/estudiantes/ajax/cargar-secciones/`) rechaza a docentes; un docente nunca
  consume ese endpoint.
- **Estudiante/Tutor en los portales**: solo su propia información (kardex,
  solicitudes, historial clínico, comunicados) y las deudas de los estudiantes
  a su cargo.
- **Superadmin**: el único que ve "Centros educativos" y puede seleccionar
  centro libremente.