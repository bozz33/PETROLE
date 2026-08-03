[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$VpsHost,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$VpsUser,
    [ValidatePattern('^/[A-Za-z0-9._/-]+$')]
    [string]$RemoteProjectRoot = "/opt/petrole",
    [string]$BackupDirectory,
    [string]$IdentityFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Push-Location $repositoryRoot
try {
    $trackedChanges = git status --porcelain --untracked-files=no
    if ($LASTEXITCODE -ne 0 -or $trackedChanges) {
        throw "Les modifications suivies doivent être commit avant le transfert."
    }

    $localCommit = (git rev-parse HEAD).Trim()
    $remoteCommit = ((git ls-remote origin refs/heads/main) -split "`t")[0]
    if ($LASTEXITCODE -ne 0 -or $localCommit -ne $remoteCommit) {
        throw "Le commit local doit être présent sur origin/main avant le transfert."
    }

    if (-not $BackupDirectory) {
        $BackupDirectory = & powershell -ExecutionPolicy Bypass -File `
            deployment/scripts/backup.ps1 | Select-Object -Last 1
        if ($LASTEXITCODE -ne 0) {
            throw "La sauvegarde locale a échoué."
        }
    }
    $backupPath = (Resolve-Path $BackupDirectory).Path
    $backupName = Split-Path $backupPath -Leaf

    $sshArguments = @()
    $scpArguments = @()
    if ($IdentityFile) {
        $identityPath = (Resolve-Path $IdentityFile).Path
        $sshArguments += @("-i", $identityPath)
        $scpArguments += @("-i", $identityPath)
    }
    $destination = "${VpsUser}@${VpsHost}"
    $remoteIncoming = "$RemoteProjectRoot/var/incoming-backup"
    $remoteCommand = @"
set -eu
if [ ! -d '$RemoteProjectRoot/.git' ]; then
  git clone https://github.com/bozz33/PETROLE.git '$RemoteProjectRoot'
else
  git -C '$RemoteProjectRoot' fetch origin main
  git -C '$RemoteProjectRoot' checkout main
  git -C '$RemoteProjectRoot' pull --ff-only origin main
fi
mkdir -p '$remoteIncoming'
"@
    & ssh @sshArguments $destination $remoteCommand
    if ($LASTEXITCODE -ne 0) {
        throw "La préparation du dépôt distant a échoué."
    }

    & scp @scpArguments -r $backupPath "${destination}:${remoteIncoming}/"
    if ($LASTEXITCODE -ne 0) {
        throw "Le transfert de la sauvegarde a échoué."
    }

    Write-Output "Code et sauvegarde transférés."
    Write-Output "Sauvegarde distante : $remoteIncoming/$backupName"
    Write-Output "Connectez-vous au VPS, créez deployment/.env.vps, puis exécutez deploy.sh et restore.sh selon deployment/VPS.md."
}
finally {
    Pop-Location
}
