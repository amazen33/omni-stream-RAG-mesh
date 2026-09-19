terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.15"
    }
  }
}

variable "location" {
  type    = string
  default = "East US"
}

variable "name" {
  type    = string
  default = "hybridrag"

  validation {
    condition     = can(regex("^[a-z0-9]{3,20}$", var.name))
    error_message = "name must be 3-20 lowercase alphanumeric characters so it can prefix the storage account."
  }
}

# These values are consumed by the provider-neutral Ansible mesh play after a
# reviewed AKS cluster module has created the Kubernetes control plane.
variable "spire_trust_domain" {
  type        = string
  description = "Unique SPIFFE trust domain for this Azure cluster."

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9._-]*$", var.spire_trust_domain)) && !contains(["example.org", "example.com", "localhost"], var.spire_trust_domain)
    error_message = "spire_trust_domain must be a non-example lowercase SPIFFE trust domain."
  }
}

variable "spire_cluster_name" {
  type        = string
  description = "AKS cluster name registered by SPIRE."
}

variable "mesh_ingress_host" {
  type        = string
  description = "Public DNS host served by the WAF and Istio gateway."
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "main" {
  name     = "${var.name}-rg"
  location = var.location
}

resource "azurerm_storage_account" "audit" {
  name                            = "${var.name}audit"
  resource_group_name             = azurerm_resource_group.main.name
  location                        = azurerm_resource_group.main.location
  account_tier                    = "Standard"
  account_replication_type        = "ZRS"
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false

  blob_properties {
    versioning_enabled = true

    container_delete_retention_policy {
      days = 30
    }
  }
}

resource "azurerm_storage_container" "audit" {
  name                  = "audit"
  storage_account_id    = azurerm_storage_account.audit.id
  container_access_type = "private"
}

output "mesh_deployment_contract" {
  value = {
    deployment_profile = "azure"
    spire_trust_domain = var.spire_trust_domain
    spire_cluster_name = var.spire_cluster_name
    mesh_ingress_host  = var.mesh_ingress_host
    edge_waf           = "Azure WAF or equivalent must forward only to the private Istio gateway"
  }
}
