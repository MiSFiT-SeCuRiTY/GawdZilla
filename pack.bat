@echo off
REM GawdZilla - package source for GitHub upload
setlocal

set NAME=GawdZilla
set /p VERSION=<VERSION
if "%VERSION%"=="" set VERSION=1.0.0
set OUT=%NAME%-v%VERSION%.zip

if not exist "GawdZilla.py" (
  echo [!] Run from the project root.
  exit /b 1
)

if exist "%OUT%" del "%OUT%"

powershell -NoProfile -Command ^
  "$skip = '(\\__pycache__\\|\\.venv\\|\\.git\\|\\.gradle\\|\\build\\|^data\\)';" ^
  "$files = Get-ChildItem -Force -Recurse | Where-Object { $_.FullName -notmatch $skip -and $_.Extension -notin '.db','.log','.zip','.keystore','.jks','.pyc' -and $_.Name -ne 'keystore.properties' };" ^
  "Compress-Archive -Path $files -DestinationPath '%OUT%' -Force"

echo [OK] Packaged: %OUT%
