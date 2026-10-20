$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$runtimeRoot = Join-Path $projectRoot '.runtime'
foreach ($name in @('backend','frontend')) {
    $pidPath = Join-Path $runtimeRoot "$name.pid"
    if (Test-Path $pidPath) {
        $ownedId = [int](Get-Content $pidPath)
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$ownedId" -ErrorAction SilentlyContinue
        if ($process -and $process.ExecutablePath -and $process.ExecutablePath.StartsWith($runtimeRoot, [StringComparison]::OrdinalIgnoreCase)) {
            Stop-Process -Id $ownedId -ErrorAction SilentlyContinue
        }
        Remove-Item -LiteralPath $pidPath
    }
}
$pgCtl = Join-Path $runtimeRoot 'pgsql/bin/pg_ctl.exe'
$dataDir = Join-Path $runtimeRoot 'postgres-data'
if (Test-Path (Join-Path $dataDir 'PG_VERSION')) {
    & $pgCtl -D $dataDir status
    if ($LASTEXITCODE -eq 0) { & $pgCtl -D $dataDir -m fast -w stop }
}
