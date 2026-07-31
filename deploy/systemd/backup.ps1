param(
  [string]$OutputDirectory = $(Join-Path $PSScriptRoot "..\..\backups")
)

$ErrorActionPreference = "Stop"
if (-not $env:DATABASE_URL) { throw "DATABASE_URL is required" }
if (-not $env:RESTIC_REPOSITORY) { throw "RESTIC_REPOSITORY is required" }
if (-not $env:RESTIC_PASSWORD_FILE) { throw "RESTIC_PASSWORD_FILE is required" }

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$mediaRoot = $env:PROJECT_HOPE_MEDIA_ROOT
if (-not $mediaRoot) { $mediaRoot = Join-Path $PSScriptRoot "..\..\services\core\media" }
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$dump = Join-Path $OutputDirectory "project-hope-$timestamp.dump"
& pg_dump --format=custom --file=$dump $env:DATABASE_URL
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed" }
& restic --repo=$env:RESTIC_REPOSITORY --password-file=$env:RESTIC_PASSWORD_FILE backup $OutputDirectory $mediaRoot
if ($LASTEXITCODE -ne 0) { throw "restic backup failed" }
& restic --repo=$env:RESTIC_REPOSITORY --password-file=$env:RESTIC_PASSWORD_FILE check
if ($LASTEXITCODE -ne 0) { throw "restic verification failed" }
Write-Output "Backup completed: $timestamp"
