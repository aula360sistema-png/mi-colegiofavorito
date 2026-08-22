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
  - Modelo `PermisoPagina` (FK a `RolCentro` y/o `Usuario`)
  - Guard en vistas o middleware que verifique permisos
  - Panel de administración para gestionar permisos (CRUD)
  - Seed de permisos por defecto por rol
  - Template tag `{% has_perm_page 'nombre_url' %}` para ocultar enlaces en sidebar
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
