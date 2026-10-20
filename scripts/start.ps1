param([switch]$NoFrontend)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$runtimeRoot = Join-Path $projectRoot '.runtime'
if (!(Test-Path (Join-Path $runtimeRoot 'python/python.exe'))) { throw 'Primero ejecuta scripts/setup-runtime.ps1.' }
if (!(Test-Path (Join-Path $projectRoot 'backend/.env'))) { throw 'Primero ejecuta scripts/setup-postgres.ps1 o configura backend/.env.' }
$dataDir = Join-Path $runtimeRoot 'postgres-data'
if (Test-Path (Join-Path $dataDir 'PG_VERSION')) {
    $pgCtl = Join-Path $runtimeRoot 'pgsql/bin/pg_ctl.exe'
    & $pgCtl -D $dataDir status
    if ($LASTEXITCODE -ne 0) {
        & $pgCtl -D $dataDir -l (Join-Path $runtimeRoot 'postgres.log') -o '-p 55432 -h 127.0.0.1' -w start
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo iniciar PostgreSQL.' }
    }
}
$backendPort = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if (!$backendPort) {
    $backendProcess = Start-Process -FilePath (Join-Path $runtimeRoot 'python/python.exe') -ArgumentList @('backend/manage.py','runserver','127.0.0.1:8000','--noreload') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeRoot 'backend.log') -RedirectStandardError (Join-Path $runtimeRoot 'backend-error.log')
    Set-Content -LiteralPath (Join-Path $runtimeRoot 'backend.pid') -Value $backendProcess.Id
}
if (!$NoFrontend) {
    $frontendPort = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
    if (!$frontendPort) {
        $frontendProcess = Start-Process -FilePath (Join-Path $runtimeRoot 'node/node.exe') -ArgumentList @('node_modules/vite/bin/vite.js','--host','127.0.0.1') -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeRoot 'frontend.log') -RedirectStandardError (Join-Path $runtimeRoot 'frontend-error.log')
        Set-Content -LiteralPath (Join-Path $runtimeRoot 'frontend.pid') -Value $frontendProcess.Id
    }
}
foreach ($url in @('http://127.0.0.1:8000/api/auth/csrf/') + $(if (!$NoFrontend) { @('http://127.0.0.1:5173/') } else { @() })) {
    $ready = $false
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2
            if ($response.StatusCode -eq 200) { $ready = $true; break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (!$ready) { throw "El servicio no respondió: $url. Revisa los registros en .runtime/." }
}
Write-Host 'Frontend: http://localhost:5173'
Write-Host 'API Django: http://localhost:8000/api/'
Write-Host 'Registros de inicio: .runtime/backend-error.log y .runtime/frontend-error.log'
