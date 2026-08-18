# Stop Outreach OS services

Write-Host "Stopping API server..."
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq "" } | Stop-Process -Force

Write-Host "Stopping PostgreSQL..."
$env:Path = "$PSScriptRoot\.local\pgsql\bin;$env:Path"
& "$PSScriptRoot\.local\pgsql\bin\pg_ctl.exe" -D "$PSScriptRoot\.local\pgdata" stop -m fast 2>$null
Write-Host "Done"