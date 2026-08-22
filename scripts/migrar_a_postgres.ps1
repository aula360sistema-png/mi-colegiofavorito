# ---------------------------------------------------------------------------
# Migra los datos de SQLite a PostgreSQL en un solo paso.
#
# Que hace:
#   1. Valida que hoy estes usando SQLite y que psycopg este instalado.
#   2. Verifica que PostgreSQL sea alcanzable en DB_HOST:DB_PORT.
#   3. Exporta todos los datos a JSON (backups/migracion_<fecha>.json).
#   4. Cambia DB_ENGINE=postgresql en el .env (guarda copia previa).
#   5. Crea el esquema (migrate) y carga los datos (loaddata).
#   6. Ejecuta checks finales.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts\migrar_a_postgres.ps1
#
# Requisitos: PostgreSQL corriendo (docker compose up -d o instalacion local)
# con las credenciales del .env ya creadas (la BD debe existir).
# ---------------------------------------------------------------------------

$ErrorActionPreference = "Stop"

function Fail($msg) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 1
}

# --- 1. Estado actual ------------------------------------------------------
$envPath = Join-Path $PSScriptRoot "..\.env"
if (-not (Test-Path $envPath)) { Fail "No se encontro .env" }

$envContent = Get-Content $envPath -Raw
$dbEngine = ([regex]::Match($envContent, "(?m)^DB_ENGINE=(.*)$")).Groups[1].Value.Trim()
if ($dbEngine -ne "sqlite") {
    Fail "El .env actual usa DB_ENGINE=$dbEngine. Este script migra desde sqlite."
}

python -c "import psycopg" 2>$null
if ($LASTEXITCODE -ne 0) {
    Fail "psycopg no esta instalado. Ejecuta: pip install `"psycopg[binary]`""
}

# --- 2. PostgreSQL alcanzable? ---------------------------------------------
$dbHost = ([regex]::Match($envContent, "(?m)^DB_HOST=(.*)$")).Groups[1].Value.Trim(); if (-not $dbHost) { $dbHost = "127.0.0.1" }
$dbPort = ([regex]::Match($envContent, "(?m)^DB_PORT=(.*)$")).Groups[1].Value.Trim(); if (-not $dbPort) { $dbPort = "5432" }

Write-Host "[1/6] Probando conexion a ${dbHost}:${dbPort} ..."
$tcp = New-Object Net.Sockets.TcpClient
try {
    $tcp.Connect($dbHost, [int]$dbPort)
} catch {
    Fail "PostgreSQL no responde en ${dbHost}:${dbPort}. Levantalo primero (docker compose up -d)."
}
$tcp.Close()

# --- 3. Exportar datos de SQLite -------------------------------------------
$fecha = Get-Date -Format "yyyy-MM-dd_HHmmss"
New-Item -ItemType Directory -Force -Path "backups" | Out-Null
$json = "backups\migracion_$fecha.json"

Write-Host "[2/6] Exportando datos de SQLite a $json ..."
python manage.py dumpdata --natural-primary --natural-foreign `
    --exclude contenttypes --exclude auth.permission --exclude sessions `
    --output $json --indent 2
if ($LASTEXITCODE -ne 0) { Fail "dumpdata fallo. No se cambio nada." }

$tamanoMB = [math]::Round((Get-Item $json).Length / 1MB, 2)
Write-Host ("      Export OK ({0} MB)" -f $tamanoMB)

# --- 4. Cambiar .env ---------------------------------------------------------
Write-Host "[3/6] Cambiando DB_ENGINE a postgresql en .env ..."
Copy-Item $envPath "$envPath.bak.$fecha"
$nuevoContenido = [regex]::Replace($envContent, "(?m)^DB_ENGINE=.*$", "DB_ENGINE=postgresql")
$utf8SinBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($envPath, $nuevoContenido, $utf8SinBom)

# --- 5. Esquema + datos en PostgreSQL ---------------------------------------
Write-Host "[4/6] Creando esquema en PostgreSQL (migrate) ..."
python manage.py migrate
if ($LASTEXITCODE -ne 0) {
    Write-Host "migrate fallo. Revirtiendo .env ..." -ForegroundColor Yellow
    Copy-Item "$envPath.bak.$fecha" $envPath
    Fail "Revisa credenciales/permisos de PostgreSQL y vuelve a intentar."
}

Write-Host "[5/6] Cargando datos (loaddata) ..."
python manage.py loaddata $json
if ($LASTEXITCODE -ne 0) {
    Write-Host "loaddata fallo. Revirtiendo .env ..." -ForegroundColor Yellow
    Copy-Item "$envPath.bak.$fecha" $envPath
    Fail "La BD PostgreSQL quedo a medio llenar: recreala (docker compose down -v && docker compose up -d) y reintenta."
}

# --- 6. Checks ---------------------------------------------------------------
Write-Host "[6/6] Checks finales ..."
python manage.py check
if ($LASTEXITCODE -ne 0) { Fail "manage.py check reporto problemas." }

Write-Host ""
Write-Host "MIGRACION COMPLETADA." -ForegroundColor Green
Write-Host "  - Datos exportados en: $json (conservalo como respaldo)"
Write-Host "  - Copia previa del .env: .env.bak.$fecha"
Write-Host "  - Tu SQLite original NO se borro (db.sqlite3 sigue intacto por si acaso)"
Write-Host ""
Write-Host "Prueba la app: python manage.py runserver"
