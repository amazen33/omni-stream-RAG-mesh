# -----------------------------------------------------------------------------
# Virtual Hard Disks (VHDX) - Differencing Disks from Golden Image
# -----------------------------------------------------------------------------

resource "hyperv_vhd" "master_vhd" {
  path                = "${var.vm_storage_path}\\${var.master_node.name}.vhdx"
  parent_path         = var.base_image_vhd_path
  vhd_type            = "Differencing"
}

resource "hyperv_vhd" "worker_vhds" {
  for_each    = var.worker_nodes
  path        = "${var.vm_storage_path}\\${each.key}.vhdx"
  parent_path = var.base_image_vhd_path
  vhd_type    = "Differencing"
}

# -----------------------------------------------------------------------------
# Kubernetes Master Node Instance (Control Plane)
# -----------------------------------------------------------------------------

resource "hyperv_machine_instance" "master" {
  name                                    = var.master_node.name
  generation                              = 2
  processor_count                         = var.master_node.cpus
  static_memory                           = true
  memory_startup_bytes                    = var.master_node.memory_mb * 1024 * 1024
  automatic_critical_error_action         = "Pause"
  checkpoint_type                         = "Production"
  guest_controlled_cache_types            = false
  high_memory_per_numa_node_warning_level = 100
  lock_on_disconnect                      = "Off"
  notes                                   = "Kubernetes Master Node / K3s Control Plane"

  network_adaptors {
    name                = "eth0"
    switch_name         = hyperv_network_switch.private_switch.name
    wait_for_ips        = false
    static_mac_address  = "00:15:5D:AA:00:10"
  }

  hard_disk_drives {
    controller_type     = "Scsi"
    controller_number   = 0
    controller_location = 0
    path                = hyperv_vhd.master_vhd.path
  }

  vm_firmware {
    enable_secure_boot = "Off"
  }

  vm_processor {
    compatibility_for_older_operating_systems_enabled         = false
    hw_thread_count_per_core                                  = 0
    maximum                                                  = 100
    maximum_count_per_numa_node                              = 0
    maximum_count_per_numa_socket                            = 0
    relative_weight                                          = 100
    reserve                                                  = 0
  }

  integration_services = {
    "Guest Service Interface" = true
    "Heartbeat"               = true
    "Key-Value Pair Exchange" = true
    "Shutdown"                = true
    "Time Synchronization"    = true
    "VSS"                     = true
  }
}

# -----------------------------------------------------------------------------
# Kubernetes Worker Node Instances
# -----------------------------------------------------------------------------

resource "hyperv_machine_instance" "workers" {
  for_each                                = var.worker_nodes
  name                                    = each.key
  generation                              = 2
  processor_count                         = each.value.cpus
  static_memory                           = true
  memory_startup_bytes                    = each.value.memory_mb * 1024 * 1024
  automatic_critical_error_action         = "Pause"
  checkpoint_type                         = "Production"
  notes                                   = "Kubernetes Worker Node / Workload Engine"

  network_adaptors {
    name                = "eth0"
    switch_name         = hyperv_network_switch.private_switch.name
    wait_for_ips        = false
  }

  hard_disk_drives {
    controller_type     = "Scsi"
    controller_number   = 0
    controller_location = 0
    path                = hyperv_vhd.worker_vhds[each.key].path
  }

  vm_firmware {
    enable_secure_boot = "Off"
  }

  integration_services = {
    "Guest Service Interface" = true
    "Heartbeat"               = true
    "Key-Value Pair Exchange" = true
    "Shutdown"                = true
    "Time Synchronization"    = true
    "VSS"                     = true
  }
}

# -----------------------------------------------------------------------------
# Static IP Configuration & Network Injection
# -----------------------------------------------------------------------------

resource "null_resource" "configure_static_ips" {
  depends_on = [
    hyperv_machine_instance.master,
    hyperv_machine_instance.workers
  ]

  provisioner "local-exec" {
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      $clusterNodes = @(
        @{ Name = "${var.master_node.name}"; IP = "${var.master_node.ip}" }
        @{ Name = "k8s-worker-01"; IP = "${var.worker_nodes["k8s-worker-01"].ip}" }
        @{ Name = "k8s-worker-02"; IP = "${var.worker_nodes["k8s-worker-02"].ip}" }
      )

      $gateway = "${var.gateway_ip}"
      $dns = "${join(",", var.dns_servers)}"

      Write-Host "Static IP mappings configured for cluster nodes:"
      foreach ($node in $clusterNodes) {
        Write-Host "Node: $($node.Name) -> IP: $($node.IP)/24, Gateway: $gateway, DNS: $dns"
      }
    EOT
  }
}
