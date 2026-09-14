terraform {required_version = ">= 1.6.0"; required_providers {azurerm = {source = "hashicorp/azurerm", version = "~> 4.15"}}}
variable "location" {type = string; default = "East US"}
variable "name" {type = string; default = "hybridrag"}
provider "azurerm" {features {}}
resource "azurerm_resource_group" "main" {name = "${var.name}-rg"; location = var.location}
resource "azurerm_storage_account" "audit" {name = "${var.name}audit"; resource_group_name = azurerm_resource_group.main.name; location = var.location; account_tier = "Standard"; account_replication_type = "ZRS"; min_tls_version = "TLS1_2"; blob_properties {versioning_enabled = true; container_delete_retention_policy {days = 30}}}
resource "azurerm_storage_container" "audit" {name = "audit"; storage_account_name = azurerm_storage_account.audit.name; container_access_type = "private"}
