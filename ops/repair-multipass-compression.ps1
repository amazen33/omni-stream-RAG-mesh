param([Parameter(Mandatory=$true)][string]$ResultPath)
$ErrorActionPreference = 'Stop'
$storage = 'E:\Hyper-V\MultipassData'
try {
    if ([Environment]::GetEnvironmentVariable('MULTIPASS_STORAGE','Machine') -ne $storage) { throw 'Unexpected storage root' }
    Stop-Service Multipass
    & compact.exe /U /A /F /Q $storage
    & compact.exe /U "/S:$storage" /A /I /F /Q
    $compressed = @(Get-Item -LiteralPath $storage; Get-ChildItem -LiteralPath $storage -Recurse -Force) | Where-Object { $_.Attributes -band [IO.FileAttributes]::Compressed }
    if (@($compressed).Count) { throw "Compression remains on $(@($compressed).Count) paths" }
    @{status='repaired'; storage=$storage; compressedPaths=0} | ConvertTo-Json | Set-Content -LiteralPath $ResultPath
} catch {
    @{status='failed'; error=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath $ResultPath
    exit 1
} finally {
    Start-Service Multipass
}
