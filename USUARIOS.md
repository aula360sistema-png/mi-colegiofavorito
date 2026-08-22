# Usuarios del sistema (datos demo)

Contraseñas por defecto generadas con `python manage.py seed_demo`.

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

| Usuario    | Contraseña  | Rol / Perfil   | Nombre             |
|------------|-------------|----------------|--------------------|
| admin      | admin123    | Superusuario   | Administrador      |
| director   | admin123    | Director       | Rosa Ventura       |
| secretaria | admin123    | Secretaria     | María Santana      |
| cajero     | admin123    | Cajero         | Juan Castillo      |
| docente    | docente123  | Docente        | Carlos Méndez      |
| docente2   | docente123  | Docente        | Laura Fernández    |
| docente3   | docente123  | Docente        | Felipe Rojas       |
| cajero1    | test1234    | Cajero         | María Elena Rodríguez |
| tutor1     | test1234    | Tutor          | Carlos Alberto Méndez |

## Estudiantes (usuario = matrícula)

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
