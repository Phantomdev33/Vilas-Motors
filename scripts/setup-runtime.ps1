$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$runtimeRoot = Join-Path $projectRoot '.runtime'
New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
if (!(Test-Path (Join-Path $runtimeRoot 'node/node.exe'))) {
    Invoke-WebRequest 'https://nodejs.org/dist/v24.12.0/node-v24.12.0-win-x64.zip' -OutFile (Join-Path $runtimeRoot 'node.zip')
    Expand-Archive -LiteralPath (Join-Path $runtimeRoot 'node.zip') -DestinationPath $runtimeRoot -Force
    Move-Item -LiteralPath (Join-Path $runtimeRoot 'node-v24.12.0-win-x64') -Destination (Join-Path $runtimeRoot 'node')
}
if (!(Test-Path (Join-Path $runtimeRoot 'python/python.exe'))) {
    Invoke-WebRequest 'https://www.python.org/ftp/python/3.13.7/python-3.13.7-embed-amd64.zip' -OutFile (Join-Path $runtimeRoot 'python.zip')
    Expand-Archive -LiteralPath (Join-Path $runtimeRoot 'python.zip') -DestinationPath (Join-Path $runtimeRoot 'python') -Force
    Set-Content -LiteralPath (Join-Path $runtimeRoot 'python/python313._pth') -Value "python313.zip`n.`nLib/site-packages`n../../backend`nimport site"
}
$localPython = Join-Path $runtimeRoot 'python/python.exe'
if (!(Test-Path (Join-Path $runtimeRoot 'python/Lib/site-packages/pip'))) {
    Invoke-WebRequest 'https://bootstrap.pypa.io/get-pip.py' -OutFile (Join-Path $runtimeRoot 'get-pip.py')
    & $localPython (Join-Path $runtimeRoot 'get-pip.py') --no-warn-script-location
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo instalar pip.' }
}
& $localPython -m pip install -r (Join-Path $projectRoot 'backend/requirements.txt') --no-warn-script-location
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias del backend.' }
$env:Path = (Join-Path $runtimeRoot 'node') + ';' + $env:Path
Push-Location (Join-Path $projectRoot 'frontend')
try {
    & (Join-Path $runtimeRoot 'node/npm.cmd') install
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias del frontend.' }
} finally { Pop-Location }
Write-Host 'Herramientas y dependencias instaladas dentro del proyecto.'
