$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$evidence=Join-Path $root 'docs/verification/kokoro-integration'
$package=Get-Content -Raw (Join-Path $evidence 'package.json') | ConvertFrom-Json
$python=[IO.Path]::GetFullPath((Join-Path $root ('.scratch/kokoro-integration/real-home/'+$package.package+'/runtime/python.exe')))
$rule='ebook2mp4-kokoro-integration-'+[guid]::NewGuid().ToString('N')
$created=$false
try {
    if ((Get-NetFirewallProfile).Enabled -contains $false) { throw 'Firewall profiles must be enabled.' }
    New-NetFirewallRule -Name $rule -DisplayName $rule -Direction Outbound -Program $python -Action Block -Profile Any | Out-Null
    $created=$true
    Start-Sleep -Seconds 2
    & $python -I -B -c "import socket; s=socket.socket(); s.settimeout(2); result=s.connect_ex(('1.1.1.1',443)); s.close(); print('network_probe',result); assert result==10013"
    if ($LASTEXITCODE -ne 0) { throw 'OS network isolation probe failed.' }
    @{program=$python;rule=$rule;networkProbe='Windows 10013';blocked=$true} | ConvertTo-Json | Set-Content (Join-Path $evidence 'offline-firewall.json')
    $env:PYTHONDONTWRITEBYTECODE='1';$env:PYTHONUTF8='1'
    $env:PYTHONPATH=(Join-Path $root '.scratch/kokoro-integration/dev')+';'+$root
    $env:EBOOK2MP4_FFMPEG=(Get-Command ffmpeg).Source
    & C:/Python314/python.exe (Join-Path $PSScriptRoot 'kokoro_acceptance.py') 2>&1 | Tee-Object (Join-Path $evidence 'acceptance-log.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Offline acceptance failed.' }
} finally {
    if ($created) { Remove-NetFirewallRule -Name $rule }
    @{rule=$rule;removed=(-not [bool](Get-NetFirewallRule -Name $rule -ErrorAction SilentlyContinue))} | ConvertTo-Json | Set-Content (Join-Path $evidence 'offline-firewall-cleanup.json')
}
