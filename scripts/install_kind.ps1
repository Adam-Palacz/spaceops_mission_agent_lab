# Install kind into %LOCALAPPDATA%\Programs\kind and prepend to User PATH.
# Usage: powershell -ExecutionPolicy Bypass -File scripts/install_kind.ps1
# Then: . .\scripts\refresh_dev_path.ps1

$ErrorActionPreference = "Stop"

$version = "0.27.0"
$installDir = Join-Path $env:LOCALAPPDATA "Programs\kind"
$exe = Join-Path $installDir "kind.exe"
$zipUrl = "https://kind.sigs.k8s.io/dl/v$version/kind-windows-amd64"

New-Item -ItemType Directory -Force -Path $installDir | Out-Null

Write-Host "Downloading kind v$version ..."
Invoke-WebRequest -Uri $zipUrl -OutFile $exe -UseBasicParsing

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$installDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$installDir;$userPath", "User")
    Write-Host "Added to User PATH: $installDir"
}

$env:Path = "$installDir;" + $env:Path
& $exe version
Write-Host ""
Write-Host "Done. In this shell kind is ready. For other terminals run:" -ForegroundColor Green
Write-Host "  . .\scripts\refresh_dev_path.ps1" -ForegroundColor Green
