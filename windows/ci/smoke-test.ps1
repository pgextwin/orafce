[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PgRoot,[Parameter(Mandatory=$true)][int]$PgPort,[Parameter(Mandatory=$true)][int]$PostgreSqlMajor)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$name='orafce'
$bin=Join-Path $PgRoot 'bin'
$initdb=Join-Path $bin 'initdb.exe'
$pgctl=Join-Path $bin 'pg_ctl.exe'
$ready=Join-Path $bin 'pg_isready.exe'
$psql=Join-Path $bin 'psql.exe'
$tmp=if($env:RUNNER_TEMP){$env:RUNNER_TEMP}else{[IO.Path]::GetTempPath()}
$data=Join-Path $tmp "pgextwin-$name-pg$PostgreSqlMajor"
$log=Join-Path $tmp "pgextwin-$name-pg$PostgreSqlMajor.log"
$sql=Join-Path $tmp "pgextwin-$name-pg$PostgreSqlMajor.sql"
if(Test-Path $data){Remove-Item $data -Recurse -Force}
if(Test-Path $log){Remove-Item $log -Force}
try {
    & $initdb -D $data -U postgres -A trust --encoding=UTF8 --no-locale
    if($LASTEXITCODE -ne 0){throw 'initdb failed'}
    & $pgctl -D $data -l $log -o "-p $PgPort" start
    if($LASTEXITCODE -ne 0){throw 'PostgreSQL start failed'}
    $ok=$false
    for($i=0;$i -lt 45;$i++){
        & $ready -h 127.0.0.1 -p $PgPort -q
        if($LASTEXITCODE -eq 0){$ok=$true;break}
        Start-Sleep -Seconds 2
    }
    if(-not $ok){throw 'pg_isready timeout'}
    @'
SET TIME ZONE 'UTC';
CREATE EXTENSION orafce;
DO $
BEGIN
  IF oracle.last_day(DATE '2024-02-12') <> DATE '2024-02-29'
    THEN RAISE EXCEPTION 'oracle.last_day leap year wrong'; END IF;
  IF oracle.last_day(DATE '2025-02-12') <> DATE '2025-02-28'
    THEN RAISE EXCEPTION 'oracle.last_day non-leap wrong'; END IF;
  IF oracle.nvl(NULL::integer,7) <> 7
    THEN RAISE EXCEPTION 'oracle.nvl null handling wrong'; END IF;
  IF oracle.nvl(3::integer,7) <> 3
    THEN RAISE EXCEPTION 'oracle.nvl non-null handling wrong'; END IF;
END $;
DROP EXTENSION orafce CASCADE;
'@ | Set-Content -Path $sql -Encoding utf8
    & $psql -h 127.0.0.1 -p $PgPort -U postgres -d postgres -v ON_ERROR_STOP=1 -f $sql
    if($LASTEXITCODE -ne 0){throw "$name SQL functional test failed"}
    Write-Host "PASS: $name functional smoke and cleanup"
} catch {
    if(Test-Path $log){Get-Content $log -Tail 300}
    throw
} finally {
    if(Test-Path (Join-Path $data 'postmaster.pid')){& $pgctl -D $data -m immediate stop}
}
