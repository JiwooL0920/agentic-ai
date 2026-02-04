# Observability Module
# Purpose: Prometheus ServiceMonitor + Grafana Dashboard
# Works with: Prometheus Operator in Kind cluster

variable "blueprint_name" {
  description = "Blueprint name for labeling"
  type        = string
}

variable "namespace" {
  description = "Kubernetes namespace for monitoring resources"
  type        = string
  default     = "monitoring"
}

variable "metrics_port" {
  description = "Port where application exposes /metrics"
  type        = number
  default     = 8001
}

variable "metrics_path" {
  description = "Path for metrics endpoint"
  type        = string
  default     = "/metrics"
}

variable "scrape_interval" {
  description = "Prometheus scrape interval"
  type        = string
  default     = "30s"
}

variable "app_namespace" {
  description = "Namespace where the application runs"
  type        = string
  default     = "default"
}

variable "enable_dashboard" {
  description = "Create Grafana dashboard ConfigMap"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags/labels for resources"
  type        = map(string)
  default     = {}
}

# Prometheus ServiceMonitor
resource "kubernetes_manifest" "service_monitor" {
  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "ServiceMonitor"
    metadata = {
      name      = "${var.blueprint_name}-monitor"
      namespace = var.namespace
      labels = merge(
        {
          blueprint = var.blueprint_name
          app       = "agentic-ai"
        },
        var.tags
      )
    }
    spec = {
      namespaceSelector = {
        matchNames = [var.app_namespace]
      }
      selector = {
        matchLabels = {
          app       = var.blueprint_name
          blueprint = var.blueprint_name
        }
      }
      endpoints = [{
        port     = "http"
        path     = var.metrics_path
        interval = var.scrape_interval
      }]
    }
  }
}

# Grafana Dashboard ConfigMap
resource "kubernetes_config_map" "dashboard" {
  count = var.enable_dashboard ? 1 : 0

  metadata {
    name      = "${var.blueprint_name}-dashboard"
    namespace = var.namespace
    labels = {
      grafana_dashboard = "1"
      blueprint         = var.blueprint_name
    }
  }

  data = {
    "${var.blueprint_name}-agents.json" = templatefile(
      "${path.module}/dashboards/agent-metrics.json",
      {
        blueprint_name = var.blueprint_name
        namespace      = var.app_namespace
      }
    )
  }
}

# Outputs
output "service_monitor_name" {
  description = "Name of the ServiceMonitor"
  value       = kubernetes_manifest.service_monitor.manifest.metadata.name
}

output "dashboard_configmap_name" {
  description = "Name of the Grafana dashboard ConfigMap"
  value       = var.enable_dashboard ? kubernetes_config_map.dashboard[0].metadata[0].name : null
}
