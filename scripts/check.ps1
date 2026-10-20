$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
& (Join-Path $projectRoot '.runtime/python/python.exe') (Join-Path $projectRoot 'backend/manage.py') check
if ($LASTEXITCODE -ne 0) { throw 'Falló la revisión de Django.' }
& (Join-Path $projectRoot '.runtime/python/python.exe') (Join-Path $projectRoot 'backend/manage.py') test fleet
if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas del backend.' }
Push-Location (Join-Path $projectRoot 'frontend')
try {
    & (Join-Path $projectRoot '.runtime/node/node.exe') node_modules/vite/bin/vite.js build
    if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación de React.' }
    & (Join-Path $projectRoot '.runtime/node/node.exe') node_modules/@playwright/test/cli.js test
    if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas del navegador.' }
} finally { Pop-Location }
