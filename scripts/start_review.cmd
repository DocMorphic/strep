@echo off
setlocal
pushd "%~dp0" || exit /b 1
if not exist "serve.py" (
  echo Extract the complete review ZIP first, then open Start Review.cmd inside it.
  pause
  popd
  exit /b 1
)
py -3 -c "import sys; sys.exit(sys.version_info.major != 3)" >nul 2>&1
if not errorlevel 1 (
  py -3 "serve.py" --open
  goto finished
)
python -c "import sys; sys.exit(sys.version_info.major != 3)" >nul 2>&1
if not errorlevel 1 (
  python "serve.py" --open
  goto finished
)
echo Python 3 was not found. Install Python 3, then open this launcher again.
echo No motion model or online account is needed to review this packet.
:finished
echo.
echo The review server has stopped. Any saved ratings remain in your browser.
pause
popd
endlocal
