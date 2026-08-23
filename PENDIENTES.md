# Checklist - Pendientes para Produccion

## Seguridad
- [ ] CSP: eliminar `'unsafe-inline'` de `style-src` y migrar estilos inline a archivos CSS externos
- [ ] CSP: eliminar `'unsafe-inline'` de `script-src` y migrar scripts inline a archivos JS externos
- [ ] CSP: configurar `CONTENT_SECURITY_POLICY_REPORT_ONLY` solo para reportes, no en produccion
- [ ] Rotar SECRET_KEY y ENCRYPTION_KEY (actualmente en `.env`)
- [ ] Rotar API key de OpenAI filtrada en historial git (`sk-proj-CgFmvzQ...`)
- [ ] Configurar `SESSION_COOKIE_SECURE = True` (solo HTTPS)
- [ ] Configurar `CSRF_COOKIE_SECURE = True` (solo HTTPS)
- [ ] Configurar `SECURE_SSL_REDIRECT = True`
- [ ] Configurar `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`
- [ ] Configurar `SECURE_CONTENT_TYPE_NOSNIFF = True`

## Datos y Residuos
- [ ] Implementar tarea programada (Celery/cron) para `anonimizar_datos` de retencion
- [ ] Configurar `DATA_RETENTION_YEARS` segun normativa RED CAPPA
- [ ] Monitorear y auditar accesos a datos sensibles (HistorialClinicoEstudiante)

## Infraestructura
- [ ] Migrar de SQLite a PostgreSQL para produccion
- [ ] Configurar backup automatico de base de datos
- [ ] Configurar logging a archivo/servicio externo (no solo consola)
- [ ] Configurar envio de emails (SMTP real, no consola)

## Funcionalidad
- [x] **Módulo de permisos por página** — Asignar qué rol/usuario puede ver cada página. Requiere:
  - Modelo `PermisoPagina` (FK a `RolCentro` y/o `Usuario`) ✔ (core/models.py)
  - Guard en vistas o middleware que verifique permisos ✔ (`PermisoPaginaMiddleware`,
    corregido: antes `startswith(('/', ...))` excluía TODAS las rutas y nunca bloqueaba)
  - Panel de administración para gestionar permisos (CRUD) ✔ (/permisos/, solo superadmin;
    fixed: al renombrar url_name se invalidaba solo la clave nueva, no la vieja)
  - Seed de permisos por defecto por rol ✔ (`python manage.py seed_permisos`, idempotente,
    `--solo-faltantes` opcional; `seed_demo` ahora crea RolCentro con códigos de rol)
  - Template tag `{% has_perm_page 'nombre_url' %}` para ocultar enlaces en sidebar ✔
    (aplicado a todos los enlaces de home.html; submenús vacíos se ocultan vía shared.js;
    memoizado por request; caché invalidada por signals en cambios M2M)
  - Tests: core/tests.py (tag, middleware 403/allow, CRUD, seed, invalidación M2M)
- [x] Completar modulo de facturacion con NCF reales
- [x] Completar modulo de nomina con calculos TSS/ARS/ISR
- [x] Completar modulo de asistencia con QR/biometrico

## Apariencia y Centros
- [x] **Módulo de apariencia/tema** — Controlar colores de todos los elementos UI (para el final). Requiere:
  - Modelo `TemaCentro` o `ConfiguracionApariencia` (colores primario, secundario, acento, texto, fondo, etc.)
  - CSS variables (`--color-primary`, `--color-secondary`, etc.) en todos los archivos CSS
  - Panel de administración para editar colores con preview en vivo
  - Seed de temas por defecto (azul, verde, morado, etc.)
  - Aplicar tema al login, sidebar, botones, headers, cards
- [x] **Logo/imagen por centro** — Cada `CentroEducativo` tenga su propio logo. Requiere:
  - Campo `logo` (ImageField) en el modelo `CentroEducativo`
  - Migración + media root configurado
  - Mostrar logo en: sidebar, login, boletines, constancias, recibos, encabezados PDF
  - Formulario de subida de logo en configuración del centro
  - Placeholder por defecto si no tiene logo

## Independencia de Modulos (Planes de Venta)
- [x] **Cobros condicionados por plan del centro** - Cada modulo es independiente: sin caja/facturacion contratados ningun flujo se rompe ni genera deudas huerfanas. Requiere:
  - Servicio central modulo_activo(centro_id, nombre) - unica fuente de verdad (core/services.py, mapa FLAGS_MODULOS)
  - Gate de URLs por modulo: ModuloGateMiddleware bloquea /caja/ y /facturacion/ si el flag esta apagado, con aviso (core/middleware.py)
  - Home de cajero: si el centro no tiene caja activa, cierra sesion con mensaje en vez de redirigir a /caja/ (bucle evitado) (core/views.py)
  - Deuda/balance neutrales: 	iene_deuda_pendiente, deuda_detalle_estudiante y alance_por_concepto devuelven vacio si modulo_caja=False - constancias/kardex nunca se bloquean por deudas incobrables (caja/services.py)
  - Certificados gratuitos auto-aprobados: portal estudiante y tutor crean solicitud con monto=0, estado aprobada y pagado=True cuando no hay caja; panel muestra "Exenta" + Entregar/Imprimir, oculta "Cobrar en caja" (estudiantes/views.py, tutores/views.py, templates)
  - Pago en linea rechazado con mensaje claro para solicitudes gratuitas
  - Dashboard admin: tarjeta Recaudado y Ultimos pagos solo con caja activa; invalidacion de dashboard al guardar ConfiguracionCentro (administracion)
  - Portales: card "Estado de mis deudas" y secciones de pagos ocultas sin caja
  - Tests: core/tests_planes.py (matriz de planes: sin caja / caja sin facturacion / completo; 15 tests)
- [x] **Semilla de dos centros para verificar planes** - python manage.py seed_planes_demo (idempotente):
  - Centro A completo (seed_demo) con caja+facturación+certificados pagados () encendidos
  - Centro B "público" sin módulos de cobro, con años/grados/estudiantes/inscripciones y una asignación impaga que NO debe verse como deuda
  - Usuarios: director|secretaria|cajero + sufijo pb para B; estudiantes 202xxxxx / pb30xx
  - seed_demo ahora es idempotente en catálogos globales de nómina (get_or_create AFP/ARS/Cargo/TipoIngreso/TipoDescuento)
  - Script opcional de humo E2E: verify_planes.py (borrable)
- [x] **Kardex bloquea por deuda pendiente** - igual que constancias; candado en ficha del estudiante; al pagar se desbloquea; neutro sin módulo caja (4 tests nuevos en tests_planes.py)
- [x] **Acceso rápido a solicitudes** - botón "Solicitudes de certificados" en el dashboard (el enlace del sidebar vive dentro del submenú colapsado Estudiantes)
