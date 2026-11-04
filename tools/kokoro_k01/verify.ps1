param([switch]$Extra)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$python = Join-Path $root 'outputs/kokoro-k01/python/cpython-3.12-windows-x86_64-none/python.exe'
$python = $python -replace '\\+', '\'
$python = (& $python -c 'import os,sys; print(os.path.realpath(sys.executable))').Trim()
$evidence = Join-Path $root 'docs/verification/kokoro-k01'
$prefix = if ($Extra) { 'extra-' } else { '' }
$rule = 'ebook2mp4-K01-offline-' + [guid]::NewGuid().ToString('N')
$created = $false
try {
    $profiles = Get-NetFirewallProfile | Select-Object Name, Enabled
    if ($profiles.Enabled -contains $false) { throw 'All firewall profiles must be enabled.' }
    New-NetFirewallRule -Name $rule -DisplayName $rule -Direction Outbound -Program $python -Action Block -Profile Any | Out-Null
    $created = $true
    Start-Sleep -Seconds 3
    Get-NetFirewallRule -PolicyStore ActiveStore -Name $rule | Get-NetFirewallApplicationFilter | Select-Object Program | ConvertTo-Json | Set-Content (Join-Path $evidence ($prefix + 'firewall-active.json'))
    @{ rule=$rule; program=$python; profiles=$profiles; action='Block'; direction='Outbound' } | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $evidence ($prefix + 'firewall.json'))
    Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors | ConvertTo-Json | Set-Content (Join-Path $evidence 'cpu.json')
    $env:K01_FIREWALL_ACTIVE = '1'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $script = if ($Extra) { 'extra.py' } else { 'run.py' }
    & $python -B (Join-Path $PSScriptRoot $script) 2>&1 | Tee-Object (Join-Path $evidence ($prefix + 'run-log.txt'))
    if ($LASTEXITCODE -ne 0) { throw "K01 run failed: $LASTEXITCODE" }
} finally {
    if ($created) { Remove-NetFirewallRule -Name $rule }
    Remove-Item Env:K01_FIREWALL_ACTIVE -ErrorAction SilentlyContinue
    @{ rule=$rule; removed=(-not [bool](Get-NetFirewallRule -Name $rule -ErrorAction SilentlyContinue)) } | ConvertTo-Json | Set-Content (Join-Path $evidence ($prefix + 'firewall-cleanup.json'))
}
