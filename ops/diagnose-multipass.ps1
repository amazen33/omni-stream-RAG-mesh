param([Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference = 'Stop'
$result = [ordered]@{}
try {
    $result.images = @(Get-ChildItem -LiteralPath 'E:\Hyper-V\MultipassData' -Recurse -Filter '*.vhdx' -File | ForEach-Object {
        try { Get-VHD -Path $_.FullName | Select-Object Path,Size,FileSize,MinimumSize,ParentPath } catch { @{path=$_.TargetObject; error=$_.Exception.Message} }
    })
    $result.events = @(Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Multipass'; StartTime=(Get-Date).AddMinutes(-20)} -MaxEvents 30 -ErrorAction SilentlyContinue | Select-Object TimeCreated,Message)
} catch { $result.error = $_.Exception.Message }
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
