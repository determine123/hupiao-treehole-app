$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $projectRoot 'backend')
$taskPython=Join-Path $projectRoot '.venv/Scripts/python.exe'
if(-not (Test-Path -LiteralPath $taskPython)){throw 'Create .venv and install backend/requirements-dev.txt first.'}
& $taskPython -m alembic upgrade head
if($LASTEXITCODE -ne 0){throw 'Migration failed'}
& $taskPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000
