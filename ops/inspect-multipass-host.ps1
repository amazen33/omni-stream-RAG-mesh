param([Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference = 'Stop'
try {
    $names = @('Ansible', 'Master', 'Worker-1', 'Worker-2', 'rag-ansible', 'rag-master', 'rag-worker-1', 'rag-worker-2')
    $vms = @(Get-VM | Where-Object { $_.Name -in $names })
    $data = [ordered]@{
        vms = @($vms | Select-Object Name, State)
        disks = @($vms | Get-VMHardDiskDrive | Select-Object VMName, ControllerType, ControllerNumber, ControllerLocation, Path)
        dvds = @($vms | Get-VMDvdDrive | Select-Object VMName, ControllerNumber, ControllerLocation, Path)
        storage = [Environment]::GetEnvironmentVariable('MULTIPASS_STORAGE', 'Machine')
        preservedDiskChecks = @($vms | Where-Object { $_.Name -notlike 'rag-*' -and $_.State -eq 'Off' } | Get-VMHardDiskDrive | ForEach-Object {
            @{vm=$_.VMName; path=$_.Path; valid=(Test-VHD -Path $_.Path)}
        })
        sourceBytes = (Get-ChildItem -LiteralPath 'C:\ProgramData\Multipass' -Recurse -File | Measure-Object Length -Sum).Sum
    }
    $data | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
} catch {
    @{error=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath $OutputPath -Encoding UTF8
    exit 1
}
