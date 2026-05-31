# PS6.9 — GKE node pool scale-down wrapper (PowerShell).
param(
    [switch]$DryRun,
    [string]$Project = $env:GCP_PROJECT_ID,
    [string]$Region = $(if ($env:GCP_REGION) { $env:GCP_REGION } else { "us-central1" }),
    [string]$Cluster = $(if ($env:GKE_CLUSTER) { $env:GKE_CLUSTER } else { "spaceops-stage" }),
    [string]$NodePool = $(if ($env:GKE_NODE_POOL) { $env:GKE_NODE_POOL } else { "spaceops-stage-pool" }),
    [int]$Nodes = $(if ($env:GKE_TARGET_NODES) { [int]$env:GKE_TARGET_NODES } else { 0 })
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }

$Args = @("$ScriptDir\schedule_scale_down.py")
if ($DryRun) { $Args += "--dry-run" }
if ($Project) { $Args += @("--project", $Project) }
$Args += @("--region", $Region, "--cluster", $Cluster, "--node-pool", $NodePool, "--nodes", "$Nodes")

& $Py @Args
