param([switch]$RealSms)

$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..\backend')
$prototypePython = Join-Path $PSScriptRoot '..\.runtime\python\python.exe'
if (!(Test-Path -LiteralPath $prototypePython)) { $prototypePython = 'python' }
$env:DJANGO_SETTINGS_MODULE = 'config.prototype'
$env:DJANGO_DEBUG = 'true'
$env:PROTOTYPE_SMS_BACKEND = if ($RealSms) { 'twilio' } else { 'console' }
if ($RealSms) {
    & $prototypePython manage.py shell -c "from django.conf import settings; raise SystemExit(0 if all((settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_FROM)) else 1)"
    if ($LASTEXITCODE -ne 0) { throw 'Configura TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN y TWILIO_FROM en backend/.env.' }
}
& $prototypePython manage.py migrate
if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar la base del prototipo.' }
& $prototypePython manage.py seed_demo
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron cargar los datos simulados.' }
& $prototypePython manage.py runserver 127.0.0.1:8000
