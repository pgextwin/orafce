[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PgRoot,[Parameter(Mandatory=$true)][string]$UpstreamDir)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$module='orafce'
$pgconfig=Join-Path $PgRoot 'bin/pg_config.exe'
$pgversion=(& $pgconfig --version).Trim()
if($LASTEXITCODE -ne 0 -or $pgversion -notmatch '^PostgreSQL\s+(14|15|16|17|18)\.') {throw "Unsupported pg_config: $pgversion"}
$vswhere=Join-Path ([Environment]::GetFolderPath('ProgramFilesX86')) 'Microsoft Visual Studio/Installer/vswhere.exe'
if(-not(Test-Path $vswhere)){throw "Visual Studio locator unavailable: $vswhere"}
$vsroot=[string](& $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | Select-Object -First 1)
if([string]::IsNullOrWhiteSpace($vsroot)){throw 'MSVC x64 toolchain unavailable'}
$devcmd=Join-Path $vsroot.Trim() 'Common7/Tools/VsDevCmd.bat'
if(-not(Test-Path $devcmd)){throw "VsDevCmd missing: $devcmd"}
$exports=@('Pg_magic_func','_PG_init')
$actualFunctionCount=0
foreach($file in Get-ChildItem $UpstreamDir -Recurse -Filter '*.c' -File){
    if($file.Name -eq 'sqlscan.c'){continue}
    $source=[IO.File]::ReadAllText($file.FullName,[Text.Encoding]::UTF8)
    foreach($match in [regex]::Matches($source,'PG_FUNCTION_INFO_V1\(\s*([A-Za-z_]\w*)\s*\)')){
        $name=$match.Groups[1].Value
        $exports+=@($name,"pg_finfo_$name")
        $actualFunctionCount++
    }
}
if($actualFunctionCount -lt 30){throw "Suspicious PG_FUNCTION_INFO_V1 export count: $actualFunctionCount"}
$exports=@($exports | Sort-Object -Unique)
$defpath=Join-Path $UpstreamDir "$module.pgextwin.def"
(@("LIBRARY $module","EXPORTS") + @($exports | ForEach-Object {"    $_"})) | Set-Content $defpath -Encoding ascii
# A tagged v4.16.13 checkout unexpectedly advertises '4.17' by default.
# Fail closed on changes, and align the disposable control file with provided 4.16 SQL.
$controlpath=Join-Path $UpstreamDir 'orafce.control'
$control=[IO.File]::ReadAllText($controlpath,[Text.Encoding]::UTF8)
if($control -notmatch "default_version\s*=\s*'4\.17'"){throw 'Unexpected upstream control version; investigate before packaging'}
$control=[regex]::Replace($control,"default_version\s*=\s*'4\.17'","default_version = '4.16'")
[IO.File]::WriteAllText($controlpath,$control,[Text.UTF8Encoding]::new($false))
if(-not(Test-Path (Join-Path $UpstreamDir 'orafce--4.16.sql'))){throw 'Pinned 4.16 SQL missing'}
$mesonpath=Join-Path $UpstreamDir 'meson.build'
$meson=[IO.File]::ReadAllText($mesonpath,[Text.Encoding]::UTF8)
$marker="module_lib = shared_module(" + [Environment]::NewLine + "  module_name," + [Environment]::NewLine + "  sources,"
if(-not $meson.Contains($marker)){throw 'Unexpected upstream Meson shared_module layout'}
$replacement=$marker + [Environment]::NewLine + "  vs_module_defs: 'orafce.pgextwin.def',"
$meson=$meson.Replace($marker,$replacement)
[IO.File]::WriteAllText($mesonpath,$meson,[Text.UTF8Encoding]::new($false))

$python=(Get-Command python.exe -ErrorAction Stop).Source
& $python -m pip install --disable-pip-version-check --quiet 'meson==1.8.3' 'ninja==1.11.1.4'
if($LASTEXITCODE -ne 0){throw 'Unable to install pinned build tools'}
$tmp=if($env:RUNNER_TEMP){$env:RUNNER_TEMP}else{[IO.Path]::GetTempPath()}
$builddir=Join-Path $tmp "$module-pgextwin-build"
if(Test-Path $builddir){Remove-Item $builddir -Recurse -Force}
$cmd=Join-Path $tmp "$module-pgextwin-build.cmd"
@"
@echo off
call "$devcmd" -arch=x64 -host_arch=x64
if errorlevel 1 exit /b %errorlevel%
set "PATH=$PgRoot\bin;%PATH%"
"$python" -m mesonbuild.mesonmain setup "$builddir" "$UpstreamDir" --backend ninja --buildtype=plain
if errorlevel 1 exit /b %errorlevel%
"$python" -m mesonbuild.mesonmain compile -C "$builddir"
if errorlevel 1 exit /b %errorlevel%
"@ | Set-Content $cmd -Encoding ascii
& cmd.exe /d /c $cmd
if($LASTEXITCODE -ne 0){throw "$module MSVC/Meson build failed: $LASTEXITCODE"}
$dll=Get-ChildItem $builddir -Recurse -Filter "$module.dll" -File | Select-Object -First 1
if($null -eq $dll){throw "$module.dll not generated"}
$out=Join-Path $UpstreamDir "$module.dll"
Copy-Item $dll.FullName $out -Force
$dumpcmd=Join-Path $tmp "$module-pgextwin-audit.cmd"
@"
@echo off
call "$devcmd" -arch=x64 -host_arch=x64 >nul
if errorlevel 1 exit /b %errorlevel%
dumpbin /nologo /exports "$out"
if errorlevel 1 exit /b %errorlevel%
dumpbin /nologo /dependents "$out"
"@ | Set-Content $dumpcmd -Encoding ascii
$dump=@(& cmd.exe /d /c $dumpcmd)
if($LASTEXITCODE -ne 0){throw 'dumpbin export/dependency audit failed'}
$dumptext=$dump -join [Environment]::NewLine
foreach($required in $exports){
    if($dumptext -notmatch "(?m)\b$([regex]::Escape($required))\b"){throw "DLL missing expected symbol $required"}
}
Write-Host "PASS: $module MSVC build + $($exports.Count) exports + dependencies"
