# Refresh Windows PATH in the current PowerShell session and verify PS6 dev tools.
# Usage (from repo root):
#   . .\scripts\refresh_dev_path.ps1
# Dot-source (leading ".") is required - it updates THIS shell, not a child process.

$ErrorActionPreference = "Stop"

function Refresh-DevPath {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Test-DevTool {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [string]$InstallHint = ""
    )
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd -and $Name -eq "python") {
        $venvPy = Join-Path $PSScriptRoot ".." ".venv" "Scripts" "python.exe" | Resolve-Path -ErrorAction SilentlyContinue
        if ($venvPy) {
            Write-Host ("[ok]   {0,-10} {1} (venv; Makefile default on Windows)" -f $Name, $venvPy) -ForegroundColor Green
            return $true
        }
    }
    if ($cmd) {
        Write-Host ("[ok]   {0,-10} {1}" -f $Name, $cmd.Source) -ForegroundColor Green
        return $true
    }
    Write-Host ("[miss] {0,-10} {1}" -f $Name, $InstallHint) -ForegroundColor Yellow
    return $false
}

Refresh-DevPath
Write-Host "PATH refreshed from Machine + User (fixes stale terminals after winget installs)." -ForegroundColor Cyan
Write-Host ""

$hints = @{
    docker  = "Install Docker Desktop"
    kind    = "winget install -e --id Kubernetes.kind  OR  scripts/install_kind.ps1"
    kubectl = "winget install Kubernetes.kubectl"
    helm    = "winget install Helm.Helm"
    make    = "GnuWin32 make or Git for Windows"
    python  = "Python 3.12 and .venv (see README)"
}

$ok = @(
    (Test-DevTool -Name "docker" -InstallHint $hints.docker)
    (Test-DevTool -Name "kind" -InstallHint $hints.kind)
    (Test-DevTool -Name "kubectl" -InstallHint $hints.kubectl)
    (Test-DevTool -Name "helm" -InstallHint $hints.helm)
    (Test-DevTool -Name "make" -InstallHint $hints.make)
    (Test-DevTool -Name "python" -InstallHint $hints.python)
)

Write-Host ""
if ($ok -contains $false) {
    Write-Host "Some tools missing. Install, then re-run:" -ForegroundColor Yellow
    Write-Host "  . .\scripts\refresh_dev_path.ps1" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "After winget install, restart Cursor or open a new terminal." -ForegroundColor Yellow
} else {
    Write-Host "All checked tools found. Try: make k8s-up" -ForegroundColor Green
}
