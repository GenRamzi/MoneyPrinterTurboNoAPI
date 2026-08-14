@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 (
  echo Installation failed.
  exit /b 1
)
echo Installation completed.
