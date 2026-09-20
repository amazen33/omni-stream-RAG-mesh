terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.12"
    }
  }
}

# This starter deliberately provisions the immutable audit data service, not a
# complete GKE/VPC/WAF platform. Use the organization's reviewed private GKE
# module, then pass its kubeconfig to the provider-neutral Ansible plays.
variable "project_id" {
  type        = string
  description = "Google Cloud project that owns the GKE target and audit bucket."

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a 6-30 character lowercase Google Cloud project ID."
  }
}

variable "location" {
  type        = string
  default     = "us-central1"
  description = "GCS bucket location; choose an approved residency location."
}

variable "name" {
  type    = string
  default = "hybrid-rag"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,24}[a-z0-9]$", var.name))
    error_message = "name must be a 3-26 character lowercase GCS-safe prefix; the project ID is appended to keep the bucket name within 63 characters."
  }
}

variable "audit_retention_days" {
  type        = number
  default     = 2555
  description = "Irreversible GCS Bucket Lock retention period. Change only through approved records governance."

  validation {
    condition     = var.audit_retention_days >= 1
    error_message = "audit_retention_days must be at least one day."
  }
}

variable "audit_service_account_id" {
  type        = string
  default     = "rag-audit"
  description = "Google service account ID created for the rag-api GKE Workload Identity binding."

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.audit_service_account_id))
    error_message = "audit_service_account_id must be a 6-30 character lowercase service-account ID."
  }
}

variable "gke_workload_identity_pool" {
  type        = string
  default     = ""
  description = "GKE Workload Identity Pool used by the target cluster. Leave empty for the standard PROJECT_ID.svc.id.goog pool."
}

variable "spire_trust_domain" {
  type        = string
  description = "Unique SPIFFE trust domain for this GKE cluster."

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9._-]*$", var.spire_trust_domain)) && !contains(["example.org", "example.com", "localhost"], var.spire_trust_domain)
    error_message = "spire_trust_domain must be a non-example lowercase SPIFFE trust domain."
  }
}

variable "spire_cluster_name" {
  type        = string
  description = "GKE cluster name registered by SPIRE."
}

variable "mesh_ingress_host" {
  type        = string
  description = "Public DNS host served by Cloud Armor/equivalent and the Istio gateway."
}

provider "google" {
  project = var.project_id
}

locals {
  gke_workload_identity_pool = var.gke_workload_identity_pool != "" ? var.gke_workload_identity_pool : "${var.project_id}.svc.id.goog"
}

resource "google_storage_bucket" "audit" {
  name                        = "${var.name}-audit-${var.project_id}"
  location                    = var.location
  force_destroy               = false
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  # is_locked is irreversible. The application refuses to start its GCS audit
  # adapter unless it observes this Bucket Lock at runtime.
  retention_policy {
    retention_period = var.audit_retention_days * 24 * 60 * 60
    is_locked        = true
  }
}

resource "google_service_account" "rag_audit" {
  account_id   = var.audit_service_account_id
  display_name = "RAG immutable audit writer"
  description  = "Create-only GCS audit writer used through GKE Workload Identity."
}

# The target GKE cluster must have Workload Identity enabled. This binding lets
# only the rag/rag-api Kubernetes service account impersonate the created GSA.
resource "google_service_account_iam_member" "rag_api_workload_identity" {
  service_account_id = google_service_account.rag_audit.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${local.gke_workload_identity_pool}[rag/rag-api]"
}

# Create-only object writes plus bucket metadata read are sufficient for the
# audit adapter. It cannot read, list, replace, or delete audit objects.
resource "google_storage_bucket_iam_member" "audit_object_creator" {
  bucket = google_storage_bucket.audit.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.rag_audit.email}"
}

resource "google_storage_bucket_iam_member" "audit_bucket_viewer" {
  bucket = google_storage_bucket.audit.name
  role   = "roles/storage.bucketViewer"
  member = "serviceAccount:${google_service_account.rag_audit.email}"
}

output "mesh_deployment_contract" {
  value = {
    deployment_profile                = "gcp"
    spire_trust_domain                = var.spire_trust_domain
    spire_cluster_name                = var.spire_cluster_name
    mesh_ingress_host                 = var.mesh_ingress_host
    edge_waf                          = "Cloud Armor or equivalent must forward only to the private Istio gateway"
    audit_backend                     = "gcs"
    audit_bucket                      = google_storage_bucket.audit.name
    workload_identity_pool            = local.gke_workload_identity_pool
    workload_identity_service_account = google_service_account.rag_audit.email
    audit_retention_days              = var.audit_retention_days
  }
}
