param([Parameter(Mandatory=$true)][string]$ResultPath)
$ErrorActionPreference = 'Stop'
$source = 'C:\ProgramData\Multipass'
$destination = 'E:\Hyper-V\MultipassData'
$serviceKey = 'HKLM:\SYSTEM\CurrentControlSet\Services\Multipass'
$previousMachine = [Environment]::GetEnvironmentVariable('MULTIPASS_STORAGE', 'Machine')
$previousService = (Get-ItemProperty -LiteralPath $serviceKey -Name Environment -ErrorAction SilentlyContinue).Environment
try {
    if ($previousMachine -and $previousMachine -ne $destination) { throw 'An unexpected custom storage path is already configured.' }
    if (@(Get-VM | Where-Object { $_.Name -in @('Ansible','Master','Worker-1','Worker-2') -and $_.State -ne 'Off' }).Count) {
        throw 'The old Multipass VMs must remain stopped during storage configuration.'
    }
    if ($previousMachine -eq $destination) {
        @{status='already-configured'; storage=$destination} | ConvertTo-Json | Set-Content -LiteralPath $ResultPath
        exit 0
    }
    $requiredBytes = (Get-ChildItem -LiteralPath $source -Recurse -File | Measure-Object Length -Sum).Sum
    if ((Get-PSDrive E).Free -lt ($requiredBytes + 12GB)) { throw 'Insufficient E: capacity for preserving data and creating the new minimal cluster.' }
    Stop-Service -Name Multipass
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    # Copy, never mirror/delete. Preserve daemon identity and existing VM metadata.
    & robocopy $source $destination /E /COPY:DATS /DCOPY:DAT /XJ /R:1 /W:1 /NFL /NDL /NJH /NJS
    if ($LASTEXITCODE -ge 8) { throw "Multipass data copy failed: robocopy $LASTEXITCODE" }
    # Existing disk/checkpoint references deliberately retain their valid C: paths.
    # New instances are created under the new E: storage root.
    [Environment]::SetEnvironmentVariable('MULTIPASS_STORAGE', $destination, 'Machine')
    $environment = @($previousService | Where-Object { $_ -notmatch '^MULTIPASS_STORAGE=' }) + "MULTIPASS_STORAGE=$destination"
    New-ItemProperty -LiteralPath $serviceKey -Name Environment -PropertyType MultiString -Value $environment -Force | Out-Null
    Start-Service -Name Multipass
    @{status='configured'; storage=$destination; preservedOriginal=$source; existingDisks='Original registered paths retained, including checkpoint chains'} | ConvertTo-Json | Set-Content -LiteralPath $ResultPath
} catch {
    $failureMessage = $_.Exception.Message
    [Environment]::SetEnvironmentVariable('MULTIPASS_STORAGE', $previousMachine, 'Machine')
    if ($null -eq $previousService) {
        Remove-ItemProperty -LiteralPath $serviceKey -Name Environment -ErrorAction SilentlyContinue
    } else {
        New-ItemProperty -LiteralPath $serviceKey -Name Environment -PropertyType MultiString -Value $previousService -Force | Out-Null
    }
    Start-Service -Name Multipass -ErrorAction SilentlyContinue
    @{status='failed'; error=$failureMessage; originalDataPreserved=$true} | ConvertTo-Json | Set-Content -LiteralPath $ResultPath
    exit 1
}
