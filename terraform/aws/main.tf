terraform {
  required_version = ">= 1.6.0"
  required_providers { aws = {source = "hashicorp/aws", version = "~> 5.80"} }
}
variable "region" {type = string, default = "us-east-1"}
variable "name" {type = string, default = "hybrid-rag"}
provider "aws" {region = var.region}
resource "aws_s3_bucket" "audit" {bucket = "${var.name}-audit"}
resource "aws_s3_bucket_versioning" "audit" {bucket = aws_s3_bucket.audit.id; versioning_configuration {status = "Enabled"}}
resource "aws_s3_bucket_object_lock_configuration" "audit" {bucket = aws_s3_bucket.audit.id; rule {default_retention {mode = "COMPLIANCE"; years = 7}}}
resource "aws_s3_bucket_server_side_encryption_configuration" "audit" {bucket = aws_s3_bucket.audit.id; rule {apply_server_side_encryption_by_default {sse_algorithm = "AES256"}}}
resource "aws_opensearch_domain" "search" {domain_name = var.name; engine_version = "OpenSearch_2.17"; cluster_config {instance_type = "t3.small.search"; instance_count = 1}; ebs_options {ebs_enabled = true; volume_size = 20}; encrypt_at_rest {enabled = true}; node_to_node_encryption {enabled = true}; domain_endpoint_options {enforce_https = true}}
