# Usuarios del sistema (datos demo)

Contraseñas por defecto generadas con los comandos de `seed`:

- `python manage.py seed_demo` → **`admin123` / `docente123` / `estudiante123`**
- `python manage.py seed_data` → **`test1234`**

> **Seguridad:** estas contraseñas son solo para desarrollo/demo. En producción cambia
> todas las contraseñas desde **Cambiar contraseña** (menú lateral) o el formulario
> `POST /usuarios/password/`. El login bloquea la cuenta 15 minutos tras 5 intentos
> fallidos, la sesión se cierra tras 30 min de inactividad, la contraseña caduca a
> los 90 días, y todos los eventos quedan registrados en la Bitácora y en `logs/security.log`.

## Acceso demo con 2FA

El usuario **admin** tiene **2FA activado**. Para entrar:

1. Agrega la clave base32 en Google Authenticator, Authy o similar:
   `JBSWY3DPEHPK3PXP`
2. Inicia sesión con `admin` / `admin123` y luego ingresa el código de 6 dígitos.

El 2FA es **obligatorio para roles `admin` y `superadmin`**. Los demás roles pueden
activarlo/desactivarlo en **Mi seguridad** (menú lateral) o en `POST /usuarios/gestionar-2fa/`.

## Administración y roles

| Usuario    | Contraseña  | Rol / Perfil   | Nombre                    |
|------------|-------------|----------------|---------------------------|
| admin      | admin123    | Superusuario   | Administrador            |
| director   | admin123    | Director       | Rosa Ventura             |
| secretaria | admin123    | Secretaria     | María Santana            |
| cajero     | admin123    | Cajero         | Juan Castillo            |
| cajero1    | test1234    | Cajero         | María Elena Rodríguez    |
| tutor1     | test1234    | Tutor          | Carlos Alberto Méndez    |

## Docentes

| Usuario       | Contraseña  | Nombre             | Origen        |
|---------------|-------------|--------------------|---------------|
| docente       | docente123  | Carlos Méndez      | seed_demo     |
| docente2      | docente123  | Laura Fernández    | seed_demo     |
| docente3      | docente123  | Felipe Rojas       | seed_demo     |
| docente1      | test1234    | Juan Perez         | seed_data     |
| docente4      | test1234    | Ana López          | seed_data     |
| docente5      | test1234    | Luis Martínez      | seed_data     |
| 131-0000136-4 | *no documentada* | Nidia Karina Betances Parra | creado manualmente |

> La cuenta `131-0000136-4` fue creada manualmente (fuera de los seeds), por lo que su
> contraseña no puede determinarse desde el código. Si la olvidaste, reasígnala con
> `python manage.py changepassword 131-0000136-4`.

## Estudiantes (usuario = matrícula)

Usuarios creados por `seed_demo` (contraseña **`estudiante123`**):

| Usuario | Contraseña     | Estudiante              |
|---------|----------------|-------------------------|
| 20170001| estudiante123  | Ana María Pérez         |
| 20200001| estudiante123  | Carmen Elena Duarte     |
| 20210001| estudiante123  | Luis Carlos Rodríguez   |
| 20210002| estudiante123  | Pedro Antonio Sánchez   |
| 20220001| estudiante123  | Juana Isabel Reyes      |
| 20220002| estudiante123  | José Miguel Santos      |
| 20230001| estudiante123  | María Fernanda Gómez    |
| 20240001| estudiante123  | Rosa Amelia Guzmán      |
| 20240002| estudiante123  | Miguel Ángel Peña       |

Usuarios creados por `seed_data` (matrículas `EST-2025-XXXX`, contraseña **`test1234`**):

> Hay 30 estudiantes `EST-2025-0001` … `EST-2025-0030` con contraseña `test1234`
> (usuario = matrícula, p. ej. `EST-2025-0001` / `test1234`).

## Otros usuarios de prueba (contraseña no documentada)

| Usuario     | Rol        | Nota                                          |
|-------------|------------|-----------------------------------------------|
| superadmin  | superadmin | Creado aparte (`createsuperuser`/bootstrap)    |
| est_mat-r01 | estudiante | Usuario de pruebas creado manualmente         |
| est_mat-r02 | estudiante | Usuario de pruebas creado manualmente         |
| 123456      | estudiante | Usuario de pruebas creado manualmente         |
| 1234567     | estudiante | Usuario de pruebas creado manualmente         |

> Estos usuarios no provienen de ningún seed, por lo que su contraseña no está
> documentada. Puedes reasignarla con `python manage.py changepassword <usuario>`.
