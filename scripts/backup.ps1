$ErrorActionPreference='Stop'
$deployRoot=Join-Path (Split-Path -Parent $PSScriptRoot) 'deploy'
Set-Location $deployRoot
$backupRoot=Join-Path (Split-Path -Parent $deployRoot) 'backups'
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
$backupTarget=Join-Path $backupRoot ('hupiao-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.sql')
# Docker writes directly to the file through --output in a temporary in-container path.
& docker compose exec -T db pg_dump -U hupiao -d hupiao -f /tmp/hupiao-backup.sql
if($LASTEXITCODE -ne 0){throw 'Backup failed'}
& docker compose cp db:/tmp/hupiao-backup.sql $backupTarget
if($LASTEXITCODE -ne 0){throw 'Backup copy failed'}
Write-Output $backupTarget
