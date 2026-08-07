@echo off
setlocal

set "SOURCE_DIR=%~dp0"
set "INSTALL_DIR=%LOCALAPPDATA%\PontoFuncionarios"
set "DESKTOP_DIR=%USERPROFILE%\Desktop"
set "SHORTCUT_NAME=Ponto Funcionarios.lnk"
set "DB_FILE=%INSTALL_DIR%\data\ponto_funcionarios.db"
set "BACKUP_DIR=%INSTALL_DIR%\backups"

echo Instalando Ponto Funcionarios...
echo Origem: "%SOURCE_DIR%"
echo Destino: "%INSTALL_DIR%"

set "INTERACTIVE=1"
if /I "%~1"=="/quiet" set "INTERACTIVE=0"

if not exist "%SOURCE_DIR%PontoFuncionarios.exe" if not exist "%SOURCE_DIR%desktop_app.py" (
  echo ERRO: arquivos do programa nao encontrados na pasta do instalador.
  if "%INTERACTIVE%"=="1" pause
  exit /b 1
)

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%INSTALL_DIR%\data" mkdir "%INSTALL_DIR%\data"
if not exist "%INSTALL_DIR%\scripts" mkdir "%INSTALL_DIR%\scripts"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

taskkill /IM PontoFuncionarios.exe /F >nul 2>nul

if exist "%DB_FILE%" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$db='%DB_FILE%'; $backupDir='%BACKUP_DIR%'; New-Item -ItemType Directory -Path $backupDir -Force | Out-Null; $backup=Join-Path $backupDir ('ponto_funcionarios_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.db'); Copy-Item -LiteralPath $db -Destination $backup -Force"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$install='%INSTALL_DIR%'; $preserve=@('data','backups'); if (Test-Path -LiteralPath $install) { Get-ChildItem -LiteralPath $install -Force | Where-Object { $preserve -notcontains $_.Name } | Remove-Item -Recurse -Force }"
if not exist "%INSTALL_DIR%\data" mkdir "%INSTALL_DIR%\data"
if not exist "%INSTALL_DIR%\scripts" mkdir "%INSTALL_DIR%\scripts"

if exist "%SOURCE_DIR%PontoFuncionarios.exe" copy /Y "%SOURCE_DIR%PontoFuncionarios.exe" "%INSTALL_DIR%\PontoFuncionarios.exe" >nul
if exist "%SOURCE_DIR%desktop_app.py" copy /Y "%SOURCE_DIR%desktop_app.py" "%INSTALL_DIR%\desktop_app.py" >nul
if exist "%SOURCE_DIR%Abrir_Ponto_Desktop.bat" copy /Y "%SOURCE_DIR%Abrir_Ponto_Desktop.bat" "%INSTALL_DIR%\Abrir_Ponto_Desktop.bat" >nul
if exist "%SOURCE_DIR%Abrir_Ponto_Desktop.vbs" copy /Y "%SOURCE_DIR%Abrir_Ponto_Desktop.vbs" "%INSTALL_DIR%\Abrir_Ponto_Desktop.vbs" >nul
if exist "%SOURCE_DIR%README.md" copy /Y "%SOURCE_DIR%README.md" "%INSTALL_DIR%\README.md" >nul
if exist "%SOURCE_DIR%version.json" copy /Y "%SOURCE_DIR%version.json" "%INSTALL_DIR%\version.json" >nul

if not exist "%INSTALL_DIR%\data\ponto_funcionarios.db" (
  if exist "%SOURCE_DIR%data\ponto_funcionarios.db" (
    copy /Y "%SOURCE_DIR%data\ponto_funcionarios.db" "%INSTALL_DIR%\data\ponto_funcionarios.db" >nul
  )
)

if exist "%SOURCE_DIR%data\dados_atuais_app.json" copy /Y "%SOURCE_DIR%data\dados_atuais_app.json" "%INSTALL_DIR%\data\dados_atuais_app.json" >nul
if exist "%SOURCE_DIR%data\dados_antigos_app.json" copy /Y "%SOURCE_DIR%data\dados_antigos_app.json" "%INSTALL_DIR%\data\dados_antigos_app.json" >nul
if exist "%SOURCE_DIR%scripts" xcopy "%SOURCE_DIR%scripts" "%INSTALL_DIR%\scripts" /E /I /Y >nul
if exist "%SOURCE_DIR%import_legacy_db.py" copy /Y "%SOURCE_DIR%import_legacy_db.py" "%INSTALL_DIR%\scripts\import_legacy_db.py" >nul
if exist "%SOURCE_DIR%export_sqlite_to_app_state.py" copy /Y "%SOURCE_DIR%export_sqlite_to_app_state.py" "%INSTALL_DIR%\scripts\export_sqlite_to_app_state.py" >nul
if exist "%SOURCE_DIR%migrate_sqlite_to_postgres.py" copy /Y "%SOURCE_DIR%migrate_sqlite_to_postgres.py" "%INSTALL_DIR%\scripts\migrate_sqlite_to_postgres.py" >nul
if exist "%SOURCE_DIR%setup_postgres_empresa.ps1" copy /Y "%SOURCE_DIR%setup_postgres_empresa.ps1" "%INSTALL_DIR%\scripts\setup_postgres_empresa.ps1" >nul
if exist "%SOURCE_DIR%backup_postgres_diario.ps1" copy /Y "%SOURCE_DIR%backup_postgres_diario.ps1" "%INSTALL_DIR%\scripts\backup_postgres_diario.ps1" >nul
if exist "%SOURCE_DIR%criar_tarefa_backup_postgres.ps1" copy /Y "%SOURCE_DIR%criar_tarefa_backup_postgres.ps1" "%INSTALL_DIR%\scripts\criar_tarefa_backup_postgres.ps1" >nul

if exist "%INSTALL_DIR%\version.json" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$version=(Get-Content -Raw -LiteralPath '%INSTALL_DIR%\version.json' | ConvertFrom-Json).version; Set-Content -LiteralPath '%INSTALL_DIR%\installed_version.txt' -Value $version -Encoding ASCII"
)

if exist "%INSTALL_DIR%\PontoFuncionarios.exe" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$shell=New-Object -ComObject WScript.Shell; $shortcut=$shell.CreateShortcut('%DESKTOP_DIR%\%SHORTCUT_NAME%'); $shortcut.TargetPath='%INSTALL_DIR%\PontoFuncionarios.exe'; $shortcut.Arguments=''; $shortcut.WorkingDirectory='%INSTALL_DIR%'; $shortcut.IconLocation='%INSTALL_DIR%\PontoFuncionarios.exe,0'; $shortcut.Description='Sistema Controle de Ponto - Ponto Funcionarios'; $shortcut.Save()"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$shell=New-Object -ComObject WScript.Shell; $shortcut=$shell.CreateShortcut('%DESKTOP_DIR%\%SHORTCUT_NAME%'); $shortcut.TargetPath='%SystemRoot%\System32\wscript.exe'; $shortcut.Arguments='""%INSTALL_DIR%\Abrir_Ponto_Desktop.vbs""'; $shortcut.WorkingDirectory='%INSTALL_DIR%'; $shortcut.IconLocation='%SystemRoot%\System32\shell32.dll,44'; $shortcut.Description='Sistema Controle de Ponto - Ponto Funcionarios'; $shortcut.Save()"
)

if errorlevel 1 (
  echo ERRO: nao foi possivel criar o atalho na Area de Trabalho.
  if "%INTERACTIVE%"=="1" pause
  exit /b 1
)

echo.
echo Instalacao concluida.
echo Atalho criado: "%DESKTOP_DIR%\%SHORTCUT_NAME%"
echo.
if "%INTERACTIVE%"=="1" pause
