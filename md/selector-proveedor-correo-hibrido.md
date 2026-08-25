# Selector de proveedor de correo (híbrido) — Diseño para "Configuración de Comunicaciones"

## 0. Contexto: lo que ya existe (y por qué no basta tal cual)

Ya tienes, en `core.ConfiguracionCentro`, una sección de correo por centro (`email_servidor`, `email_puerto`, `email_usuario`, `email_clave`, `email_tls`, `email_ssl`, `email_remitente`), editable desde `ConfiguracionCentroForm` (`core/forms.py`) en la vista de configuración (`core/views.py`), con botón de **"correo de prueba"** ya implementado (`comunicaciones/services/email.py: enviar_correo_prueba`).

**El problema:** esos campos asumen siempre SMTP. Si el centro está en Render plan `free`, **no importa qué host SMTP ponga el usuario (Gmail, Outlook, SendGrid-SMTP, lo que sea) — el puerto sigue bloqueado a nivel de red**, y el correo de prueba seguirá fallando por timeout sin importar que los datos estén bien.

**La solución híbrida que pides:** agregar un selector de "tipo de proveedor" arriba de esos campos. Según lo que el usuario elija, el formulario muestra solo los campos relevantes (SMTP clásico *o* API key de un proveedor HTTP), y el backend de envío decide cómo mandar el correo según esa elección — sin que el usuario necesite saber nada de puertos ni de Render.

---

## 1. Experiencia de usuario (UI)

En la pantalla de Configuración → Comunicaciones, reemplazar el bloque fijo de "Correo" por:

```
┌─────────────────────────────────────────────────┐
│  Proveedor de correo                             │
│  ○ Gmail / Google Workspace (SMTP)               │
│  ○ Outlook / Microsoft 365 (SMTP)                │
│  ○ Otro servidor SMTP (personalizado)            │
│  ○ Resend (recomendado en plan gratuito Render)  │
│  ○ SendGrid (API)                                │
│  ○ Mailgun (API)                                 │
│  ○ Ninguno (modo consola / desarrollo)           │
└─────────────────────────────────────────────────┘
```

Al elegir una opción, el formulario muestra **solo** los campos que ese proveedor necesita (con JS simple, mostrar/ocultar `div`s — no hace falta recargar la página):

| Proveedor | Campos que se muestran | Ayuda visible en el form |
|---|---|---|
| Gmail / Workspace | Correo, Clave de aplicación, Remitente | "Genera una 'contraseña de aplicación' en myaccount.google.com/apppasswords (requiere verificación en 2 pasos activada). No uses tu contraseña normal." + aviso: "Si tu hosting está en plan gratuito de Render, Gmail SMTP no funcionará por bloqueo de puertos; usa Resend o SendGrid." |
| Outlook / M365 | Correo, Clave de aplicación, Remitente | Similar, con link a la doc de Microsoft |
| Otro SMTP | Servidor, Puerto, Usuario, Clave, TLS/SSL, Remitente | Los campos que ya existen hoy, tal cual |
| Resend | API Key, Remitente | "Crea una cuenta gratis en resend.com, verifica tu dominio y pega la API key aquí." |
| SendGrid | API Key, Remitente | "Usa tu API Key de SendGrid (no el usuario/clave SMTP)." |
| Mailgun | API Key, Dominio, Remitente | — |
| Ninguno | (nada) | "Los correos se mostrarán en el log del servidor, no se enviarán realmente. Úsalo solo en desarrollo." |

El botón **"Enviar correo de prueba"** se mantiene igual para todos los proveedores — es la forma en que el usuario valida que eligió bien, sin que le tengas que explicar nada técnico de Render.

---

## 2. Cambios de modelo (`core/models.py`)

Agregar a `ConfiguracionCentro`:

```python
class ConfiguracionCentro(models.Model):
    ...
    PROVEEDORES_CORREO = (
        ('smtp_gmail', 'Gmail / Google Workspace (SMTP)'),
        ('smtp_outlook', 'Outlook / Microsoft 365 (SMTP)'),
        ('smtp_otro', 'Otro servidor SMTP'),
        ('resend', 'Resend (API)'),
        ('sendgrid', 'SendGrid (API)'),
        ('mailgun', 'Mailgun (API)'),
        ('consola', 'Ninguno (modo consola / desarrollo)'),
    )

    email_proveedor = models.CharField(
        'Proveedor de correo',
        max_length=20,
        choices=PROVEEDORES_CORREO,
        default='consola',
    )

    # Los campos SMTP existentes (email_servidor, email_puerto, email_usuario,
    # email_clave, email_tls, email_ssl) se REUTILIZAN para
    # smtp_gmail / smtp_outlook / smtp_otro — no hace falta duplicarlos.
    # Para gmail/outlook, el servidor y puerto se autocompletan en el
    # backend (el usuario no los ve ni los edita).

    # Nuevo: para proveedores API HTTP
    email_api_key = models.CharField(
        'API Key del proveedor',
        max_length=300,
        blank=True,
        default='',
        help_text='API Key de Resend, SendGrid o Mailgun, según el proveedor elegido.',
    )
    email_dominio_api = models.CharField(
        'Dominio (solo Mailgun)',
        max_length=200,
        blank=True,
        default='',
        help_text='Dominio verificado en Mailgun, ej: mg.tudominio.com',
    )
    # email_remitente ya existe y se reutiliza para todos los proveedores.
```

Migración estándar (`python manage.py makemigrations core`).

---

## 3. Cambios de formulario (`core/forms.py`)

Agregar `email_proveedor`, `email_api_key`, `email_dominio_api` a `ConfiguracionCentroForm.Meta.fields`, y agregar la clase de JS/HTML (`data-proveedor-correo`) a cada campo relacionado para que el template pueda mostrarlos/ocultarlos dinámicamente según el valor de `email_proveedor` (puede ser JS plano, no requiere librería).

Ejemplo de bloque en el template (`core/templates/core/configuracion_centro.html` o donde viva):

```html
<select name="email_proveedor" id="id_email_proveedor" onchange="mostrarCamposCorreo(this.value)">
  {% for value, label in form.email_proveedor.field.choices %}
    <option value="{{ value }}" {% if form.email_proveedor.value == value %}selected{% endif %}>
      {{ label }}
    </option>
  {% endfor %}
</select>

<div id="bloque-smtp-generico" class="campos-correo">
  {{ form.email_servidor }} {{ form.email_puerto }}
  {{ form.email_tls }} {{ form.email_ssl }}
</div>

<div id="bloque-smtp-credenciales" class="campos-correo">
  {{ form.email_usuario }} {{ form.email_clave }}
</div>

<div id="bloque-api" class="campos-correo">
  {{ form.email_api_key }}
</div>

<div id="bloque-mailgun-dominio" class="campos-correo">
  {{ form.email_dominio_api }}
</div>

{{ form.email_remitente }}  {# siempre visible, para todos los proveedores #}

<script>
function mostrarCamposCorreo(proveedor) {
  const smtpGenerico = document.getElementById('bloque-smtp-generico');
  const smtpCred = document.getElementById('bloque-smtp-credenciales');
  const api = document.getElementById('bloque-api');
  const mailgunDominio = document.getElementById('bloque-mailgun-dominio');

  const esSmtp = ['smtp_gmail', 'smtp_outlook', 'smtp_otro'].includes(proveedor);
  const esApi = ['resend', 'sendgrid', 'mailgun'].includes(proveedor);

  // Servidor/puerto/TLS solo se editan a mano en "otro SMTP";
  // gmail/outlook los autocompleta el backend.
  smtpGenerico.style.display = (proveedor === 'smtp_otro') ? '' : 'none';
  smtpCred.style.display = esSmtp ? '' : 'none';
  api.style.display = esApi ? '' : 'none';
  mailgunDominio.style.display = (proveedor === 'mailgun') ? '' : 'none';
}
document.addEventListener('DOMContentLoaded', () => {
  mostrarCamposCorreo(document.getElementById('id_email_proveedor').value);
});
</script>
```

---

## 4. Cambios de backend — `comunicaciones/services/configuracion.py` y `email.py`

`obtener_configuracion_correo(centro)` pasa a devolver también `proveedor`, y a autocompletar host/puerto para Gmail/Outlook:

```python
HOSTS_CONOCIDOS = {
    'smtp_gmail': {'host': 'smtp.gmail.com', 'port': 587, 'tls': True, 'ssl': False},
    'smtp_outlook': {'host': 'smtp.office365.com', 'port': 587, 'tls': True, 'ssl': False},
}

def obtener_configuracion_correo(centro):
    cfg = _configuracion_de(centro)
    if not cfg:
        return _fallback_settings()

    proveedor = cfg.email_proveedor or 'consola'

    if proveedor in HOSTS_CONOCIDOS:
        preset = HOSTS_CONOCIDOS[proveedor]
        return {
            'proveedor': proveedor,
            'host': preset['host'],
            'port': preset['port'],
            'user': cfg.email_usuario,
            'password': cfg.email_clave,
            'use_tls': preset['tls'],
            'use_ssl': preset['ssl'],
            'from_email': cfg.email_remitente or settings.DEFAULT_FROM_EMAIL,
        }

    if proveedor == 'smtp_otro':
        return {
            'proveedor': proveedor,
            'host': cfg.email_servidor,
            'port': cfg.email_puerto or 587,
            'user': cfg.email_usuario,
            'password': cfg.email_clave,
            'use_tls': cfg.email_tls and not cfg.email_ssl,
            'use_ssl': cfg.email_ssl,
            'from_email': cfg.email_remitente or settings.DEFAULT_FROM_EMAIL,
        }

    if proveedor in ('resend', 'sendgrid', 'mailgun'):
        return {
            'proveedor': proveedor,
            'api_key': cfg.email_api_key,
            'dominio_api': cfg.email_dominio_api,
            'from_email': cfg.email_remitente or settings.DEFAULT_FROM_EMAIL,
        }

    # 'consola' o vacío -> backend de consola
    return {'proveedor': 'consola', 'from_email': cfg.email_remitente or settings.DEFAULT_FROM_EMAIL}
```

Y `_conexion(config)` en `email.py` se convierte en el punto único que decide **cómo** mandar, según `config['proveedor']`:

```python
def _conexion(config):
    proveedor = config.get('proveedor', 'consola')

    if proveedor == 'consola':
        return get_connection(backend='django.core.mail.backends.console.EmailBackend')

    if proveedor in ('smtp_gmail', 'smtp_outlook', 'smtp_otro'):
        return get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=config['host'],
            port=config['port'],
            username=config['user'],
            password=config['password'],
            use_tls=config['use_tls'],
            use_ssl=config['use_ssl'],
            timeout=getattr(settings, 'EMAIL_TIMEOUT', 30),
            fail_silently=False,
        )

    if proveedor == 'resend':
        return get_connection(
            backend='anymail.backends.resend.EmailBackend',
            api_key=config['api_key'],
        )

    if proveedor == 'sendgrid':
        return get_connection(
            backend='anymail.backends.sendgrid.EmailBackend',
            api_key=config['api_key'],
        )

    if proveedor == 'mailgun':
        return get_connection(
            backend='anymail.backends.mailgun.EmailBackend',
            api_key=config['api_key'],
            sender_domain=config['dominio_api'],
        )

    raise ValueError(f"Proveedor de correo no soportado: {proveedor}")
```

**Nota clave:** esto requiere instalar `django-anymail` (`pip install django-anymail`) y agregarlo a `INSTALLED_APPS`. El resto del código de `email.py` (`enviar_email`, `enviar_email_pago`, `enviar_correo_prueba`, etc.) **no cambia nada** — ya usan `send_mail(..., connection=_conexion(config))`, así que el cambio queda 100% encapsulado en esa función.

---

## 5. Validación del formulario según proveedor elegido

En `ConfiguracionCentroForm.clean()`, agregar validación condicional para que el director no pueda guardar una config incompleta (ej. eligió "Resend" pero dejó la API key vacía):

```python
def clean(self):
    cleaned = super().clean()
    proveedor = cleaned.get('email_proveedor')

    if proveedor in ('smtp_gmail', 'smtp_outlook'):
        if not cleaned.get('email_usuario') or not cleaned.get('email_clave'):
            raise forms.ValidationError(
                'Debes indicar el correo y la clave de aplicación.'
            )
    elif proveedor == 'smtp_otro':
        if not cleaned.get('email_servidor'):
            raise forms.ValidationError('Debes indicar el servidor SMTP.')
    elif proveedor in ('resend', 'sendgrid', 'mailgun'):
        if not cleaned.get('email_api_key'):
            raise forms.ValidationError('Debes indicar la API Key del proveedor.')
        if proveedor == 'mailgun' and not cleaned.get('email_dominio_api'):
            raise forms.ValidationError('Mailgun requiere el dominio verificado.')

    return cleaned
```

---

## 6. Aviso proactivo si el centro está en Render free + eligió SMTP

Detalle de UX que evita que el usuario pierda tiempo probando algo que sabemos que va a fallar por la red, no por sus datos: si detectas (por variable de entorno, ej. `RENDER=true` y `RENDER_PLAN` si Render la expone, o simplemente un flag manual `HOSTING_BLOQUEA_SMTP=True` que tú controlas en `.env` según el plan que tengas contratado) que el hosting bloquea SMTP, mostrar un banner de advertencia junto al selector cuando el usuario elige un proveedor SMTP:

```
⚠️ Tu plan de hosting actual bloquea el envío por SMTP (puertos 25/465/587).
   Te recomendamos elegir Resend o SendGrid (API), que sí funcionan en tu plan.
   Puedes seguir usando SMTP si cambias a un plan de hosting pago.
```

Esto es opcional, pero le ahorra al usuario final (director/secretaria, no programador) el ciclo de "configuré Gmail → probé → no llega → no sé por qué".

---

## 7. Resumen de lo que hay que tocar

| Archivo | Cambio |
|---|---|
| `core/models.py` | Agregar `email_proveedor`, `email_api_key`, `email_dominio_api` a `ConfiguracionCentro` + migración |
| `core/forms.py` | Agregar los 3 campos al `ConfiguracionCentroForm`, widgets, y `clean()` con validación condicional |
| Template de configuración | Selector de proveedor + bloques condicionales con JS para mostrar/ocultar campos |
| `comunicaciones/services/configuracion.py` | `obtener_configuracion_correo()` devuelve `proveedor` y autocompleta host/puerto de Gmail/Outlook |
| `comunicaciones/services/email.py` | `_conexion()` decide el backend (SMTP o Anymail) según `proveedor` |
| `requirements.txt` | Agregar `django-anymail` |
| `settings.py` | Agregar `'anymail'` a `INSTALLED_APPS` |

Todo lo demás del módulo de comunicaciones (`enviar_email`, `enviar_email_pago`, `enviar_correo_prueba`, campañas, etc.) sigue funcionando sin tocarse, porque ya pasa por `_conexion(config)`.

---

## 8. ¿Seguimos con la implementación?

Si quieres, lo implemento directo en el repo (modelo + migración + form + template + servicios) y te dejo el `pip install django-anymail` agregado a `requirements.txt`. Solo dime si prefieres que el "Otro SMTP" también quede disponible o si por ahora solo quieres Gmail/Outlook/Resend/SendGrid activos en el selector.
