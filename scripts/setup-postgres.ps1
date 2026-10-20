$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$runtimeRoot = Join-Path $projectRoot '.runtime'
$postgresBin = Join-Path $runtimeRoot 'pgsql/bin'
if (!(Test-Path (Join-Path $runtimeRoot 'postgres-extracted'))) {
    if (!(Test-Path (Join-Path $runtimeRoot 'postgres.zip'))) {
        Invoke-WebRequest 'https://get.enterprisedb.com/postgresql/postgresql-18.6-5-windows-x64-binaries.zip' -OutFile (Join-Path $runtimeRoot 'postgres.zip')
    }
    & (Join-Path $runtimeRoot 'python/python.exe') (Join-Path $PSScriptRoot 'extract-postgres.py')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo extraer PostgreSQL.' }
}
$envPath = Join-Path $projectRoot 'backend/.env'
if (!(Test-Path $envPath)) {
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $bytes = New-Object byte[] 48
    $rng.GetBytes($bytes)
    $dbPassword = [Convert]::ToBase64String($bytes)
    $rng.GetBytes($bytes)
    $djangoSecret = [Convert]::ToBase64String($bytes)
    $rng.Dispose()
    Set-Content -LiteralPath $envPath -Encoding ASCII -Value @(
        'DJANGO_DEBUG=true', "DJANGO_SECRET_KEY=$djangoSecret", 'POSTGRES_DB=vilas_motor', 'POSTGRES_USER=vilas',
        "POSTGRES_PASSWORD=$dbPassword", 'POSTGRES_HOST=127.0.0.1', 'POSTGRES_PORT=55432',
        'FRONTEND_URL=http://localhost:5173', 'CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173'
    )
} else {
    $dbPassword = (Get-Content $envPath | Where-Object { $_ -match '^POSTGRES_PASSWORD=' }) -replace '^POSTGRES_PASSWORD=', ''
    if (!$dbPassword) { throw 'El archivo backend/.env existente necesita POSTGRES_PASSWORD. No se sobrescribió.' }
}
$dataDir = Join-Path $runtimeRoot 'postgres-data'
if (!(Test-Path (Join-Path $dataDir 'PG_VERSION'))) {
    $passwordFile = Join-Path $runtimeRoot 'postgres-init-password.tmp'
    Set-Content -LiteralPath $passwordFile -Encoding ASCII -Value $dbPassword
    try {
        & (Join-Path $postgresBin 'initdb.exe') -D $dataDir -U vilas --auth=scram-sha-256 --encoding=UTF8 --locale=C --pwfile=$passwordFile
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo inicializar PostgreSQL.' }
    } finally { Remove-Item -LiteralPath $passwordFile -Force }
}
& (Join-Path $postgresBin 'pg_ctl.exe') -D $dataDir status
if ($LASTEXITCODE -ne 0) {
    & (Join-Path $postgresBin 'pg_ctl.exe') -D $dataDir -l (Join-Path $runtimeRoot 'postgres.log') -o '-p 55432 -h 127.0.0.1' -w start
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo iniciar PostgreSQL.' }
}
$env:PGPASSWORD = $dbPassword
try {
    $exists = & (Join-Path $postgresBin 'psql.exe') -h 127.0.0.1 -p 55432 -U vilas -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='vilas_motor'"
    if ($exists -ne '1') {
        & (Join-Path $postgresBin 'createdb.exe') -h 127.0.0.1 -p 55432 -U vilas vilas_motor
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear la base del proyecto.' }
    }
} finally { Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue }
& (Join-Path $runtimeRoot 'python/python.exe') (Join-Path $projectRoot 'backend/manage.py') migrate
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron aplicar las migraciones.' }
& (Join-Path $runtimeRoot 'python/python.exe') (Join-Path $projectRoot 'backend/manage.py') seed_demo
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron cargar los datos ficticios.' }
Write-Host 'PostgreSQL listo en 127.0.0.1:55432. Credenciales locales guardadas en backend/.env.'
