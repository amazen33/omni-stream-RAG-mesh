param(
    [int]$Cpus = 4,
    [int]$MemoryGB = 4,
    [int]$DiskGB = 30,
    [ValidateSet('kubeadm', 'k3s')]
    [string]$KubernetesMode = 'kubeadm',
    # K3s remains available only for a deliberately selected edge/lab run.
    [string]$K3sVersion = 'v1.35.8+k3s1'
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$stateDir = Join-Path $repoRoot '.deployment'
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
$names = @('rag-ansible', 'rag-master', 'rag-worker-1', 'rag-worker-2')
$storageRoot = [Environment]::GetEnvironmentVariable('MULTIPASS_STORAGE', 'Machine')
if ($storageRoot -ne 'E:\Hyper-V\MultipassData') {
    throw 'Configure and verify E:\Hyper-V\MultipassData storage before creating this cluster.'
}
if ((Get-Item -LiteralPath $storageRoot -Force).Attributes -band [IO.FileAttributes]::Compressed) {
    throw 'The Multipass storage directory has NTFS compression enabled. Hyper-V cannot use compressed VHD files.'
}

function Invoke-Multipass {
    param([string[]]$Arguments)
    & multipass @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Multipass command failed: $($Arguments[0])" }
}

$driver = (Invoke-Multipass -Arguments @('get', 'local.driver')).Trim()
if ($driver -ne 'hyperv') { throw 'The existing Multipass driver must be hyperv.' }
$existing = (Invoke-Multipass -Arguments @('list', '--format', 'json') | ConvertFrom-Json).list
$needed = @($names | Where-Object { $_ -notin @($existing | Where-Object state -eq 'Running' | ForEach-Object name) }).Count
$freeGB = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
if ($freeGB -lt ($needed * $MemoryGB + 0.25)) {
    throw "Insufficient free host RAM: $([math]::Round($freeGB,1)) GiB; need $($needed * $MemoryGB + 0.25). Stop approved old VMs or free memory first."
}
foreach ($name in $names) {
    if ($name -in $existing.name) {
        $detail = (Invoke-Multipass -Arguments @('info', $name, '--format', 'json') | ConvertFrom-Json).info.$name
        if ([int]$detail.cpu_count -ne $Cpus) { throw "Existing $name has a different CPU allocation; refusing to overwrite it." }
        Invoke-Multipass -Arguments @('start', $name)
    } else {
        Invoke-Multipass -Arguments @('launch', '24.04', '--name', $name, '--cpus', "$Cpus", '--memory', "${MemoryGB}G", '--disk', "${DiskGB}G", '--timeout', '600')
    }
}

Invoke-Multipass -Arguments @('transfer', (Join-Path $repoRoot 'ansible/files/setup-controller.sh'), 'rag-ansible:/home/ubuntu/setup-controller.sh')
Invoke-Multipass -Arguments @('exec', 'rag-ansible', '--', 'bash', '/home/ubuntu/setup-controller.sh')
$publicKey = (Invoke-Multipass -Arguments @('exec', 'rag-ansible', '--', 'cat', '/home/ubuntu/.ssh/rag_cluster.pub')).Trim()
$publicKeyFile = Join-Path $stateDir 'controller.pub'
[IO.File]::WriteAllText($publicKeyFile, "$publicKey`n")
$addresses = @{}
$knownHosts = @()
foreach ($name in $names) {
    $detail = (Invoke-Multipass -Arguments @('info', $name, '--format', 'json') | ConvertFrom-Json).info.$name
    $addresses[$name] = @($detail.ipv4)[0]
    if ($name -eq 'rag-ansible') { continue }
    Invoke-Multipass -Arguments @('transfer', $publicKeyFile, "${name}:/home/ubuntu/controller.pub")
    Invoke-Multipass -Arguments @('transfer', (Join-Path $repoRoot 'ansible/files/authorize-controller.py'), "${name}:/home/ubuntu/authorize-controller.py")
    Invoke-Multipass -Arguments @('exec', $name, '--', 'python3', '/home/ubuntu/authorize-controller.py', '/home/ubuntu/controller.pub')
    $hostKey = (Invoke-Multipass -Arguments @('exec', $name, '--', 'cat', '/etc/ssh/ssh_host_ed25519_key.pub')).Trim()
    $knownHosts += "$($addresses[$name]) $hostKey"
}
$knownHostsFile = Join-Path $stateDir 'known_hosts'
[IO.File]::WriteAllText($knownHostsFile, (($knownHosts -join "`n") + "`n"))
Invoke-Multipass -Arguments @('transfer', $knownHostsFile, 'rag-ansible:/home/ubuntu/.ssh/known_hosts')
Invoke-Multipass -Arguments @('exec', 'rag-ansible', '--', 'chmod', '600', '/home/ubuntu/.ssh/known_hosts')

$k3sInventoryValue = if ($KubernetesMode -eq 'k3s') { "k3s_version=$K3sVersion" } else { '' }
$inventory = @"
[controller]
rag-ansible ansible_connection=local

[master]
rag-master ansible_host=$($addresses['rag-master'])

[workers]
rag-worker-1 ansible_host=$($addresses['rag-worker-1'])
rag-worker-2 ansible_host=$($addresses['rag-worker-2'])

[all:vars]
ansible_user=ubuntu
ansible_python_interpreter=/usr/bin/python3
ansible_ssh_private_key_file=/home/ubuntu/.ssh/rag_cluster
$k3sInventoryValue
"@
$inventoryFile = Join-Path $stateDir 'inventory.multipass.ini'
[IO.File]::WriteAllText($inventoryFile, ($inventory.Replace("`r`n", "`n") + "`n"))
Invoke-Multipass -Arguments @('transfer', $inventoryFile, 'rag-ansible:/home/ubuntu/rag-mesh/inventory.ini')
$bootstrapPlaybook = if ($KubernetesMode -eq 'kubeadm') { 'bootstrap-kubernetes.yaml' } else { 'bootstrap-k3s.yaml' }
Invoke-Multipass -Arguments @('exec', 'rag-ansible', '--', 'mkdir', '-p', '/home/ubuntu/rag-mesh/ansible/templates')
Invoke-Multipass -Arguments @('transfer', (Join-Path $repoRoot "ansible/$bootstrapPlaybook"), "rag-ansible:/home/ubuntu/rag-mesh/ansible/$bootstrapPlaybook")
if ($KubernetesMode -eq 'kubeadm') {
    foreach ($relativePath in @('ansible/kubernetes-vars.yaml', 'ansible/templates/kubeadm-init.yaml.j2', 'ansible/templates/calico-installation.yaml.j2')) {
        Invoke-Multipass -Arguments @('transfer', (Join-Path $repoRoot $relativePath), "rag-ansible:/home/ubuntu/rag-mesh/$relativePath")
    }
}
Invoke-Multipass -Arguments @('exec', 'rag-ansible', '--', '/home/ubuntu/ansible-venv/bin/ansible', '-i', '/home/ubuntu/rag-mesh/inventory.ini', 'all', '-m', 'ping')
Invoke-Multipass -Arguments @('exec', 'rag-ansible', '--', '/home/ubuntu/ansible-venv/bin/ansible-playbook', '-i', '/home/ubuntu/rag-mesh/inventory.ini', "/home/ubuntu/rag-mesh/ansible/$bootstrapPlaybook")
if ($KubernetesMode -eq 'kubeadm') {
    Invoke-Multipass -Arguments @('exec', 'rag-master', '--', 'sudo', 'kubectl', 'get', 'nodes', '-o', 'wide')
} else {
    Invoke-Multipass -Arguments @('exec', 'rag-master', '--', 'sudo', 'k3s', 'kubectl', 'get', 'nodes', '-o', 'wide')
}
Write-Output "New $KubernetesMode cluster ready. The controller private key remains inside rag-ansible."
