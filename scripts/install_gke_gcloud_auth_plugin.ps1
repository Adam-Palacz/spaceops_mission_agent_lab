# Fix broken `gcloud components install gke-gcloud-auth-plugin` on Windows (bundled Python).
# Usage: powershell -ExecutionPolicy Bypass -File scripts/install_gke_gcloud_auth_plugin.ps1
# Then: . .\scripts\refresh_dev_path.ps1

$ErrorActionPreference = "Stop"

$gcloud = Get-Command gcloud -ErrorAction SilentlyContinue
if (-not $gcloud) {
    Write-Error "gcloud not on PATH. Install Google Cloud SDK first."
}

Write-Host "Step 1/2: copy-bundled-python (required on Windows before component install)..."
$pyLine = & gcloud components copy-bundled-python 2>&1 | Select-Object -Last 1
$pyPath = ($pyLine | Out-String).Trim()
if (-not (Test-Path $pyPath)) {
    Write-Error "copy-bundled-python did not return a valid python.exe: $pyPath"
}
$env:CLOUDSDK_PYTHON = $pyPath
Write-Host "  CLOUDSDK_PYTHON=$pyPath"

Write-Host "Step 2/2: install gke-gcloud-auth-plugin..."
& gcloud components install gke-gcloud-auth-plugin --quiet

$plugin = Join-Path (Split-Path $gcloud.Source) "gke-gcloud-auth-plugin.exe"
if (-not (Test-Path $plugin)) {
    Write-Error "Install finished but plugin not found at $plugin"
}

$env:USE_GKE_GCLOUD_AUTH_PLUGIN = "True"
Write-Host ""
Write-Host "Done. Plugin: $plugin" -ForegroundColor Green
Write-Host "New terminal, then:" -ForegroundColor Green
Write-Host "  gcloud container clusters get-credentials spaceops-stage --region us-central1 --project spaceops-project" -ForegroundColor Green
Write-Host "  kubectl get nodes" -ForegroundColor Green
