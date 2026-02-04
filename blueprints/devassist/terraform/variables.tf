# DevAssist Blueprint - Variables

variable "blueprint_name" {
  description = "Name of the blueprint"
  type        = string
  default     = "devassist"
}

variable "environment" {
  description = "Environment name (local, dev, staging, prod)"
  type        = string
  default     = "local"
}

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

variable "monitoring_namespace" {
  description = "Kubernetes namespace for monitoring"
  type        = string
  default     = "monitoring"
}

variable "app_namespace" {
  description = "Kubernetes namespace for the application"
  type        = string
  default     = "default"
}

variable "metrics_port" {
  description = "Port for metrics endpoint"
  type        = number
  default     = 8001
}

variable "enable_dashboard" {
  description = "Enable Grafana dashboard"
  type        = bool
  default     = true
}

variable "enable_cors" {
  description = "Enable CORS on S3 buckets"
  type        = bool
  default     = true
}
