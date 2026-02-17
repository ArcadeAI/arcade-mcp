Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

function Assert-PathExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathToCheck
    )

    if (-not (Test-Path $PathToCheck)) {
        throw "Expected path to exist: $PathToCheck"
    }
}

function Start-BackgroundProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [Parameter(Mandatory = $false)]
        [switch]$AllowEarlyExit
    )

    $unique = [Guid]::NewGuid().ToString("N")
    $stdoutPath = Join-Path $env:TEMP ($Name + "-" + $unique + "-stdout.log")
    $stderrPath = Join-Path $env:TEMP ($Name + "-" + $unique + "-stderr.log")

    $process = Start-Process -FilePath "uv" `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -PassThru `
        -NoNewWindow `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath

    Start-Sleep -Seconds 4
    if ($process.HasExited) {
        $stdout = if (Test-Path $stdoutPath) { Get-Content -Raw $stdoutPath } else { "" }
        $stderr = if (Test-Path $stderrPath) { Get-Content -Raw $stderrPath } else { "" }
        $exitCode = $process.ExitCode

        if ($AllowEarlyExit -and $exitCode -eq 0) {
            $combinedOutput = "$stdout`n$stderr"
            if ($combinedOutput -match "(?i)started successfully") {
                return @{
                    Process = $process
                    Stdout  = $stdoutPath
                    Stderr  = $stderrPath
                }
            }
        }

        throw "Process '$Name' exited early (exit code: $exitCode).`nSTDOUT:`n$stdout`nSTDERR:`n$stderr"
    }

    return @{
        Process = $process
        Stdout  = $stdoutPath
        Stderr  = $stderrPath
    }
}

function Stop-BackgroundProcess {
    param(
        [Parameter(Mandatory = $false)]
        [hashtable]$Handle
    )

    if ($null -eq $Handle) {
        return
    }
    if ($null -eq $Handle.Process) {
        return
    }

    try {
        if (-not $Handle.Process.HasExited) {
            # /T kills child processes as well, avoiding orphaned python workers.
            & taskkill /PID $Handle.Process.Id /T /F | Out-Null
        }
    } catch {
        try {
            if (-not $Handle.Process.HasExited) {
                Stop-Process -Id $Handle.Process.Id -Force
            }
        } catch {
            Write-Host "Warning: failed to stop background process: $($_.Exception.Message)"
        }
    }
}

function Wait-ForHttpHealth {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [Parameter(Mandatory = $false)]
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                return $true
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

function Get-FreeTcpPort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    try {
        return $listener.LocalEndpoint.Port
    } finally {
        $listener.Stop()
    }
}

function Convert-ToTomlPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue
    )

    return ($PathValue -replace "\\", "/")
}

function Add-LocalArcadeUvSources {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PyprojectPath,
        [Parameter(Mandatory = $true)]
        [string]$RepoRootPath
    )

    $pyproject = Get-Content -Raw $PyprojectPath
    if ($pyproject -match "(?m)^\[tool\.uv\.sources\]\s*$") {
        return
    }

    $repoRootTomlPath = Convert-ToTomlPath -PathValue $RepoRootPath
    $sourcesBlock = @(
        "[tool.uv.sources]"
        "arcade-mcp = { path = `"$repoRootTomlPath`", editable = true }"
        "arcade-mcp-server = { path = `"$repoRootTomlPath/libs/arcade-mcp-server`", editable = true }"
        "arcade-core = { path = `"$repoRootTomlPath/libs/arcade-core`", editable = true }"
        "arcade-serve = { path = `"$repoRootTomlPath/libs/arcade-serve`", editable = true }"
        "arcade-tdk = { path = `"$repoRootTomlPath/libs/arcade-tdk`", editable = true }"
    ) -join "`n"

    $updatedPyproject = $pyproject.TrimEnd() + "`n`n" + $sourcesBlock + "`n"
    Set-Content -Path $PyprojectPath -Value $updatedPyproject -Encoding utf8
}

$RepoRoot = (Get-Location).Path
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"

Write-Host "Repo root: $RepoRoot"
uv --version
uv sync --dev
uv pip install -e .

$ArcadeCli = Join-Path $RepoRoot ".venv\Scripts\arcade.exe"
Assert-PathExists -PathToCheck $ArcadeCli

Write-Host "Using CLI: $ArcadeCli"
& $ArcadeCli --version

# --------------------------------------------------------------------------
# Configure commands in a path with spaces
# --------------------------------------------------------------------------
$configTemp = Join-Path $env:TEMP ("arcade mcp config test " + $env:GITHUB_RUN_ID + "-" + $env:GITHUB_RUN_ATTEMPT)
New-Item -ItemType Directory -Force -Path $configTemp | Out-Null
Set-Location $configTemp
"print('ok')" | Set-Content -Path ".\server.py" -Encoding utf8

& $ArcadeCli configure cursor --name demo --config ".\cursor config.json"
$overwriteOutput = & $ArcadeCli configure cursor --transport http --port 8123 --name demo --config ".\cursor config.json" 2>&1 | Out-String
if ($overwriteOutput -notmatch "(?i)overwrite") {
    throw "Expected overwrite warning when configuring cursor with same --name."
}

& $ArcadeCli configure vscode --name demo --config ".\vscode config.json"
& $ArcadeCli configure claude --name demo --config ".\claude config.json"

Get-Content -Raw ".\cursor config.json" | ConvertFrom-Json | Out-Null
Get-Content -Raw ".\vscode config.json" | ConvertFrom-Json | Out-Null
Get-Content -Raw ".\claude config.json" | ConvertFrom-Json | Out-Null

# --------------------------------------------------------------------------
# Scaffold command in a path with spaces
# --------------------------------------------------------------------------
Set-Location $RepoRoot
$scaffoldBase = Join-Path $env:TEMP ("arcade scaffold with spaces " + $env:GITHUB_RUN_ID + "-" + $env:GITHUB_RUN_ATTEMPT)
New-Item -ItemType Directory -Force -Path $scaffoldBase | Out-Null

$newOutput = & $ArcadeCli new my_server --dir $scaffoldBase 2>&1 | Out-String
if ($newOutput -notmatch "Next steps:") {
    throw "Expected 'Next steps:' output from 'arcade new'."
}

$serverRoot = Join-Path $scaffoldBase "my_server"
Assert-PathExists -PathToCheck (Join-Path $serverRoot "pyproject.toml")
Assert-PathExists -PathToCheck (Join-Path $serverRoot "src\my_server\server.py")
Assert-PathExists -PathToCheck (Join-Path $serverRoot "src\my_server\.env.example")

# Ensure generated project is runnable without auth flows.
$generatedPyproject = Join-Path $serverRoot "pyproject.toml"
Add-LocalArcadeUvSources -PyprojectPath $generatedPyproject -RepoRootPath $RepoRoot
Set-Location (Join-Path $serverRoot "src\my_server")
uv run python -c "import server; print('generated server import ok')"

$generatedServerDir = (Get-Location).Path

# Validate stdio transport starts and stays alive briefly.
$stdioHandle = $null
try {
    $stdioHandle = Start-BackgroundProcess `
        -Name "arcade-generated-stdio" `
        -WorkingDirectory $generatedServerDir `
        -Arguments @("run", "server.py") `
        -AllowEarlyExit
} finally {
    Stop-BackgroundProcess -Handle $stdioHandle
}

# Validate HTTP transport starts and responds on health endpoint.
$httpHandle = $null
$httpRunnerPath = $null
$hadWorkerSecret = Test-Path Env:ARCADE_WORKER_SECRET
$previousWorkerSecret = $null
if ($hadWorkerSecret) {
    $previousWorkerSecret = $env:ARCADE_WORKER_SECRET
}
$env:ARCADE_WORKER_SECRET = "arcade-smoke-worker-secret"
try {
    $httpPort = Get-FreeTcpPort
    $httpRunnerFileName = "__arcade_http_smoke_runner.py"
    $httpRunnerPath = Join-Path $generatedServerDir $httpRunnerFileName
    @(
        "from server import app"
        "app.run(transport='http', host='127.0.0.1', port=$httpPort)"
    ) | Set-Content -Path $httpRunnerPath -Encoding utf8

    $httpHandle = Start-BackgroundProcess `
        -Name "arcade-generated-http" `
        -WorkingDirectory $generatedServerDir `
        -Arguments @("run", "python", $httpRunnerFileName)

    $healthUrl = "http://127.0.0.1:$httpPort/worker/health"
    if (-not (Wait-ForHttpHealth -Url $healthUrl -TimeoutSeconds 30)) {
        $stdout = if (Test-Path $httpHandle.Stdout) { Get-Content -Raw $httpHandle.Stdout } else { "" }
        $stderr = if (Test-Path $httpHandle.Stderr) { Get-Content -Raw $httpHandle.Stderr } else { "" }
        throw "HTTP transport did not become healthy at $healthUrl.`nSTDOUT:`n$stdout`nSTDERR:`n$stderr"
    }
} finally {
    Stop-BackgroundProcess -Handle $httpHandle
    if ($null -ne $httpRunnerPath -and (Test-Path $httpRunnerPath)) {
        Remove-Item -Path $httpRunnerPath -Force
    }
    if ($hadWorkerSecret) {
        $env:ARCADE_WORKER_SECRET = $previousWorkerSecret
    } else {
        Remove-Item Env:ARCADE_WORKER_SECRET -ErrorAction SilentlyContinue
    }
}

Write-Host "Windows no-auth CLI smoke checks passed."
