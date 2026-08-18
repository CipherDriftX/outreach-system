# Outreach OS — Single-click start
# Starts PostgreSQL and the API server. Open http://localhost:8000

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pgdir  = "$root\.local"
$pgdata = "$pgdir\pgdata"
$pgbin  = "$pgdir\pgsql\bin"

# 1. Start Postgres if not running
$env:Path = "$pgbin;$env:Path"
$ready = & "$pgbin\pg_isready.exe" -h localhost -p 5432 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Starting PostgreSQL..."
    $env:PGDATA = $pgdata
    Start-Process -FilePath "$pgbin\postgres.exe" -ArgumentList "-D",$pgdata -WindowStyle Hidden
    Start-Sleep -Seconds 4
    & "$pgbin\pg_isready.exe" -h localhost -p 5432
}

# 2. Start API server
Write-Host "Starting Outreach OS API on http://localhost:8000"
python -m uvicorn src.api.server:app --port 8000 --host 127.0.0.1