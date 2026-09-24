# opencode-env.ps1 — OpenCode CLI launcher for the Solo-Code harness
#
# Why this exists: bridges .env configuration to OpenCode runtime environment.
# It reads OPENAI_BASE_URL, OPENAI_API_KEY, and COMMANDCODE credentials from .env,
# normalizes the base URL (stripping any trailing /v1 so {env:OPENAI_BASE_URL}/v1
# in opencode config resolves cleanly), exports them into the process environment,
# and launches opencode with any pass-through arguments.
#
# Usage:
#   .\opencode-env.ps1                                # interactive OpenCode TUI
#   .\opencode-env.ps1 run "run the tests"            # non-interactive command
#   .\opencode-env.ps1 -m freemodel/gpt-5.6-terra     # specify model directly
#   .\opencode-env.ps1 --help                         # pass-through flags

$ErrorActionPreference = "Stop"

# Ensure working directory is the project root containing .env
if ($PSScriptRoot -and (Test-Path -LiteralPath (Join-Path $PSScriptRoot ".env"))) {
    Set-Location $PSScriptRoot
}

$envFile = Join-Path (Get-Location) ".env"
if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Error "No .env found at $envFile. Run this launcher from the project root."
    exit 1
}

$config = @{}
foreach ($line in Get-Content -LiteralPath $envFile) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
        continue
    }
    $name, $value = $trimmed.Split("=", 2)
    $name = $name.Trim()
    $value = $value.Trim()
    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    $config[$name] = $value
}

# Export all loaded env vars into process environment
foreach ($entry in $config.GetEnumerator()) {
    if ($entry.Value) {
        [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, "Process")
    }
}

# Export OpenAI / FreeModel credentials
if ($config.ContainsKey("OPENAI_API_KEY") -and $config["OPENAI_API_KEY"]) {
    $env:OPENAI_API_KEY = $config["OPENAI_API_KEY"]
    $env:FREEMODEL_API_KEY = $config["OPENAI_API_KEY"]
}

# Normalize OPENAI_BASE_URL: ensure it has no trailing /v1 or slashes
# so {env:OPENAI_BASE_URL}/v1 in opencode config resolves reliably.
if ($config.ContainsKey("OPENAI_BASE_URL") -and $config["OPENAI_BASE_URL"]) {
    $baseUrl = $config["OPENAI_BASE_URL"].Trim().TrimEnd("/")
    if ($baseUrl.EndsWith("/v1")) {
        $baseUrl = $baseUrl.Substring(0, $baseUrl.Length - 3)
    }
    $env:OPENAI_BASE_URL = $baseUrl
}

# Export and normalize CommandCode credentials if present
if ($config.ContainsKey("COMMANDCODE_API_KEY") -and $config["COMMANDCODE_API_KEY"]) {
    $env:COMMANDCODE_API_KEY = $config["COMMANDCODE_API_KEY"]
}
if ($config.ContainsKey("COMMANDCODE_BASE_URL") -and $config["COMMANDCODE_BASE_URL"]) {
    $env:COMMANDCODE_BASE_URL = $config["COMMANDCODE_BASE_URL"].Trim().TrimEnd("/")
}

# Export and normalize Anthropic credentials if present
if ($config.ContainsKey("ANTHROPIC_API_KEY") -and $config["ANTHROPIC_API_KEY"]) {
    $env:ANTHROPIC_API_KEY = $config["ANTHROPIC_API_KEY"]
}
if ($config.ContainsKey("ANTHROPIC_BASE_URL") -and $config["ANTHROPIC_BASE_URL"]) {
    $antUrl = $config["ANTHROPIC_BASE_URL"].Trim().TrimEnd("/")
    $freemodelDomains = @("api.freemodel.dev", "cc.freemodel.dev", "api-cc.freemodel.dev", "cc-t2.freemodel.dev")
    foreach ($domain in $freemodelDomains) {
        if ($antUrl -eq "https://${domain}/v1/messages") {
            $antUrl = "https://${domain}"
            break
        }
    }
    $env:ANTHROPIC_BASE_URL = $antUrl
}

# Resolve opencode executable:
# Prefer native opencode.exe if available to avoid Windows batch/shim (%*) argument mangling
$opencodeBin = $null
$exeCmd = Get-Command opencode.exe -ErrorAction SilentlyContinue
if ($exeCmd -and (Test-Path -LiteralPath $exeCmd.Source)) {
    $opencodeBin = $exeCmd.Source
}
else {
    $genericCmd = Get-Command opencode -ErrorAction SilentlyContinue
    if ($genericCmd) {
        $parentDir = Split-Path $genericCmd.Source -Parent
        $v2Exe = Join-Path $parentDir "node_modules\@opencode\cli\bin\opencode.exe"
        $v1Exe = Join-Path $parentDir "node_modules\opencode-ai\bin\opencode.exe"
        if (Test-Path -LiteralPath $v2Exe) {
            $opencodeBin = $v2Exe
        }
        elseif (Test-Path -LiteralPath $v1Exe) {
            $opencodeBin = $v1Exe
        }
        else {
            $opencodeBin = $genericCmd.Source
        }
    }
}

if (-not $opencodeBin) {
    Write-Error "opencode not found on PATH. Install with: npm install -g @opencode/cli"
    exit 1
}

$opencodeArgs = @($args)
$exitCode = 1
try {
    & $opencodeBin @opencodeArgs
    if ($null -ne $LASTEXITCODE) {
        $exitCode = $LASTEXITCODE
    }
    else {
        $exitCode = 0
    }
}
catch {
    Write-Error $_
    $exitCode = 1
}
exit $exitCode
