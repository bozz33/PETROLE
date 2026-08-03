[CmdletBinding()]
param(
    [string]$OutputDirectory
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $repositoryRoot "var\backups"
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

foreach ($service in @("postgres", "minio", "api")) {
    $containerId = (Invoke-Compose ps -q $service | Select-Object -First 1).Trim()
    if (-not $containerId) {
        throw "Le service $service doit être démarré avant la sauvegarde."
    }
}

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$destination = Join-Path ([System.IO.Path]::GetFullPath($OutputDirectory)) $timestamp
New-Item -ItemType Directory -Path $destination -Force | Out-Null

$postgresContainer = (Invoke-Compose ps -q postgres | Select-Object -First 1).Trim()
$minioContainer = (Invoke-Compose ps -q minio | Select-Object -First 1).Trim()
$helperImage = (& docker inspect --format "{{.Config.Image}}" $postgresContainer).Trim()
if ($LASTEXITCODE -ne 0 -or -not $helperImage) {
    throw "L'image utilitaire de sauvegarde est introuvable."
}
$databaseArchive = Join-Path $destination "postgres.dump"
$objectArchive = Join-Path $destination "object-storage.tar.gz"
$databaseTemporaryPath = "/tmp/hydro-backup-$timestamp.dump"

try {
    Invoke-Compose exec -T postgres sh -c (
        'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --file=' +
        $databaseTemporaryPath
    )
    Invoke-Compose exec -T postgres pg_restore --list $databaseTemporaryPath | Out-Null
    & docker cp "${postgresContainer}:$databaseTemporaryPath" $databaseArchive
    if ($LASTEXITCODE -ne 0) {
        throw "La copie de la sauvegarde PostgreSQL a échoué."
    }

    & docker run --rm --volumes-from $minioContainer `
        --mount "type=bind,source=$destination,target=/backup" `
        --entrypoint sh $helperImage `
        -c "tar -czf /backup/object-storage.tar.gz -C /data . && tar -tzf /backup/object-storage.tar.gz >/dev/null"
    if ($LASTEXITCODE -ne 0) {
        throw "La sauvegarde du stockage objet a échoué."
    }
}
finally {
    Invoke-Compose exec -T postgres rm -f $databaseTemporaryPath
}

$alembicRevision = (Invoke-Compose exec -T api alembic current | Select-Object -First 1).Trim()
$manifest = [ordered]@{
    format_version = 1
    created_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    alembic_revision = $alembicRevision
    files = @(
        [ordered]@{
            name = "postgres.dump"
            sha256 = (Get-FileHash -Algorithm SHA256 $databaseArchive).Hash.ToLowerInvariant()
            size_bytes = (Get-Item $databaseArchive).Length
        },
        [ordered]@{
            name = "object-storage.tar.gz"
            sha256 = (Get-FileHash -Algorithm SHA256 $objectArchive).Hash.ToLowerInvariant()
            size_bytes = (Get-Item $objectArchive).Length
        }
    )
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content (
    Join-Path $destination "manifest.json"
) -Encoding utf8

Write-Output $destination
