param([string]$Directory = (Join-Path $env:USERPROFILE '.codex/private/hupiao/backups'))
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'This encryption wrapper requires PowerShell 7 on Windows.' }
if (-not $env:HUPIAO_DATABASE_URL) { throw 'Set HUPIAO_DATABASE_URL privately in the environment.' }
$taskRepo = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$taskDirectory = [IO.Path]::GetFullPath($Directory)
if ($taskDirectory.Equals($taskRepo, [StringComparison]::OrdinalIgnoreCase) -or $taskDirectory.StartsWith($taskRepo + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Choose a private backup directory outside the repository.'
}
New-Item -ItemType Directory -Force -Path $taskDirectory | Out-Null
$taskName = 'hupiao-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N')
$taskClear = Join-Path $taskDirectory ($taskName + '.jsonl.gz')
$taskFinal = $taskClear + '.dpapi'
$taskEncryptedTemporary = $taskFinal + '.tmp'
$taskPython = Join-Path $taskRepo '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { $taskPython = 'python' }
try {
    & $taskPython (Join-Path $taskRepo 'backend/backup.py') export $taskClear
    if ($LASTEXITCODE -ne 0) { throw 'Database snapshot export failed.' }
    $taskBytes = [IO.File]::ReadAllBytes($taskClear)
    $taskCipher = [Security.Cryptography.ProtectedData]::Protect($taskBytes, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
    [IO.File]::WriteAllBytes($taskEncryptedTemporary, $taskCipher)
    $taskRecovered = [Security.Cryptography.ProtectedData]::Unprotect([IO.File]::ReadAllBytes($taskEncryptedTemporary), $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
    $taskHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($taskBytes)).ToLowerInvariant()
    if ($taskHash -ne [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($taskRecovered)).ToLowerInvariant()) { throw 'Encrypted snapshot verification failed.' }
    Move-Item -LiteralPath $taskEncryptedTemporary -Destination $taskFinal
    [pscustomobject]@{path=$taskFinal;sha256=$taskHash;encryption='Windows DPAPI CurrentUser';verified=$true} | ConvertTo-Json -Compress
} finally {
    foreach ($taskTemporary in @($taskClear, $taskEncryptedTemporary)) {
        if (Test-Path -LiteralPath $taskTemporary) { Remove-Item -LiteralPath $taskTemporary -Force }
    }
}
