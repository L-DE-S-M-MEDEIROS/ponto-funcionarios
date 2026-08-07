param(
  [string]$PostgresBin = "C:\Program Files\PostgreSQL\17\bin",
  [string]$AdminUser = "postgres",
  [string]$Database = "ponto_funcionarios",
  [string]$AppUser = "ponto_app",
  [Parameter(Mandatory = $true)]
  [string]$AppPassword,
  [int]$Port = 5432,
  [string]$ListenAddresses = "*"
)

$ErrorActionPreference = "Stop"
$psql = Join-Path $PostgresBin "psql.exe"
if (!(Test-Path -LiteralPath $psql)) {
  throw "psql.exe nao encontrado em $psql. Ajuste -PostgresBin para a pasta bin do PostgreSQL."
}

$escapedPassword = $AppPassword.Replace("'", "''")
$sql = @"
DO `$`$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$AppUser') THEN
    CREATE ROLE $AppUser LOGIN PASSWORD '$escapedPassword';
  ELSE
    ALTER ROLE $AppUser LOGIN PASSWORD '$escapedPassword';
  END IF;
END
`$`$;

SELECT 'CREATE DATABASE $Database OWNER $AppUser'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$Database')\gexec

\connect $Database

GRANT ALL PRIVILEGES ON DATABASE $Database TO $AppUser;
GRANT ALL ON SCHEMA public TO $AppUser;
ALTER SCHEMA public OWNER TO $AppUser;
"@

$tmpSql = Join-Path $env:TEMP "setup_ponto_postgres.sql"
Set-Content -LiteralPath $tmpSql -Value $sql -Encoding UTF8
& $psql -U $AdminUser -p $Port -f $tmpSql

$dataDir = Get-ChildItem "C:\Program Files\PostgreSQL" -Directory -ErrorAction SilentlyContinue |
  Sort-Object Name -Descending |
  ForEach-Object { Join-Path $_.FullName "data" } |
  Where-Object { Test-Path -LiteralPath (Join-Path $_ "postgresql.conf") } |
  Select-Object -First 1

if ($dataDir) {
  $postgresqlConf = Join-Path $dataDir "postgresql.conf"
  $pgHba = Join-Path $dataDir "pg_hba.conf"
  $conf = Get-Content -LiteralPath $postgresqlConf
  if ($conf -match "^\s*#?\s*listen_addresses\s*=") {
    $conf = $conf -replace "^\s*#?\s*listen_addresses\s*=.*$", "listen_addresses = '$ListenAddresses'"
  } else {
    $conf += "listen_addresses = '$ListenAddresses'"
  }
  Set-Content -LiteralPath $postgresqlConf -Value $conf -Encoding ASCII

  $hba = Get-Content -LiteralPath $pgHba
  $line = "host    $Database    $AppUser    192.168.0.0/16    scram-sha-256"
  if ($hba -notcontains $line) {
    Add-Content -LiteralPath $pgHba -Value $line -Encoding ASCII
  }
}

New-NetFirewallRule -DisplayName "PostgreSQL Ponto Funcionarios 5432" -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow -ErrorAction SilentlyContinue | Out-Null

Get-Service postgresql* | Restart-Service -Force
Write-Host "PostgreSQL preparado. Banco: $Database | Usuario: $AppUser | Porta: $Port"
