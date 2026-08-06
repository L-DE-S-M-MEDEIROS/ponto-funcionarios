@echo off
setlocal

set "SOURCE_DIR=%~dp0"
set "INSTALL_DIR=%LOCALAPPDATA%\PontoFuncionarios"
set "DESKTOP_DIR=%USERPROFILE%\Desktop"
set "SHORTCUT_NAME=Ponto Funcionarios.lnk"

echo Instalando Ponto Funcionarios...
echo Origem: "%SOURCE_DIR%"
echo Destino: "%INSTALL_DIR%"

if not exist "%SOURCE_DIR%desktop_app.py" (
  echo ERRO: desktop_app.py nao encontrado na pasta do instalador.
  pause
  exit /b 1
)

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%INSTALL_DIR%\data" mkdir "%INSTALL_DIR%\data"
if not exist "%INSTALL_DIR%\scripts" mkdir "%INSTALL_DIR%\scripts"

copy /Y "%SOURCE_DIR%desktop_app.py" "%INSTALL_DIR%\desktop_app.py" >nul
copy /Y "%SOURCE_DIR%Abrir_Ponto_Desktop.bat" "%INSTALL_DIR%\Abrir_Ponto_Desktop.bat" >nul
copy /Y "%SOURCE_DIR%README.md" "%INSTALL_DIR%\README.md" >nul

if not exist "%INSTALL_DIR%\data\ponto_funcionarios.db" (
  if exist "%SOURCE_DIR%data\ponto_funcionarios.db" (
    copy /Y "%SOURCE_DIR%data\ponto_funcionarios.db" "%INSTALL_DIR%\data\ponto_funcionarios.db" >nul
  )
)

if exist "%SOURCE_DIR%data\dados_atuais_app.json" copy /Y "%SOURCE_DIR%data\dados_atuais_app.json" "%INSTALL_DIR%\data\dados_atuais_app.json" >nul
if exist "%SOURCE_DIR%data\dados_antigos_app.json" copy /Y "%SOURCE_DIR%data\dados_antigos_app.json" "%INSTALL_DIR%\data\dados_antigos_app.json" >nul
if exist "%SOURCE_DIR%scripts\import_legacy_db.py" copy /Y "%SOURCE_DIR%scripts\import_legacy_db.py" "%INSTALL_DIR%\scripts\import_legacy_db.py" >nul
if exist "%SOURCE_DIR%scripts\export_sqlite_to_app_state.py" copy /Y "%SOURCE_DIR%scripts\export_sqlite_to_app_state.py" "%INSTALL_DIR%\scripts\export_sqlite_to_app_state.py" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "$shell=New-Object -ComObject WScript.Shell; $shortcut=$shell.CreateShortcut('%DESKTOP_DIR%\%SHORTCUT_NAME%'); $shortcut.TargetPath='%INSTALL_DIR%\Abrir_Ponto_Desktop.bat'; $shortcut.WorkingDirectory='%INSTALL_DIR%'; $shortcut.IconLocation='%SystemRoot%\System32\shell32.dll,44'; $shortcut.Description='Sistema Controle de Ponto - Ponto Funcionarios'; $shortcut.Save()"

if errorlevel 1 (
  echo ERRO: nao foi possivel criar o atalho na Area de Trabalho.
  pause
  exit /b 1
)

echo.
echo Instalacao concluida.
echo Atalho criado: "%DESKTOP_DIR%\%SHORTCUT_NAME%"
echo.
pause
