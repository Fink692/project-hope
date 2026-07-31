param(
  [Parameter(Mandatory = $true)][string]$Snapshot,
  [Parameter(Mandatory = $true)][string]$RestoreRoot,
  [Parameter(Mandatory = $true)][string]$RestoreDatabaseUrl,
  [switch]$Confirm
)

$ErrorActionPreference = "Stop"
if (-not $Confirm) { throw "Use -Confirm to run a restore drill." }
if (-not $env:RESTIC_REPOSITORY) { throw "RESTIC_REPOSITORY is required" }
if (-not $env:RESTIC_PASSWORD_FILE) { throw "RESTIC_PASSWORD_FILE is required" }

New-Item -ItemType Directory -Force -Path $RestoreRoot | Out-Null
& restic --repo=$env:RESTIC_REPOSITORY --password-file=$env:RESTIC_PASSWORD_FILE restore $Snapshot --target $RestoreRoot
if ($LASTEXITCODE -ne 0) { throw "restic restore failed" }

$dump = Get-ChildItem -LiteralPath $RestoreRoot -Recurse -Filter *.dump -File | Select-Object -First 1
if (-not $dump) { throw "No PostgreSQL custom dump found in restored snapshot." }
& pg_restore --clean --if-exists --no-owner --dbname=$RestoreDatabaseUrl $dump.FullName
if ($LASTEXITCODE -ne 0) { throw "pg_restore failed" }
Write-Output "Restore drill completed into explicitly supplied staging targets."
