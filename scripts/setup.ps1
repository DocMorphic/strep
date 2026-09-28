$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot
try {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw 'Install uv before running setup.' }
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        uv venv --python 3.10 .venv
        if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
    }
    uv pip install --python .venv\Scripts\python.exe torch==2.10.0 --index-url https://download.pytorch.org/whl/cu128
    if ($LASTEXITCODE -ne 0) { throw 'CUDA PyTorch installation failed.' }
    $previousSkip = $env:SKIP_MOTION_CORRECTION_IN_SETUP
    try {
        # Official setup switch: retain unchanged source and install diffusion first.
        $env:SKIP_MOTION_CORRECTION_IN_SETUP = '1'
        uv pip install --python .venv\Scripts\python.exe -e .\vendor\kimodo psutil pytest
        if ($LASTEXITCODE -ne 0) { throw 'Kimodo dependencies failed.' }
    } finally { $env:SKIP_MOTION_CORRECTION_IN_SETUP = $previousSkip }
    uv pip freeze --python .venv\Scripts\python.exe | Set-Content -Encoding utf8 benchmarks\environment.windows.txt
    if ($LASTEXITCODE -ne 0) { throw 'Environment capture failed.' }
    node scripts\plan-baseline.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Benchmark validation failed.' }
    .venv\Scripts\python.exe scripts\strep.py doctor --online
    if ($LASTEXITCODE -ne 0) { throw 'Preflight command failed.' }
} finally { Pop-Location }
