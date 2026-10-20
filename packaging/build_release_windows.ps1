$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path "$PSScriptRoot\..").Path
$config = Get-Content "$repo\packaging\release.json" -Raw | ConvertFrom-Json
$work = Join-Path $env:RUNNER_TEMP 'boshy-release'
New-Item $work -ItemType Directory -Force | Out-Null
$installer = Join-Path $work 'python.exe'
Invoke-WebRequest 'https://www.python.org/ftp/python/3.14.8/python-3.14.8-amd64.exe' -OutFile $installer
if ((Get-FileHash $installer -Algorithm SHA256).Hash.ToLower() -ne '759be887b96e736a3ca886daf8d575f18fcae1a09efab6902f42d59e8999f8ef') { throw 'Python checksum mismatch' }
$signature = Get-AuthenticodeSignature $installer
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') { throw 'Python signature mismatch' }
$pythonRoot = Join-Path $work 'Python'
$p = Start-Process $installer -ArgumentList @('/quiet','InstallAllUsers=0','Include_launcher=0','Include_test=0','PrependPath=0',"TargetDir=$pythonRoot") -Wait -PassThru
if ($p.ExitCode -ne 0) { throw "Python installation failed: $($p.ExitCode)" }
$python = Join-Path $pythonRoot 'python.exe'
& $python -m pip install --only-binary=:all: Pillow==13.0.0 numpy==2.5.4 psutil==7.2.2 pycaw==20260927 comtypes==1.4.17 imageio-ffmpeg==0.6.0
if ($LASTEXITCODE -ne 0) { throw 'Runtime dependencies failed' }
& $python -m pip install PyGetWindow==0.0.9
if ($LASTEXITCODE -ne 0) { throw 'Window library failed' }
& $python -m unittest discover -s "$repo\native-linux\tests" -p test_death_visuals.py
if ($LASTEXITCODE -ne 0) { throw 'Windows death pack validation failed' }
& $python "$repo\packaging\build_windows.py" "$repo\windows-payload" "$work\portable"
if ($LASTEXITCODE -ne 0) { throw 'Portable build failed' }
$inno = Join-Path $work 'innosetup.exe'
Invoke-WebRequest 'https://github.com/jrsoftware/issrc/releases/download/is-7_1_0/innosetup-7.1.0-x64.exe' -OutFile $inno
if ((Get-FileHash $inno -Algorithm SHA256).Hash.ToLower() -ne '0362a383ed217d4c4239b5933866dd96d3eb2102737da92f80f6057a4b40df2f') { throw 'Inno Setup checksum mismatch' }
$p = Start-Process $inno -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',"/DIR=$work\InnoSetup") -Wait -PassThru
if ($p.ExitCode -ne 0) { throw 'Inno Setup installation failed' }
New-Item "$repo\dist" -ItemType Directory -Force | Out-Null
& "$work\InnoSetup\ISCC.exe" "/DPackageDir=$work\portable\BoshyRandomizer" "/DOutputDir=$repo\dist" "/DVersion=$($config.version)" "$repo\packaging\windows\setup.iss"
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
$setup = Join-Path "$repo\dist" $config.windows_file
$target = Join-Path $work 'installed'
$p = Start-Process $setup -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',"/DIR=$target") -Wait -PassThru
if ($p.ExitCode -ne 0) { throw 'Installer smoke test failed' }
$manifest = Get-Content "$target\app\package-files.json" -Raw | ConvertFrom-Json
foreach ($entry in $manifest.files.PSObject.Properties) {
 if ((Get-FileHash (Join-Path "$target\app" $entry.Name) -Algorithm SHA256).Hash.ToLower() -ne $entry.Value) { throw "Installed file mismatch: $($entry.Name)" }
}
Push-Location "$target\app"
try { & "$target\runtime\python.exe" -c 'import tkinter,PIL,numpy,psutil,death_visuals,soundpacks; assert "reset" not in soundpacks.CUES; print("Installed runtime OK")'; if ($LASTEXITCODE -ne 0) { throw 'Installed runtime smoke test failed' } } finally { Pop-Location }
$defender = 'unavailable'
try {
 $status = Get-MpComputerStatus
 if ($status.AntivirusEnabled) {
  Start-MpScan -ScanType CustomScan -ScanPath $setup
  $detections = @(Get-MpThreatDetection | Where-Object { ($_.Resources -join ' ') -like "*$($config.windows_file)*" })
  if ($detections.Count) { throw 'Installer reported by Defender' }
  $defender = 'custom scan completed without a matching detection'
 } else { $defender = 'not enabled on hosted build runner' }
} catch {
 if ($_.Exception.Message -eq 'Installer reported by Defender') { throw }
 $defender = 'scan unavailable on hosted build runner'
}
@{version=$config.version;source_commit=$env:GITHUB_SHA;file=$config.windows_file;sha256=(Get-FileHash $setup -Algorithm SHA256).Hash.ToLower();installed_files=@($manifest.files.PSObject.Properties).Count;defender=$defender} | ConvertTo-Json | Set-Content "$repo\dist\windows-build.json" -Encoding utf8
