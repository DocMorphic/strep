$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot
try {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw 'Install uv before running setup.' }
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Install Git before running setup.' }
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Install Node.js before running setup.' }
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        uv venv --python 3.10 .venv
        if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
    }
    .venv\Scripts\python.exe scripts\prepare_vendor.py
    if ($LASTEXITCODE -ne 0) { throw 'Pinned Kimodo source preparation failed; package installation has not started.' }
    uv pip install --python .venv\Scripts\python.exe torch==2.10.0 --index-url https://download.pytorch.org/whl/cu128
    if ($LASTEXITCODE -ne 0) { throw 'CUDA PyTorch installation failed.' }
    $previousSkip = $env:SKIP_MOTION_CORRECTION_IN_SETUP
    try {
        # Official setup switch: retain unchanged source and install diffusion first.
        $env:SKIP_MOTION_CORRECTION_IN_SETUP = '1'
        uv pip install --python .venv\Scripts\python.exe -e .\vendor\kimodo psutil pytest
        if ($LASTEXITCODE -ne 0) { throw 'Kimodo dependencies failed.' }
    } finally { $env:SKIP_MOTION_CORRECTION_IN_SETUP = $previousSkip }
    $strepEnvironment = uv pip freeze --python .venv\Scripts\python.exe
    if ($LASTEXITCODE -ne 0) { throw 'Environment capture failed.' }
    $strepSetupReport = Join-Path $projectRoot ('reports\setup\' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $strepSetupReport -ErrorAction Stop | Out-Null
    $strepEnvironment | Set-Content -Encoding utf8 (Join-Path $strepSetupReport 'environment.windows.txt')
    Write-Host "Environment capture saved in $strepSetupReport"
    node scripts\plan-baseline.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Benchmark validation failed.' }
    .venv\Scripts\python.exe scripts\strep.py doctor --online
    if ($LASTEXITCODE -ne 0) { throw 'Preflight command failed.' }
} finally { Pop-Location }
