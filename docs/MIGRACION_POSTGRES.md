# Migración a PostgreSQL (y backups)

Este proyecto funciona con **SQLite o PostgreSQL sin cambiar una línea de
código**. El motor se elige con una sola variable en el `.env`.

---

## 1. Cómo funciona el cambio

En `mycolegiofavorito/settings.py` la configuración de BD lee `DB_ENGINE`:

| Valor            | Motor       | Cuándo usarlo                          |
|------------------|-------------|----------------------------------------|
| `DB_ENGINE=sqlite`     | SQLite   | Desarrollo local, un solo servidor      |
| `DB_ENGINE=postgresql` | PostgreSQL | Producción, varios workers/servidores |

Todo lo demás (modelos, vistas, admin) es idéntico: Django abstrae el motor.

---

## 2. Poner en marcha PostgreSQL

### Opción A — Docker (recomendada)

```powershell
docker compose up -d          # levanta postgres:17 en 127.0.0.1:5432
docker compose logs -f db     # espera a ver "database system is ready"
```

Los datos persisten en el volumen `pgdata` aunque apagues el contenedor.
Las credenciales del `docker-compose.yml` coinciden con las del `.env`.

> Si no tienes Docker Desktop: instálalo desde https://www.docker.com/products/docker-desktop/
> e inicia sesión una vez.

### Opción B — Instalación nativa de Windows

1. Descarga PostgreSQL 17: https://www.postgresql.org/download/windows/
2. Durante la instalación crea el usuario/clave que pongas en tu `.env`.
3. Crea la base de datos:
   ```powershell
   psql -U postgres -c "CREATE DATABASE mycolegiofavorito;"
   psql -U postgres -c "CREATE USER mcf_user WITH PASSWORD 'cambia_esta_clave';"
   psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE mycolegiofavorito TO mcf_user;"
   ```

---

## 3. Migrar los datos existentes (SQLite → PostgreSQL)

Con la BD PostgreSQL ya corriendo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\migrar_a_postgres.ps1
```

El script:
1. Valida que estás en SQLite y que psycopg está instalado
2. Prueba que PostgreSQL responde en `DB_HOST:DB_PORT`
3. Exporta todos los datos a `backups/migracion_<fecha>.json`
4. Cambia `DB_ENGINE=postgresql` en el `.env` (guarda copia `.env.bak.<fecha>`)
5. Ejecuta `migrate` + `loaddata`
6. Corre los checks finales

Si algo falla **revierte el `.env` solo** y no toca tu SQLite original.

### Manual (equivalente al script)

```powershell
# 1. Exportar desde SQLite
python manage.py dumpdata --natural-primary --natural-foreign `
    --exclude contenttypes --exclude auth.permission --exclude sessions `
    --output backups\datos.json

# 2. Cambiar DB_ENGINE=postgresql en .env, luego:
python manage.py migrate
python manage.py loaddata backups\datos.json
```

> Los archivos de `media/` no viven en la BD; si cambias de servidor cópialos aparte.

### Volver atrás (rollback)

```powershell
Copy-Item .env.bak.<fecha> .env        # restaura DB_ENGINE=sqlite
python manage.py runserver             # sigues donde estabas
```

---

## 4. Backups

Comando único para ambos motores:

```powershell
python manage.py backup_db                 # backup a backups/
python manage.py backup_db --keep 14       # conserva solo los 14 más recientes
python manage.py backup_db --dest D:\backups
```

- **SQLite**: usa la API de backup en caliente (`sqlite3.Connection.backup`),
  segura aunque la app esté escribiendo. Genera `backups/mcf_sqlite_<fecha>.sqlite3`.
- **PostgreSQL**: usa `pg_dump` formato custom comprimido. Genera
  `backups/mcf_postgres_<fecha>.dump`. Requiere `pg_dump` en el PATH
  (viene con PostgreSQL; con Docker puedes ejecutarlo dentro del contenedor).

### Automatizar el backup diario (Windows)

```powershell
# Ejecutar como administrador: crea tarea diaria 02:00 AM
schtasks /create /tn "MCF Backup BD" /tr "cmd /c cd /d C:\Users\tonto\mycolegiofavorito && python manage.py backup_db --keep 30" /sc daily /st 02:00
```

### Restaurar

**SQLite** — copia el archivo del backup sobre `db.sqlite3`
(con la app detenida) o ábrelo y verifica antes:

```powershell
python manage.py dbshell    # .tables  → confirmar que el backup tiene datos
```

**PostgreSQL**

```powershell
pg_restore --clean --if-exists --host 127.0.0.1 --port 5432 `
    --username mcf_user --dbname mycolegiofavorito backups\mcf_postgres_<fecha>.dump
```

O desde Docker:

```powershell
Get-Content backups\mcf_postgres_<fecha>.dump | docker compose exec -T db pg_restore --clean --if-exists -U mcf_user -d mycolegiofavorito
```

---

## 5. Regla de oro de los backups

Un backup **solo existe de verdad** si está en otro lugar físico.
Cada semana copia manualmente (o programa) la carpeta `backups/` a:

- Un disco externo / USB, o
- La nube (Google Drive, OneDrive, S3: `aws s3 sync backups/ s3://mi-bucket/backups/`)
