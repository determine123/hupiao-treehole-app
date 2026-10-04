# Run manually on the owner's Windows computer; does not print secrets.
$ErrorActionPreference='Stop'
$taskPrivateDirectory=Join-Path $env:USERPROFILE '.codex/private/hupiao'
$taskState=Get-Content (Join-Path $taskPrivateDirectory 'cloud-state.json') -Raw | ConvertFrom-Json
$taskSecrets=Get-Content (Join-Path $taskPrivateDirectory 'backend-secrets.json') -Raw | ConvertFrom-Json
if(-not $taskSecrets.ADMIN_TOKEN){throw 'Administrator credential is unavailable on this computer.'}
Set-Clipboard -Value $taskSecrets.ADMIN_TOKEN
Start-Process ($taskState.apiUrl+'/admin')
Write-Host 'Administrator page opened. Paste the key from the clipboard into its login field.'
Write-Host 'Clear the clipboard after login. Never paste the key into public chats or feedback.'
