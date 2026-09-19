terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
  }
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "name" {
  type    = string
  default = "hybrid-rag"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,27}$", var.name))
    error_message = "name must be 3-28 lowercase alphanumeric/hyphen characters for the OpenSearch domain."
  }
}

# These outputs are the contract consumed by the provider-neutral Ansible mesh
# play. EKS itself is intentionally provisioned by the organization's reviewed
# cluster module rather than this small data-service starter.
variable "spire_trust_domain" {
  type        = string
  description = "Unique SPIFFE trust domain for this AWS cluster."

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9._-]*$", var.spire_trust_domain)) && !contains(["example.org", "example.com", "localhost"], var.spire_trust_domain)
    error_message = "spire_trust_domain must be a non-example lowercase SPIFFE trust domain."
  }
}

variable "spire_cluster_name" {
  type        = string
  description = "EKS cluster name registered by SPIRE."
}

variable "mesh_ingress_host" {
  type        = string
  description = "Public DNS host served by the WAF and Istio gateway."
}

variable "opensearch_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for the OpenSearch VPC endpoint."

  validation {
    condition     = length(var.opensearch_subnet_ids) > 0
    error_message = "Provide one or more private OpenSearch subnet IDs."
  }
}

variable "opensearch_security_group_ids" {
  type        = list(string)
  description = "Security group IDs permitting only approved private clients."

  validation {
    condition     = length(var.opensearch_security_group_ids) > 0
    error_message = "Provide at least one restrictive OpenSearch security group ID."
  }
}

provider "aws" {
  region = var.region
}

resource "aws_s3_bucket" "audit" {
  bucket              = "${var.name}-audit"
  object_lock_enabled = true
}

resource "aws_s3_bucket_versioning" "audit" {
  bucket = aws_s3_bucket.audit.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "audit" {
  bucket = aws_s3_bucket.audit.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_object_lock_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id

  rule {
    default_retention {
      mode  = "COMPLIANCE"
      years = 7
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_opensearch_domain" "search" {
  domain_name    = var.name
  engine_version = "OpenSearch_2.17"

  cluster_config {
    instance_type  = "t3.small.search"
    instance_count = 1
  }

  ebs_options {
    ebs_enabled = true
    volume_size = 20
  }

  encrypt_at_rest {
    enabled = true
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https = true
  }

  vpc_options {
    subnet_ids         = var.opensearch_subnet_ids
    security_group_ids = var.opensearch_security_group_ids
  }
}

output "mesh_deployment_contract" {
  value = {
    deployment_profile = "aws"
    spire_trust_domain = var.spire_trust_domain
    spire_cluster_name = var.spire_cluster_name
    mesh_ingress_host  = var.mesh_ingress_host
    edge_waf           = "AWS WAF or equivalent must forward only to the private Istio gateway"
  }
}
