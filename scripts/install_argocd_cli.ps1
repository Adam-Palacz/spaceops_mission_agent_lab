# Install Argo CD CLI into %LOCALAPPDATA%\Programs\argocd and prepend to User PATH.
# Usage: powershell -ExecutionPolicy Bypass -File scripts/install_argocd_cli.ps1
# Then: . .\scripts\refresh_dev_path.ps1

$ErrorActionPreference = "Stop"

$version = if ($env:ARGOCD_CLI_VERSION) { $env:ARGOCD_CLI_VERSION } else { "v2.14.8" }
if (-not $version.StartsWith("v")) {
    $version = "v$version"
}

$installDir = Join-Path $env:LOCALAPPDATA "Programs\argocd"
$exe = Join-Path $installDir "argocd.exe"
$downloadUrl = "https://github.com/argoproj/argo-cd/releases/download/$version/argocd-windows-amd64.exe"

New-Item -ItemType Directory -Force -Path $installDir | Out-Null

Write-Host "Downloading Argo CD CLI $version ..."
Invoke-WebRequest -Uri $downloadUrl -OutFile $exe -UseBasicParsing

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$installDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$installDir;$userPath", "User")
    Write-Host "Added to User PATH: $installDir"
}

$env:Path = "$installDir;" + $env:Path
& $exe version --client
Write-Host ""
Write-Host "Done. Example (with port-forward on 8080:443):" -ForegroundColor Green
Write-Host "  argocd login localhost:8080 --username admin --insecure" -ForegroundColor Green
Write-Host "  argocd app list" -ForegroundColor Green
Write-Host ""
Write-Host "For other terminals run:" -ForegroundColor Green
Write-Host "  . .\scripts\refresh_dev_path.ps1" -ForegroundColor Green
