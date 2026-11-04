$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$evidence = Join-Path $root 'docs/verification/kokoro-k01'
$bundle = Join-Path $root 'outputs/kokoro-k01'
$runtime = [IO.Path]::GetFullPath((Join-Path $bundle 'python/cpython-3.12.15-windows-x86_64-none'))
$running = @(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($runtime, [StringComparison]::OrdinalIgnoreCase) })
if ($running.Count) { throw 'A K01 Python process is still running. Stop verification before cleanup.' }
$rules = @('firewall.json', 'extra-firewall.json') | ForEach-Object {
    $name = (Get-Content -Raw (Join-Path $evidence $_) | ConvertFrom-Json).rule
    @{ name=$name; present=[bool](Get-NetFirewallRule -Name $name -ErrorAction SilentlyContinue) }
}
if ($rules.present -contains $true) { throw 'A test firewall rule remains active.' }
$removedCaches = 0
Get-ChildItem -LiteralPath $runtime -Recurse -Directory -Filter __pycache__ | ForEach-Object {
    $target = [IO.Path]::GetFullPath($_.FullName)
    if (-not $target.StartsWith(([IO.Path]::GetFullPath($runtime) + [IO.Path]::DirectorySeparatorChar), [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid cache cleanup target.' }
    Remove-Item -LiteralPath $target -Recurse -Force
    $removedCaches++
}
$scratch = [IO.Path]::GetFullPath((Join-Path $root '.scratch/k01'))
$expected = [IO.Path]::GetFullPath((Join-Path $root '.scratch')) + [IO.Path]::DirectorySeparatorChar + 'k01'
if ($scratch -ne $expected) { throw 'Invalid scratch cleanup target.' }
if (Test-Path -LiteralPath $scratch) { Remove-Item -LiteralPath $scratch -Recurse -Force }
$locks = @(
    (Join-Path $runtime 'python.exe'),
    (Join-Path $runtime 'Lib/site-packages/torch/lib/torch_cpu.dll')
) | ForEach-Object {
    $handle = [IO.File]::Open($_, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::None)
    $handle.Dispose()
    @{ path=$_; exclusiveRead=$true }
}
@{ remainingProcesses=$running.Count; firewallRules=$rules; runtimeLocks=$locks;
   scratchExists=(Test-Path -LiteralPath $scratch); removedBytecodeDirectories=$removedCaches;
   runtimeBytecodeDirectories=@(Get-ChildItem -LiteralPath $runtime -Directory -Recurse -Filter __pycache__).Count
} | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $evidence 'cleanup.json')
