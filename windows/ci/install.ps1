[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PgRoot,[Parameter(Mandatory=$true)][string]$UpstreamDir)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$name='orafce'
$dest=Join-Path $PgRoot 'share/extension'
$dll=Join-Path $UpstreamDir "$name.dll"
if(-not(Test-Path $dll)){throw 'Compiled DLL missing'}
Copy-Item $dll (Join-Path $PgRoot "lib/$name.dll") -Force
$control=Join-Path $UpstreamDir "$name.control"
if(-not(Test-Path $control)){throw 'Upstream control missing'}
Copy-Item $control $dest -Force
$sqlFiles=@(Get-ChildItem $UpstreamDir -File -Filter "$name--*.sql")
if($sqlFiles.Count -lt 20){throw "Missing upstream SQL migration files for $name"}
foreach($file in $sqlFiles){Copy-Item $file.FullName $dest -Force}
