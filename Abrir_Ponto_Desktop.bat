@echo off
cd /d "%~dp0"

if exist "C:\Python314\python.exe" (
  "C:\Python314\python.exe" desktop_app.py
  exit /b
)

if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
  "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" desktop_app.py
  exit /b
)

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 desktop_app.py
  exit /b
)

where python >nul 2>nul
if %errorlevel%==0 (
  python desktop_app.py
  exit /b
)

echo Python nao encontrado.
echo Instale o Python 3 ou execute pelo ambiente do Codex.
pause
