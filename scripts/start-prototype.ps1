$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..\backend')
$prototypePython = Join-Path $PSScriptRoot '..\.runtime\python\python.exe'
if (!(Test-Path -LiteralPath $prototypePython)) { $prototypePython = 'python' }
$env:DJANGO_SETTINGS_MODULE = 'config.prototype'
$env:DJANGO_DEBUG = 'true'
& $prototypePython manage.py migrate
if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar la base del prototipo.' }
& $prototypePython manage.py seed_demo
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron cargar los datos simulados.' }
& $prototypePython manage.py runserver 127.0.0.1:8000
