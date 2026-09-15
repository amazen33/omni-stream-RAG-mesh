terraform {
  required_version = ">= 1.5.0"

  required_providers {
    hyperv = {
      source  = "taliesins/hyperv"
      version = "~> 1.0.4"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
  }
}

provider "hyperv" {
  user     = var.hyperv_user
  password = var.hyperv_password
  host     = var.hyperv_host
  port     = var.hyperv_port
  tls      = var.hyperv_tls
}
