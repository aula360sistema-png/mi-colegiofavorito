# 5. Hoja de ruta técnica para vender mejor

> Brechas que conviene cerrar para que la propuesta comercial sea 100% creíble.
> Priorizadas por impacto en ventas (2026).

## 5.1 CRÍTICO: Facturación electrónica e-CF ante la DGII

**Estado actual:** el proyecto ya factura con **NCF** (secuencias y tipos de
comprobante, notas de crédito) y lleva cuentas por cobrar por estudiante.

**Brecha:** la **emisión/declaración electrónica (e-CF)** ante la DGII aún no
está conectada a un **proveedor autorizado** (ej. Alegra, FacturasRD, etc.).
En 2026 los comprobantes electrónicos son el argumento #1 del mercado y los
competidores locales ya publican la integración.

**Plan:**
1. Contratar un proveedor DGII autorizado (API REST) e integrar la emisión de
   e-CF desde la caja/portales (Tipo 31/32 y Notas de crédito).
2. Publicar el logotipo y certificado del proveedor en la propuesta comercial.
3. Tener fecha de entrega prometida en contratos ("entrega certificada 2026").

## 5.2 CRÍTICO: Pasarela de pago en línea (tarjeta RD)

**Brecha:** hoy el cobro es presencial/transferencia.

**Plan:** integrar una pasarela local (CardNet / RD$ o similar) para:
- Cobro de mensualidades desde el **portal del padre** (pago recurrente).
- Pagos de certificados y tienda del centro.
- Recibos/e-CF automáticos al confirmar el pago.
Impacto: ataca la **morosidad**, el dolor #2 de los colegios.

## 5.3 ALTO: Ajuste fino a la normativa MINERD

- Reportes/actas en los **formatos oficiales** que pide cada distrito escolar
  (el módulo de acta de sección ya existe; pulir plantillas y exportación).
- Soporte del **calendario escolar MINERD** y feriados por distrito.
- KPI de promoción/deserción alineados a los indicadores del MINERD.
Impacto: ganas el "punto técnico" frente a distrito; hoy ya está el 80%.

## 5.4 ALTO: Imagen comercial y venta digital

| Acción | Por qué |
|---|---|
| **Landing page** con nombre comercial propio (.com.do) | credibilidad y captura de prospectos |
| **Demos automatizadas** / video de 3 min | califica interesados antes del WhatsApp |
| **Caso de éxito** (1-2 colegios piloto con testimonios) | el mercado educativo compra por referencia |
| **Branding** de la marca: colores/logo del producto | coherencia ante colegios |
| **Precios publicados** en la web | transparencia, filtra curiosos |

## 5.5 MEDIO: Experiencia móvil

- Portales correctamente responsivos (hoy funcionan en móvil; pulir)
  y **notificaciones** a padres (recordatorios de pago, notas, comunicados).
- Evaluar PWA en lugar de app nativa (coste cero almacén).

## 5.6 MEDIO: Automatizaciones que dependan de la DGII

- Generación automática de recordatorios de mora (el módulo de **Alertas**
  ya existe; conectarlo a WhatsApp/correo transaccional).
- Comunicados por grado/sección desde el panel del director.

## 5.7 BAJO (pero vende en cadenas): panel de red

- Reportes **consolidados multi-centro** (matrícula, morosidad, rendimiento)
  con drill-down por colegio. La base multi-centro ya existe; falta la vista
  gerencial de red.

## 5.8 Operación y gobernanza

- Ambiente estable de **producción separado de demo**, migraciones versionadas
  y `seed_permisos` corriendo siempre en deploy (ya automático en Render).
- Contrato/SLA modelo, **términos de procesamiento de datos** y política de
  respaldos documentados (Ley 172-13).
- Inventario de cuentas con acceso (superadmin) y rotación de 2FA.

## Prioridad sugerida

| Semana | Hito |
|---|---|
| 1-4 | Landing + branding + caso de éxito piloto (2 colegios) |
| 4-8 | Integración proveedor e-CF DGII (validado con el proveedor) |
| 8-12 | Pasarela de pago en línea en portales |
| 12-16 | Plantillas MINERD + panel de red multi-centro |
| continuo | Testimonios, referidos, segundo caso de éxito |