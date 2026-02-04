# DevAssist Blueprint - Terraform Configuration
# Composes reusable modules for this specific blueprint

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

# LocalStack Provider Configuration
provider "aws" {
  access_key                  = "test"
  secret_key                  = "test"
  region                      = var.aws_region
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true

  endpoints {
    dynamodb       = var.localstack_endpoint
    s3             = var.localstack_endpoint
    lambda         = var.localstack_endpoint
    iam            = var.localstack_endpoint
    sqs            = var.localstack_endpoint
    sns            = var.localstack_endpoint
    secretsmanager = var.localstack_endpoint
  }
}

provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = var.kube_context
}

# Local variables
locals {
  tags = {
    Blueprint   = var.blueprint_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Project     = "agentic-ai"
  }
}

# Session Storage (LocalStack DynamoDB)
module "sessions" {
  source = "../../../terraform/modules/dynamodb"

  table_name    = "${var.blueprint_name}-sessions"
  hash_key      = "session_id"
  ttl_attribute = "expires_at"
  tags          = local.tags
}

# Conversation History
module "history" {
  source = "../../../terraform/modules/dynamodb"

  table_name     = "${var.blueprint_name}-history"
  hash_key       = "session_id"
  range_key      = "timestamp"
  range_key_type = "N"
  ttl_attribute  = "expires_at"

  # Define user_id attribute for GSI
  additional_attributes = [
    {
      name = "user_id"
      type = "S"
    }
  ]

  global_secondary_indexes = [
    {
      name     = "user-index"
      hash_key = "user_id"
    }
  ]

  tags = local.tags
}

# Document Storage (LocalStack S3)
module "documents" {
  source = "../../../terraform/modules/s3"

  bucket_name        = "${var.blueprint_name}-documents"
  versioning_enabled = true
  force_destroy      = var.environment == "local"

  cors_rules = var.enable_cors ? [
    {
      allowed_methods = ["GET", "PUT", "POST"]
      allowed_origins = ["http://localhost:3000"]
      allowed_headers = ["*"]
    }
  ] : []

  tags = local.tags
}

# Knowledge Base Storage
module "knowledge" {
  source = "../../../terraform/modules/s3"

  bucket_name        = "${var.blueprint_name}-knowledge"
  versioning_enabled = true
  force_destroy      = var.environment == "local"
  tags               = local.tags
}

# Observability (Prometheus + Grafana)
module "monitoring" {
  source = "../../../terraform/modules/observability"

  blueprint_name   = var.blueprint_name
  namespace        = var.monitoring_namespace
  app_namespace    = var.app_namespace
  metrics_port     = var.metrics_port
  enable_dashboard = var.enable_dashboard

  tags = local.tags
}
