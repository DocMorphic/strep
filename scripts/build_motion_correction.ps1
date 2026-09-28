# Rebuild the pinned upstream extension from the retained local toolchain.
# No system installation, PATH persistence, model changes, or network fetches.
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$toolchain = Join-Path $project '.cache/motion-correction-toolchain'
$build = Join-Path $project '.cache/motion-correction-build'
$package = Join-Path $project '.cache/motion-correction-package/motion_correction'
$dependencies = @{
    'pybind11' = '8a099e44b3d5f85b20f05828d919d2332a8de841'
    'eigen' = '3147391d946bb4b6c68edd901f2add6ac1f31f8c'
}
$downloads = Get-Content (Join-Path $toolchain 'downloads.json') -Raw | ConvertFrom-Json
foreach ($entry in $downloads) {
    $archive = Join-Path $toolchain ($entry[0].Split('/')[-1])
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLower() -ne $entry[1]) { throw "Archive hash mismatch: $archive" }
}
foreach ($name in $dependencies.Keys) {
    $source = Join-Path $build "_deps/$name-src"
    $revision = & git -C $source rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $revision -ne $dependencies[$name]) { throw "Dependency revision mismatch: $name" }
    $modified = & git -C $source status --porcelain --untracked-files=no
    if ($LASTEXITCODE -ne 0 -or $modified) { throw "Modified dependency: $name" }
}
$savedPath = $env:PATH
try {
    $env:PATH = "$toolchain/cmake-3.31.8-windows-x86_64/bin;$toolchain/w64devkit/bin;$savedPath"
    & cmake -S "$project/vendor/kimodo/MotionCorrection" -B $build -G 'MinGW Makefiles' '-DCMAKE_BUILD_TYPE=Release' "-DPython3_EXECUTABLE=$project/.venv/Scripts/python.exe" "-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=$package" '-DFETCHCONTENT_FULLY_DISCONNECTED=ON' "-DFETCHCONTENT_SOURCE_DIR_PYBIND11=$build/_deps/pybind11-src" "-DFETCHCONTENT_SOURCE_DIR_EIGEN=$build/_deps/eigen-src"
    if ($LASTEXITCODE -ne 0) { throw 'CMake configuration failed' }
    & cmake --build $build --target _motion_correction --parallel 4
    if ($LASTEXITCODE -ne 0) { throw 'C++ build failed' }
    Copy-Item "$project/vendor/kimodo/MotionCorrection/python/motion_correction/*.py" $package
} finally { $env:PATH = $savedPath }
