# Terraform Modules

Reusable Terraform modules for the Agentic AI Platform.

## Available Modules

| Module | Purpose | Provider |
|--------|---------|----------|
| `dynamodb` | Session/conversation storage | LocalStack AWS |
| `s3` | Document/knowledge storage | LocalStack AWS |
| `pgvector` | Vector database schema setup | PostgreSQL |
| `observability` | Prometheus + Grafana monitoring | Kubernetes |

## Usage

Modules are called from blueprint Terraform configurations:

```hcl
module "sessions" {
  source = "../../../terraform/modules/dynamodb"

  table_name    = "${var.blueprint_name}-sessions"
  hash_key      = "session_id"
  ttl_attribute = "expires_at"
  tags          = local.tags
}

module "documents" {
  source = "../../../terraform/modules/s3"

  bucket_name = "${var.blueprint_name}-documents"
  tags        = local.tags
}
```

## Module Pattern

Each module follows the standard structure:

```
modules/<name>/
├── main.tf          # Resource definitions
├── variables.tf     # Input variables with validation
├── outputs.tf       # Output values
└── README.md        # Module documentation
```

## Configuration Layering

1. **Module defaults** - Sensible defaults in `variables.tf`
2. **Blueprint defaults** - Override in blueprint `variables.tf`
3. **Environment config** - `config/<env>/tfvars.conf` (gitignored)
4. **Example templates** - `config/example/*.example` (committed)
