# DevAssist Blueprint - Outputs

output "dynamodb_tables" {
  description = "DynamoDB table names"
  value = {
    sessions = module.sessions.table_name
    history  = module.history.table_name
  }
}

output "s3_buckets" {
  description = "S3 bucket names"
  value = {
    documents = module.documents.bucket_id
    knowledge = module.knowledge.bucket_id
  }
}

output "monitoring" {
  description = "Monitoring resources"
  value = {
    service_monitor = module.monitoring.service_monitor_name
    dashboard       = module.monitoring.dashboard_configmap_name
  }
}

output "blueprint_info" {
  description = "Blueprint information"
  value = {
    name        = var.blueprint_name
    environment = var.environment
    endpoint    = var.localstack_endpoint
  }
}
