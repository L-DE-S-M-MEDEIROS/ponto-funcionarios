param(
  [string]$PostgresBin = "C:\Program Files\PostgreSQL\17\bin",
  [string]$BackupDir = "$env:USERPROFILE\Documents\Backups Ponto Funcionarios",
  [string]$HostName = "localhost",
  [int]$Port = 5432,
  [string]$Database = "ponto_funcionarios",
  [string]$User = "ponto_app",
  [Parameter(Mandatory = $true)]
  [string]$Password
)

$ErrorActionPreference = "Stop"
$pgDump = Join-Path $PostgresBin "pg_dump.exe"
if (!(Test-Path -LiteralPath $pgDump)) {
  throw "pg_dump.exe nao encontrado em $pgDump. Ajuste -PostgresBin para a pasta bin do PostgreSQL."
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$out = Join-Path $BackupDir "ponto_funcionarios_$stamp.backup"
$env:PGPASSWORD = $Password
& $pgDump -h $HostName -p $Port -U $User -d $Database -F c -f $out
if ($LASTEXITCODE -ne 0) {
  throw "pg_dump falhou com codigo $LASTEXITCODE"
}

Get-ChildItem -LiteralPath $BackupDir -Filter "ponto_funcionarios_*.backup" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -Skip 30 |
  Remove-Item -Force

Write-Host "Backup criado: $out"
