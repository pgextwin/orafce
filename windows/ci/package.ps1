[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$UpstreamDir,
[Parameter(Mandatory=$true)][string]$UpstreamRepository,
[Parameter(Mandatory=$true)][string]$UpstreamRef,
[Parameter(Mandatory=$true)][string]$UpstreamVersion,
[Parameter(Mandatory=$true)][int]$PostgreSqlMajor,
[Parameter(Mandatory=$true)][string]$PostgreSqlMinor,
[string]$DistDir='dist')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$name='orafce'
$asset="$name-$UpstreamRef-pg$PostgreSqlMajor-windows-x64"
$stage=Join-Path $DistDir $asset
$zip=Join-Path $DistDir "$asset.zip"
if(Test-Path $stage){Remove-Item $stage -Recurse -Force}
if(Test-Path $zip){Remove-Item $zip -Force}
$share=Join-Path $stage 'share/extension'
$lib=Join-Path $stage 'lib'
New-Item -ItemType Directory -Force $share,$lib | Out-Null
Copy-Item (Join-Path $UpstreamDir "$name.dll") $lib
Copy-Item (Join-Path $UpstreamDir "$name.control") $share
Get-ChildItem $UpstreamDir -Filter "$name--*.sql" -File | ForEach-Object {Copy-Item $_.FullName $share}
Copy-Item (Join-Path $UpstreamDir 'LICENSE') (Join-Path $stage 'LICENSE')
Copy-Item (Join-Path $UpstreamDir 'COPYRIGHT.orafce') (Join-Path $stage 'COPYRIGHT.orafce')
$commit=(& git -C $UpstreamDir rev-parse HEAD).Trim().ToLowerInvariant()
if($LASTEXITCODE -ne 0 -or $commit -notmatch '^[0-9a-f]{40}$'){throw 'Unable to verify source provenance'}
@"
$name Windows binary package
Upstream repository: $UpstreamRepository
Upstream ref: $UpstreamRef
Upstream commit: $commit
Version: $UpstreamVersion
PostgreSQL major: $PostgreSqlMajor
PostgreSQL tested: $PostgreSqlMinor
Architecture: Windows x64
Compiler: MSVC
License: See copied upstream license files
"@ | Set-Content (Join-Path $stage 'PACKAGE-INFO.txt') -Encoding utf8
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip -CompressionLevel Optimal
if(-not(Test-Path $zip)){throw 'ZIP missing'}
