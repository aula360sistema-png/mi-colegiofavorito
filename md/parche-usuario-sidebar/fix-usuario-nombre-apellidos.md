# Fix: Usuario se crea sin nombre/apellidos — Implementado

## Qué se hizo
`UsuarioManager.create_user()` ahora acepta `first_name`/`last_name`, y los 4 puntos que crean un `Usuario` (docente, estudiante, tutor, administrativo) le pasan el nombre real de la persona en vez de dejarlo vacío.

## Archivos modificados
| Archivo | Cambio |
|---|---|
| `usuarios/models.py` | `UsuarioManager.create_user()` acepta `first_name='', last_name=''` |
| `docentes/views.py` | `docente_create` pasa `docente.primer_nombre` / apellidos |
| `estudiantes/views.py` | pasa `estudiante.primer_nombre` / apellidos |
| `tutores/views.py` | pasa `tutor.primer_nombre` / apellidos |
| `administracion/views.py` | pasa `admin.primer_nombre` / apellidos |

Los 4 modelos (`Docente`, `Estudiante`, `Tutor`, `Administrativo`) usan los mismos nombres de campo (`primer_nombre`, `primer_apellido`, `segundo_apellido`), así que el patrón es idéntico en los 4 lugares:

```python
usuario = Usuario.objects.create_user(
    username=...,
    email=...,
    password=password,
    first_name=persona.primer_nombre,
    last_name=f"{persona.primer_apellido} {persona.segundo_apellido or ''}".strip(),
)
```

## Verificación
```
python manage.py test usuarios docentes estudiantes tutores administracion
Ran 96 tests — OK
```
Ninguna migración necesaria (los campos ya existían en `Usuario`).

## Cómo aplicarlo
1. Descomprime `parche-usuario-sidebar.zip`.
2. Copia los 5 archivos `.py` de esta lista sobre tu repo (mismas rutas).
3. `python manage.py test usuarios docentes estudiantes tutores administracion` para confirmar en tu entorno.

## Pendiente (no incluido en este fix, a propósito)
Los usuarios que **ya existen** con nombre vacío no se corrigen retroactivamente con este cambio — solo afecta a los que se creen de ahora en adelante. Si quieres, en otra sesión armamos un script de una sola corrida que recorra `Docente`/`Estudiante`/`Tutor`/administrativos existentes y copie el nombre al `Usuario` vinculado que ya tienen.
