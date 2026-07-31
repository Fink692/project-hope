param(
  [ValidateSet("setup", "start", "stop", "status", "logs", "doctor", "help")]
  [string]$Command = "help",
  [switch]$NoOpen
)

$ErrorActionPreference = "Stop"
$script:RepoRoot = Split-Path -Parent $PSScriptRoot
$script:ComposeFile = Join-Path $script:RepoRoot "deploy\podman\compose.yml"
$script:Engine = $null

function Show-Help {
  Write-Host ""
  Write-Host "Project Hope - simple local workspace" -ForegroundColor Green
  Write-Host ""
  Write-Host "Use these commands from the project folder:"
  Write-Host "  .\scripts\project-hope.ps1 setup   First-time setup, start services, and open Project Hope"
  Write-Host "  .\scripts\project-hope.ps1 start   Start the workspace"
  Write-Host "  .\scripts\project-hope.ps1 stop    Stop the workspace without deleting data"
  Write-Host "  .\scripts\project-hope.ps1 status  Show service status"
  Write-Host "  .\scripts\project-hope.ps1 logs    Show recent service logs"
  Write-Host "  .\scripts\project-hope.ps1 doctor  Check the computer before setup"
  Write-Host ""
  Write-Host "Plain-language guide: docs\GETTING_STARTED_FOR_CHARITIES.md" -ForegroundColor Cyan
  Write-Host ""
}

function Find-ContainerEngine {
  $preferred = $env:PROJECT_HOPE_CONTAINER_ENGINE
  $candidates = if ($preferred) { @($preferred) } else { @("docker", "podman") }
  foreach ($candidate in $candidates) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
      $script:Engine = $candidate
      return
    }
  }
  throw "Project Hope needs Docker Desktop or Podman Desktop. Install one, start it, and run this command again. See docs\GETTING_STARTED_FOR_CHARITIES.md."
}

function Invoke-Container {
  param([Parameter(Mandatory = $true)][string[]]$Arguments)
  $previousErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  & $script:Engine @Arguments
  $exitCode = $LASTEXITCODE
  $ErrorActionPreference = $previousErrorActionPreference
  if ($exitCode -ne 0) {
    throw "The container command did not finish successfully. Make sure $script:Engine is open, then try again."
  }
}

function Invoke-Compose {
  param([Parameter(Mandatory = $true)][string[]]$Arguments)
  Invoke-Container -Arguments (@("compose", "-f", $script:ComposeFile) + $Arguments)
}

function Confirm-ContainerReady {
  if (-not (Test-Path -LiteralPath $script:ComposeFile)) {
    throw "Project Hope's workspace file is missing: $script:ComposeFile"
  }
  Find-ContainerEngine
  Write-Host "Checking $script:Engine..." -ForegroundColor DarkGray
  $previousErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  & $script:Engine info *> $null
  $exitCode = $LASTEXITCODE
  $ErrorActionPreference = $previousErrorActionPreference
  if ($exitCode -ne 0) {
    throw "$script:Engine is installed but not running. Open Docker Desktop or Podman Desktop, wait until it says it is ready, and try again."
  }
}

function Wait-ForWorkspace {
  $healthUrl = "http://localhost:8090/api/v1/healthz/"
  if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
    return
  }
  Write-Host "Waiting for Project Hope to become ready..." -ForegroundColor DarkGray
  for ($attempt = 1; $attempt -le 30; $attempt++) {
    & curl.exe --silent --show-error --fail --max-time 2 $healthUrl *> $null
    if ($LASTEXITCODE -eq 0) {
      return
    }
    Start-Sleep -Seconds 2
  }
  Write-Host "The services are still starting. Run '.\scripts\project-hope.ps1 status' for details." -ForegroundColor Yellow
}

function Open-Workspace {
  if (-not $NoOpen) {
    Start-Process "http://localhost:8090"
  }
}

function Start-Workspace {
  Confirm-ContainerReady
  Write-Host "Starting Project Hope. The first start may take a few minutes while images are prepared." -ForegroundColor Green
  Invoke-Compose -Arguments @("up", "-d", "--build")
  Wait-ForWorkspace
  Write-Host "Project Hope is available at http://localhost:8090" -ForegroundColor Green
}

try {
  switch ($Command) {
    "help" { Show-Help; break }
    "doctor" {
      Confirm-ContainerReady
      Write-Host "Everything needed for the local workspace is ready." -ForegroundColor Green
      break
    }
    "setup" {
      Start-Workspace
      Open-Workspace
      Write-Host ""
      Write-Host "Sign in for this local workspace:" -ForegroundColor Cyan
      Write-Host "  Email:    demo@example.org"
      Write-Host "  Password: change-me-now"
      Write-Host ""
      Write-Host "This account is for local setup only. Change the identity setup before using real charity data." -ForegroundColor Yellow
      break
    }
    "start" { Start-Workspace; break }
    "stop" {
      Confirm-ContainerReady
      Invoke-Compose -Arguments @("down")
      Write-Host "Project Hope is stopped. Your named data volumes were not deleted." -ForegroundColor Green
      break
    }
    "status" {
      Confirm-ContainerReady
      Invoke-Compose -Arguments @("ps")
      break
    }
    "logs" {
      Confirm-ContainerReady
      Invoke-Compose -Arguments @("logs", "--tail", "80")
      break
    }
  }
} catch {
  Write-Host ""
  Write-Host "Setup needs one more step:" -ForegroundColor Yellow
  Write-Host $_.Exception.Message -ForegroundColor Yellow
  exit 1
}
