# Correo bloqueado en Render (puerto 587) — Diagnóstico y solución

## 1. Diagnóstico: esto NO es un bug de tu código

Es una restricción real de Render, documentada oficialmente:

> Desde el **26 de septiembre de 2025**, los **web services gratuitos (plan `free`)** de Render bloquean **todo el tráfico saliente hacia los puertos SMTP 25, 465 y 587**. Para seguir usando SMTP hay que subir a cualquier plan de pago. El puerto 25 queda bloqueado siempre (incluso en pago), porque Render corre sobre AWS EC2 y EC2 bloquea el 25 por defecto anti-spam; los puertos 465 y 587 sí funcionan normalmente en planes pagos.
> — Render Changelog, [render.com/changelog/free-web-services-will-no-longer-allow-outbound-traffic-to-smtp-ports](https://render.com/changelog/free-web-services-will-no-longer-allow-outbound-traffic-to-smtp-ports)

**Confirmé en tu repo que este es exactamente tu caso:**

```yaml
# render.yaml
services:
  - type: web
    name: mycolegiofavorito
    plan: free        # ← aquí está la causa
```

Y tu configuración de correo (`mycolegiofavorito/settings.py`, `comunicaciones/services/email.py`) está correctamente armada para SMTP estándar de Django (`EMAIL_HOST`, `EMAIL_PORT=587`, `EMAIL_USE_TLS`) — el código no tiene ningún error. El bloqueo pasa **antes** de que tu aplicación logre siquiera abrir el socket TCP hacia Gmail; por eso normalmente se ve como un **timeout de conexión**, no como un error de autenticación o de credenciales.

Dato adicional importante para tu caso específico: aunque uses Gmail SMTP, Google además **no permite usar contraseña normal de cuenta para SMTP** — exige "Contraseña de aplicación" (App Password) con verificación en 2 pasos activada, o OAuth2. Pero eso es un problema aparte que solo importaría *después* de resolver el bloqueo de Render.

---

## 2. Opciones de solución (de más simple/barata a más robusta)

### Opción A — Subir el web service a un plan pago de Render
Es la solución más directa si solo necesitas que SMTP funcione tal cual está.

- En el dashboard de Render → tu servicio → Settings → cambiar `plan: free` por `starter` (o el que uses) en `render.yaml`, o cambiarlo desde la UI.
- Con esto, el puerto 587 (TLS) y 465 (SSL) dejan de estar bloqueados; el 25 sigue bloqueado siempre, pero no lo necesitas (Gmail usa 587/465).
- No requiere tocar código.
- **Contras:** cuesta dinero solo por esto, y si tu app ya iba a necesitar plan pago por otras razones (que no duerma, más RAM, etc.), tiene más sentido. Si solo la subes por el correo, quizás la Opción B te sale más barata o gratis.

### Opción B — Enviar correo por API HTTP en vez de SMTP (recomendada)
Esta es la opción que más equipos usan hoy en Render/Heroku/similares, porque **no depende de puertos SMTP en absoluto** — el envío se hace por HTTPS (puerto 443), que nunca está bloqueado.

Servicios con API HTTP y buen soporte para Django, con plan gratuito:
- **Resend** — API muy simple, 100 correos/día gratis, tiene SDK oficial y también funciona como backend SMTP-compatible si prefieres.
- **SendGrid** — 100 correos/día gratis en el plan free actual; **ojo:** si usas SendGrid vía SMTP (puerto 587) desde Render free, **sigue bloqueado igual** — tienes que usar su API HTTP (`sendgrid` SDK o `requests` a su endpoint REST), no su SMTP relay.
- **Mailgun** / **Postmark** — planes gratuitos limitados, también con API HTTP.

**Cómo se integraría en tu proyecto concreto (Django):**

La forma más limpia es usar `django-anymail`, que soporta estos proveedores por API HTTP con la misma interfaz de `django.core.mail` que ya usa tu código en `comunicaciones/services/email.py` (usa `send_mail`, `EmailMessage`) — **no tendrías que reescribir la lógica de envío, solo cambiar el backend**.

```bash
pip install django-anymail
```

```python
# settings.py
EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"  # o sendgrid, mailgun, postmark...
ANYMAIL = {
    "RESEND_API_KEY": os.getenv("RESEND_API_KEY"),
}
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "notificaciones@mi-colegio.com")
```

Como tu `EMAIL_BACKEND` ya se resuelve dinámicamente por variable de entorno en `settings.py`, el cambio en producción sería solo agregar la variable de entorno correspondiente en Render (no tocar código en absoluto si generalizas un poco esa lógica).

**Contras:** requiere verificar el dominio remitente (SPF/DKIM) en el proveedor elegido para que los correos no caigan en spam — es un paso de configuración de una sola vez, no recurrente.

### Opción C — Servidor SMTP intermedio en un servicio que sí permita el puerto
Menos recomendable, pero existe: correr un relay SMTP en otra plataforma (ej. una VM en otro proveedor, o un contenedor en Fly.io/Railway que no bloquee el puerto) y que tu app en Render le hable por HTTPS a ese relay. Es más infraestructura para mantener sin beneficio real sobre la Opción B, así que solo tendría sentido si ya tienes esa infraestructura por otra razón.

---

## 3. Mi recomendación concreta para tu proyecto

Dado que:
- Tu `render.yaml` ya está en plan `free` (probablemente a propósito, para no pagar mientras el colegio no está en producción real),
- Tu código de correo ya está bien abstraído detrás de `EMAIL_BACKEND`,
- El volumen de correo de un colegio (notificaciones puntuales, no marketing masivo) encaja perfecto en los límites gratuitos de Resend o SendGrid,

**Te conviene la Opción B (API HTTP vía `django-anymail`)** antes que pagar un plan de Render solo por SMTP. Mantiene el plan free de Render para todo lo demás, y es la solución que no se te vuelve a romper si en el futuro cambias de proveedor de hosting.

Si en algún momento el colegio crece y de todas formas vas a necesitar plan pago en Render (por rendimiento, que no "duerma" el servicio, etc.), entonces ahí sí la Opción A se vuelve gratis en el sentido de que ya la estás pagando por otra razón, y podrías quedarte con SMTP normal si prefieres no depender de un tercero.

---

## 4. Pasos siguientes si quieres que te ayude a implementarlo

Puedo:
1. Modificar `mycolegiofavorito/settings.py` para soportar `django-anymail` con Resend o SendGrid, dejando el fallback a consola en desarrollo tal como está ahora.
2. Actualizar `comunicaciones/services/email.py` si hace falta algún ajuste puntual (probablemente ninguno, ya que usa las funciones estándar de Django).
3. Dejarte el `render.yaml` con las variables de entorno correctas comentadas, como ya tienes el bloque preparado para SendGrid SMTP (que habría que cambiar a la variante API, no SMTP).

Dime cuál proveedor prefieres (Resend, SendGrid o Mailgun) y lo dejo implementado.
