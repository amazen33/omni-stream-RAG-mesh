# -----------------------------------------------------------------------------
# Hyper-V Virtual Switch Definitions (Private Subnet & Public Egress)
# -----------------------------------------------------------------------------

# Internal Virtual Switch for Private Node Interconnect & Cluster Traffic
resource "hyperv_network_switch" "private_switch" {
  name        = var.private_vswitch_name
  switch_type = "Internal"
  notes       = "Private cluster network for Kubernetes master and worker nodes (CIDR: 192.168.100.0/24)"
}

# External Virtual Switch for Internet Access and External Ingress
resource "hyperv_network_switch" "public_switch" {
  name              = var.public_vswitch_name
  switch_type       = "External"
  net_adapter_names = [var.external_network_adapter_name]
  notes             = "Public external network for ingress traffic and outbound gateway"
}

# Local provisioner to configure Host NAT Gateway for the Private Subnet
# Enables 192.168.100.0/24 to route outbound to internet through the host
resource "null_resource" "host_nat_gateway" {
  depends_on = [hyperv_network_switch.private_switch]

  provisioner "local-exec" {
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      $switchName = "${var.private_vswitch_name}"
      $gatewayIp  = "${var.gateway_ip}"
      $subnetCidr = "${var.private_subnet_cidr}"
      $natName    = "k8s-cluster-nat"

      # Check if IP address already exists on vEthernet adapter
      $adapter = Get-NetAdapter -Name "vEthernet ($switchName)" -ErrorAction SilentlyContinue
      if ($adapter) {
        $ipExists = Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -IPAddress $gatewayIp -ErrorAction SilentlyContinue
        if (-not $ipExists) {
          New-NetIPAddress -InterfaceIndex $adapter.ifIndex -IPAddress $gatewayIp -PrefixLength 24 -Confirm:$false
        }
        $natExists = Get-NetNat -Name $natName -ErrorAction SilentlyContinue
        if (-not $natExists) {
          New-NetNat -Name $natName -InternalIPInterfaceAddressPrefix $subnetCidr -Confirm:$false
        }
      }
    EOT
  }
}
