# Mi Colegio Favorito

Sistema integral de gestión escolar multi-centro: matrícula, notas y kardex,
asistencia, disciplina, nómina docente, biblioteca, transporte, caja
(facturación y recibos), certificados con flujo de aprobación/cobro/entrega,
comunicaciones (correo/WhatsApp) y dashboard administrativo.

Cada centro educativo contrata **módulos** de forma independiente: los flujos
de módulos inactivos se desactivan solos (gate de URLs, portales sin cobros,
certificados gratuitos auto-aprobados, deuda neutral).

## Stack

- Python 3.14 · Django 6 · PostgreSQL (o SQLite en desarrollo)
- Whitenoise · Gunicorn · Redis opcional para caché
- 2FA (TOTP) · control de permisos por página y rol

## Desarrollo local

```bash
pip install -r requirements.txt
copy .env.example .env        # configurar SECRET_KEY
python manage.py migrate
python manage.py seed_demo    # datos demo del centro principal
python manage.py runserver
```

## Producción (Render)

El repositorio incluye un Blueprint (`render.yaml`): en
[dashboard.render.com](https://dashboard.render.com) → New + → Blueprint →
conectar este repo. El primer deploy crea web service + base PostgreSQL,
aplica migraciones y sirve estáticos con Whitenoise.

Crear el superadmin inicial (Shell del servicio):

```bash
DJANGO_SUPERUSER_PASSWORD='...' python manage.py bootstrap_superuser
```

## Tests

```bash
python manage.py test
```

> Documentación adicional en `PENDIENTES.md` y `docs/`.
