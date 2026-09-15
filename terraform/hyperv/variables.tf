variable "hyperv_user" {
  type        = string
  description = "Username for Hyper-V host (null if running locally via WinRM/local admin)"
  default     = null
}

variable "hyperv_password" {
  type        = string
  description = "Password for Hyper-V host"
  default     = null
  sensitive   = true
}

variable "hyperv_host" {
  type        = string
  description = "Hyper-V hostname or IP address (127.0.0.1 for local)"
  default     = "127.0.0.1"
}

variable "hyperv_port" {
  type        = number
  description = "Hyper-V WinRM/management port"
  default     = 5985
}

variable "hyperv_tls" {
  type        = bool
  description = "Enable HTTPS/TLS for Hyper-V connection"
  default     = false
}

variable "vm_storage_path" {
  type        = string
  description = "Base local path to store virtual machine disks and configuration"
  default     = "C:\\Hyper-V\\Virtual Hard Disks\\k8s-cluster"
}

variable "base_image_vhd_path" {
  type        = string
  description = "Path to base OS image (e.g. Ubuntu 22.04 / Debian 12 cloud image VHDX)"
  default     = "C:\\Hyper-V\\Templates\\ubuntu-22.04-server-cloudimg.vhdx"
}

variable "private_vswitch_name" {
  type        = string
  description = "Name of the internal private virtual switch"
  default     = "k8s-private-vswitch"
}

variable "public_vswitch_name" {
  type        = string
  description = "Name of the external/public virtual switch"
  default     = "k8s-public-vswitch"
}

variable "external_network_adapter_name" {
  type        = string
  description = "Host physical network interface name bound to the external virtual switch"
  default     = "Ethernet"
}

variable "private_subnet_cidr" {
  type        = string
  description = "CIDR block for the private Kubernetes cluster subnet"
  default     = "192.168.100.0/24"
}

variable "gateway_ip" {
  type        = string
  description = "Default gateway IP for the private cluster network"
  default     = "192.168.100.1"
}

variable "dns_servers" {
  type        = list(string)
  description = "List of upstream DNS server IP addresses"
  default     = ["1.1.1.1", "8.8.8.8"]
}

variable "admin_ssh_public_key" {
  type        = string
  description = "Public SSH key to inject into VMs for Ansible management"
  default     = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleAdminKeyForKubernetesClusterProvisioning admin@k8s"
}

variable "master_node" {
  type = object({
    name      = string
    cpus      = number
    memory_mb = number
    disk_gb   = number
    ip        = string
  })
  description = "Master control-plane node configuration"
  default = {
    name      = "k8s-master-01"
    cpus      = 2
    memory_mb = 4096
    disk_gb   = 50
    ip        = "192.168.100.10"
  }
}

variable "worker_nodes" {
  type = map(object({
    cpus      = number
    memory_mb = number
    disk_gb   = number
    ip        = string
  }))
  description = "Worker nodes configuration"
  default = {
    "k8s-worker-01" = {
      cpus      = 4
      memory_mb = 8192
      disk_gb   = 80
      ip        = "192.168.100.11"
    }
    "k8s-worker-02" = {
      cpus      = 4
      memory_mb = 8192
      disk_gb   = 80
      ip        = "192.168.100.12"
    }
  }
}
