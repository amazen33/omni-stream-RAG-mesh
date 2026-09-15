# -----------------------------------------------------------------------------
# Hyper-V Port ACLs & Firewall Security Group Rules
# -----------------------------------------------------------------------------

# Master Node Security Group / Port ACLs
resource "null_resource" "master_security_rules" {
  depends_on = [hyperv_machine_instance.master]

  provisioner "local-exec" {
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      $vmName = "${hyperv_machine_instance.master.name}"

      # Remove default open or legacy ACLs
      Get-VMNetworkAdapter -VMName $vmName | Remove-VMNetworkAdapterAcl -ErrorAction SilentlyContinue

      # 1. Allow Outbound traffic (Stateful/Egress)
      Add-VMNetworkAdapterAcl -VMName $vmName -Action Allow -Direction Outbound

      # 2. Inbound SSH (Port 22)
      Add-VMNetworkAdapterAcl -VMName $vmName -Action Allow -Direction Inbound -LocalPort 22 -Protocol TCP

      # 3. Inbound K3s / Kubernetes API Server (Port 6443) from Private Subnet
      Add-VMNetworkAdapterAcl -VMName $vmName -Action Allow -Direction Inbound -LocalPort 6443 -Protocol TCP

      # 4. Inbound Kubelet Metrics & Exec (Port 10250)
      Add-VMNetworkAdapterAcl -VMName $vmName -Action Allow -Direction Inbound -LocalPort 10250 -Protocol TCP

      # 5. Inbound Flannel VXLAN overlay (UDP Port 8472)
      Add-VMNetworkAdapterAcl -VMName $vmName -Action Allow -Direction Inbound -LocalPort 8472 -Protocol UDP

      # 6. Inbound etcd peer communication (Ports 2379-2380)
      Add-VMNetworkAdapterAcl -VMName $vmName -Action Allow -Direction Inbound -LocalPort 2379 -Protocol TCP
      Add-VMNetworkAdapterAcl -VMName $vmName -Action Allow -Direction Inbound -LocalPort 2380 -Protocol TCP

      # 7. Deny all other unapproved inbound traffic
      Add-VMNetworkAdapterAcl -VMName $vmName -Action Deny -Direction Inbound
    EOT
  }
}

# Worker Nodes Security Group / Port ACLs
resource "null_resource" "worker_security_rules" {
  for_each   = var.worker_nodes
  depends_on = [hyperv_machine_instance.workers]

  provisioner "local-exec" {
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      $vmName = "${each.key}"

      # Remove default open or legacy ACLs
      Get-VMNetworkAdapter -VMName $vmName | Remove-VMNetworkAdapterAcl -ErrorAction SilentlyContinue

      # 1. Allow Outbound traffic
      Add-VMNetworkAdapterAcl -VMName $vmName -Action Allow -Direction Outbound

      # 2. Inbound SSH (Port 22)
      Add-VMNetworkAdapterAcl -VMName $vmName -Action Allow -Direction Inbound -LocalPort 22 -Protocol TCP

      # 3. Inbound Kubelet Metrics & Health (Port 10250)
      Add-VMNetworkAdapterAcl -VMName $vmName -Action Allow -Direction Inbound -LocalPort 10250 -Protocol TCP

      # 4. Inbound Flannel VXLAN overlay (UDP Port 8472)
      Add-VMNetworkAdapterAcl -VMName $vmName -Action Allow -Direction Inbound -LocalPort 8472 -Protocol UDP

      # 5. Inbound Ingress Controllers (HTTP 80 / HTTPS 443)
      Add-VMNetworkAdapterAcl -VMName $vmName -Action Allow -Direction Inbound -LocalPort 80 -Protocol TCP
      Add-VMNetworkAdapterAcl -VMName $vmName -Action Allow -Direction Inbound -LocalPort 443 -Protocol TCP

      # 6. Inbound Kubernetes NodePort range (30000 - 32767)
      Add-VMNetworkAdapterAcl -VMName $vmName -Action Allow -Direction Inbound -LocalPort 30000-32767 -Protocol TCP

      # 7. Deny all other unapproved inbound traffic
      Add-VMNetworkAdapterAcl -VMName $vmName -Action Deny -Direction Inbound
    EOT
  }
}
