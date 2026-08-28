# Selector de proveedor de correo — Implementación lista

Ya implementé, probé (61 tests del módulo + 341 de todo el proyecto, todos en verde) y empaqueté los cambios. Esto es lo que hice y cómo lo aplicas.

## 1. Qué se agregó

Selector de proveedor de correo en **Configuración → Correo y WhatsApp**, con 6 opciones:

- Gmail / Google Workspace (SMTP) — host y puerto se autocompletan, solo pides correo + clave de aplicación
- Outlook / Microsoft 365 (SMTP) — igual, autocompletado
- Otro servidor SMTP (personalizado) — los campos manuales que ya existían (servidor, puerto, TLS/SSL)
- Resend (API) — solo pide API Key
- SendGrid (API) — solo pide API Key
- Ninguno (modo consola / desarrollo)

El formulario muestra/oculta los campos según lo que elijas (JS simple, sin librerías nuevas en el frontend). El botón de "correo de prueba" que ya existía sigue funcionando igual para cualquier proveedor.

## 2. Archivos modificados (están en el zip adjunto)

| Archivo | Qué cambió |
|---|---|
| `core/models.py` | Nuevos campos `email_proveedor` y `email_api_key` en `ConfiguracionCentro` |
| `core/migrations/0015_agregar_proveedor_correo.py` | Migración ya generada, probada contra BD limpia |
| `core/forms.py` | Selector agregado al form + validación condicional según proveedor elegido |
| `core/templates/core/configuracion_centro.html` | UI del selector + bloques que se muestran/ocultan + banner opcional de aviso si el hosting bloquea SMTP |
| `comunicaciones/services/configuracion.py` | Resuelve la config según proveedor (autocompleta host de Gmail/Outlook, arma dict de API key para Resend/SendGrid) |
| `comunicaciones/services/email.py` | `_conexion()` decide el backend real de envío (SMTP o Anymail) según proveedor — es el único punto que cambió de comportamiento |
| `requirements.txt` | Se agregó `django-anymail==14.1` |
| `mycolegiofavorito/settings.py` | Se agregó `'anymail'` a `INSTALLED_APPS` |
| `core/tests.py`, `comunicaciones/tests.py` | 3 tests legacy actualizados para reflejar el nuevo selector (antes asumían SMTP implícito) |

**Nada más se tocó.** El resto del envío de correos (campañas, notificaciones de pago, avisos de vencimiento) sigue funcionando exactamente igual porque todo pasa por la misma función `_conexion()`.

## 3. Cómo aplicarlo en tu repo

1. Descarga y descomprime `selector-correo-cambios.zip`.
2. Copia cada archivo sobre la ruta correspondiente en tu repo local (mismos paths, así que puedes simplemente arrastrar la carpeta encima si tu editor lo permite, o copiar uno por uno).
3. Instala la dependencia nueva:
   ```bash
   pip install django-anymail --break-system-packages
   ```
   (o `pip install -r requirements.txt` de nuevo, ya que lo agregué ahí)
4. Aplica la migración:
   ```bash
   python manage.py migrate core
   ```
5. Verifica que todo sigue en verde:
   ```bash
   python manage.py test core comunicaciones
   ```
6. Haz commit y push como siempre (yo no tengo forma de hacer `git push` a tu repo, así que ese paso es tuyo).

## 4. Cómo probarlo después de desplegar

1. Entra como director → Configuración → Correo y WhatsApp.
2. Elige "Resend (API)" (o el que quieras probar).
3. Pega la API Key y el correo remitente.
4. Guarda.
5. Baja a la sección "Probar configuración de correo" y dale a "Enviar correo de prueba".
6. Si te llega, quedó funcionando — y ya no depende de que Render bloquee o no el puerto SMTP.

## 5. Nota sobre Resend/SendGrid y dominios

Para que los correos no caigan en spam, ambos proveedores piden verificar tu dominio remitente (agregar unos registros DNS tipo TXT/CNAME que ellos te dan al crear la cuenta). Es un paso de una sola vez en el panel de Resend o SendGrid, no algo que se configure en el código.

## 6. Pendiente opcional (no implementado, lo dejo anotado)

El banner de aviso "tu hosting bloquea SMTP" que puse en el template depende de una variable `hosting_bloquea_smtp` en el contexto de la vista, que hoy no se está pasando (por defecto queda oculto, no rompe nada). Si en algún momento quieres activarlo, solo hay que agregar esa variable al `context` de la vista `configuracion_centro` en `core/views.py`, por ejemplo en base a una variable de entorno que tú controles según tu plan de Render.
