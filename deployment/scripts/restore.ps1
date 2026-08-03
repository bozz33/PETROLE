[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BackupDirectory,
    [switch]$ConfirmRestore,
    [switch]$StartWeb
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $ConfirmRestore) {
    throw "Ajoutez -ConfirmRestore pour autoriser le remplacement de la base et des fichiers."
}

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$backupPath = (Resolve-Path $BackupDirectory).Path
$manifestPath = Join-Path $backupPath "manifest.json"
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Le manifeste de sauvegarde est absent."
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.format_version -ne 1) {
    throw "La version du format de sauvegarde n'est pas prise en charge."
}
foreach ($entry in $manifest.files) {
    $filePath = Join-Path $backupPath $entry.name
    if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) {
        throw "Le fichier de sauvegarde $($entry.name) est absent."
    }
    $actualHash = (Get-FileHash -Algorithm SHA256 $filePath).Hash.ToLowerInvariant()
    if ($actualHash -ne $entry.sha256) {
        throw "L'empreinte du fichier $($entry.name) est invalide."
    }
}

$composeFiles = @(
    (Join-Path $repositoryRoot "deployment\docker-compose.yml"),
    (Join-Path $repositoryRoot "deployment\docker-compose.dev.yml")
)
$composeArguments = @()
foreach ($composeFile in $composeFiles) {
    $composeArguments += @("-f", $composeFile)
}

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    & docker compose @composeArguments @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "La commande Docker Compose a échoué avec le code $LASTEXITCODE."
    }
}

Invoke-Compose up --detach postgres minio
Invoke-Compose stop api worker web minio
$postgresContainer = (Invoke-Compose ps --all -q postgres | Select-Object -First 1).Trim()
$minioContainer = (Invoke-Compose ps --all -q minio | Select-Object -First 1).Trim()
if (-not $postgresContainer -or -not $minioContainer) {
    throw "Les conteneurs PostgreSQL et MinIO doivent être disponibles."
}
$helperImage = (& docker inspect --format "{{.Config.Image}}" $postgresContainer).Trim()
if ($LASTEXITCODE -ne 0 -or -not $helperImage) {
    throw "L'image utilitaire de restauration est introuvable."
}

$databaseTemporaryPath = "/tmp/hydro-restore.dump"
& docker cp (Join-Path $backupPath "postgres.dump") "${postgresContainer}:$databaseTemporaryPath"
if ($LASTEXITCODE -ne 0) {
    throw "La copie de l'archive PostgreSQL a échoué."
}

try {
    Invoke-Compose exec -T postgres pg_restore --list $databaseTemporaryPath | Out-Null
    & docker run --rm `
        --mount "type=bind,source=$backupPath,target=/backup,readonly" `
        --entrypoint sh $helperImage `
        -c "tar -tzf /backup/object-storage.tar.gz >/dev/null"
    if ($LASTEXITCODE -ne 0) {
        throw "L'archive du stockage objet est invalide."
    }
    Invoke-Compose exec -T postgres sh -c (
        'dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB" && ' +
        'createdb -U "$POSTGRES_USER" "$POSTGRES_DB" && ' +
        'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges ' +
        $databaseTemporaryPath
    )
    & docker run --rm --volumes-from $minioContainer `
        --mount "type=bind,source=$backupPath,target=/backup,readonly" `
        --entrypoint sh $helperImage `
        -c "find /data -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + && tar -xzf /backup/object-storage.tar.gz -C /data"
    if ($LASTEXITCODE -ne 0) {
        throw "La restauration du stockage objet a échoué."
    }
}
finally {
    Invoke-Compose exec -T postgres rm -f $databaseTemporaryPath
}

Invoke-Compose run --rm --no-deps api alembic upgrade head
Invoke-Compose up --detach minio api worker
if ($StartWeb) {
    Invoke-Compose up --detach web
}

$result = [ordered]@{
    restored_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    backup_directory = $backupPath
    source_alembic_revision = $manifest.alembic_revision
    status = "restored"
}
$result | ConvertTo-Json -Depth 3 | Set-Content (
    Join-Path $backupPath "restore-result.json"
) -Encoding utf8
Write-Output "Restauration terminée depuis $backupPath."
