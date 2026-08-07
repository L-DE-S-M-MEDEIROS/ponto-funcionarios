param(
  [string]$ScriptPath = "$PSScriptRoot\backup_postgres_diario.ps1",
  [string]$PostgresBin = "C:\Program Files\PostgreSQL\17\bin",
  [string]$BackupDir = "$env:USERPROFILE\Documents\Backups Ponto Funcionarios",
  [string]$HostName = "localhost",
  [int]$Port = 5432,
  [string]$Database = "ponto_funcionarios",
  [string]$User = "ponto_app",
  [Parameter(Mandatory = $true)]
  [string]$Password,
  [string]$At = "19:00"
)

$ErrorActionPreference = "Stop"
$argument = "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`" -PostgresBin `"$PostgresBin`" -BackupDir `"$BackupDir`" -HostName `"$HostName`" -Port $Port -Database `"$Database`" -User `"$User`" -Password `"$Password`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "Ponto Funcionarios - Backup PostgreSQL" -Action $action -Trigger $trigger -Settings $settings -Description "Backup diario do banco ponto_funcionarios" -Force | Out-Null
Write-Host "Tarefa criada: Ponto Funcionarios - Backup PostgreSQL ($At)"
