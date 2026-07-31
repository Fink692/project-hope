param(
  [Parameter(Mandatory = $true)]
  [ValidatePattern('^https://')]
  [string]$ServerUrl
)

$ErrorActionPreference = "Stop"
$desktopRoot = Join-Path $PSScriptRoot "..\apps\desktop"
$resolvedDesktopRoot = (Resolve-Path -LiteralPath $desktopRoot).Path

Push-Location $resolvedDesktopRoot
try {
  $env:PROJECT_HOPE_APP_URL = $ServerUrl.TrimEnd('/')
  pnpm install --frozen-lockfile
  pnpm run dist:win
  Write-Host "Project Hope installer created in $resolvedDesktopRoot\release" -ForegroundColor Green
} finally {
  Pop-Location
}
