# pgvector Module
# Purpose: Initialize PostgreSQL with pgvector extension for RAG
# Works with: CloudNative PostgreSQL (CNPG) in Kind cluster

variable "postgres_host" {
  description = "PostgreSQL host"
  type        = string
  default     = "postgres-rw.database.svc.cluster.local"
}

variable "postgres_port" {
  description = "PostgreSQL port"
  type        = number
  default     = 5432
}

variable "postgres_database" {
  description = "Database name"
  type        = string
  default     = "agentic"
}

variable "postgres_user" {
  description = "PostgreSQL user"
  type        = string
  default     = "postgres"
}

variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
  default     = ""
}

variable "blueprint_name" {
  description = "Blueprint name for schema prefix"
  type        = string
}

variable "embedding_dimensions" {
  description = "Vector embedding dimensions (768 for nomic-embed-text)"
  type        = number
  default     = 768
}

variable "tags" {
  description = "Tags for tracking"
  type        = map(string)
  default     = {}
}

# Run schema setup via local-exec
# In production, use a proper migration tool like Flyway/Liquibase
resource "null_resource" "schema_setup" {
  triggers = {
    schema_version = "1.0.0"
    blueprint      = var.blueprint_name
  }

  provisioner "local-exec" {
    command = <<-EOT
      PGPASSWORD="${var.postgres_password}" psql \
        -h ${var.postgres_host} \
        -p ${var.postgres_port} \
        -U ${var.postgres_user} \
        -d ${var.postgres_database} \
        -f ${path.module}/schema.sql \
        -v blueprint_name='${var.blueprint_name}' \
        -v embedding_dim=${var.embedding_dimensions}
    EOT

    environment = {
      PGPASSWORD = var.postgres_password
    }
  }
}

output "database_name" {
  description = "Database name"
  value       = var.postgres_database
}

output "blueprint_schema" {
  description = "Blueprint schema name"
  value       = var.blueprint_name
}

output "embedding_dimensions" {
  description = "Embedding vector dimensions"
  value       = var.embedding_dimensions
}
