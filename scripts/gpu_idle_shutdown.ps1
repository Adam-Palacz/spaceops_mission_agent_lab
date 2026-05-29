[CmdletBinding()]
param(
    [switch]$DryRun,
    [int]$TtlMinutes = [int]([Environment]::GetEnvironmentVariable("GPU_IDLE_TTL_MINUTES") ?? 45),
    [string]$ActivityFile = "",
    [string]$ComposeFile = "",
    [string]$Service = "nim-llm",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

if ([string]::IsNullOrWhiteSpace($ActivityFile)) {
    $ActivityFile = Join-Path $RepoRoot "var\llm_last_gpu_call_at"
}
if ([string]::IsNullOrWhiteSpace($ComposeFile)) {
    $ComposeFile = Join-Path $RepoRoot "infra\docker-compose.yml"
}

$python = "python"
$venvPy = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPy) {
    $python = $venvPy
}

$args = @(
    (Join-Path $ScriptDir "gpu_idle_shutdown.py"),
    "--ttl-minutes", "$TtlMinutes",
    "--activity-file", "$ActivityFile",
    "--compose-file", "$ComposeFile",
    "--service", "$Service"
)
if ($DryRun) { $args += "--dry-run" }
if ($ExtraArgs) { $args += $ExtraArgs }

& $python @args
exit $LASTEXITCODE
