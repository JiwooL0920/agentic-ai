# Shared Terraform Provider Configuration
# Configured for LocalStack (Kind cluster: dev-services-amer)

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
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

# LocalStack AWS Provider
# All AWS services emulated locally via LocalStack
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

# Kubernetes Provider for Kind cluster
provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = var.kube_context
}

# Variables with defaults
variable "localstack_endpoint" {
  description = "LocalStack endpoint URL"
  type        = string
  default     = "http://localstack.local"
}

variable "aws_region" {
  description = "AWS region (for LocalStack)"
  type        = string
  default     = "us-east-1"
}

variable "kube_context" {
  description = "Kubernetes context"
  type        = string
  default     = "kind-dev-services-amer"
}
