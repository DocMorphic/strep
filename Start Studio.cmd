@echo off
setlocal
pushd "%~dp0" || exit /b 1
if not exist "scripts\action_studio_server.py" (
  echo The Studio source is missing. Keep this launcher in the complete Strep project folder.
  pause
  popd
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo This development workspace is not set up yet.
  echo Follow docs\baseline-runbook.md to prepare the local environment and models.
  echo This launcher does not install or download anything.
  pause
  popd
  exit /b 1
)
echo Starting Strep Studio. Keep this window open while using it.
echo Once the server prints its ready address, open http://127.0.0.1:8768/studio
echo Press Ctrl+C here to stop the Studio server.
echo.
".venv\Scripts\python.exe" "scripts\action_studio_server.py" --port 8768
set "strepStudioExit=%errorlevel%"
echo.
echo The Studio server has stopped. Check any error shown above before retrying.
pause
popd
exit /b %strepStudioExit%
