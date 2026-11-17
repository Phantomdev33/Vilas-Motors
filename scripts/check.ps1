$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$previousSettings = $env:DJANGO_SETTINGS_MODULE
try {
    $env:DJANGO_SETTINGS_MODULE = 'config.prototype'
    & (Join-Path $projectRoot '.runtime/python/python.exe') (Join-Path $projectRoot 'backend/manage.py') check
    if ($LASTEXITCODE -ne 0) { throw 'Falló la revisión de Django.' }
    & (Join-Path $projectRoot '.runtime/python/python.exe') (Join-Path $projectRoot 'backend/manage.py') test fleet config.test_database --noinput
    if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas del backend.' }
} finally {
    $env:DJANGO_SETTINGS_MODULE = $previousSettings
}
Push-Location (Join-Path $projectRoot 'frontend')
try {
    & (Join-Path $projectRoot '.runtime/node/node.exe') node_modules/vite/bin/vite.js build
    if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación de React.' }
    & (Join-Path $projectRoot '.runtime/node/node.exe') node_modules/@playwright/test/cli.js test
    if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas del navegador.' }
} finally { Pop-Location }
