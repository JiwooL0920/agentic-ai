# DynamoDB Module Variables

variable "table_name" {
  description = "Name of the DynamoDB table"
  type        = string

  validation {
    condition     = length(var.table_name) >= 3 && length(var.table_name) <= 255
    error_message = "Table name must be between 3 and 255 characters."
  }
}

variable "hash_key" {
  description = "Hash key (partition key) for the table"
  type        = string
}

variable "hash_key_type" {
  description = "Type of hash key (S=String, N=Number, B=Binary)"
  type        = string
  default     = "S"

  validation {
    condition     = contains(["S", "N", "B"], var.hash_key_type)
    error_message = "Hash key type must be S, N, or B."
  }
}

variable "range_key" {
  description = "Range key (sort key) for the table (optional)"
  type        = string
  default     = null
}

variable "range_key_type" {
  description = "Type of range key"
  type        = string
  default     = "S"

  validation {
    condition     = contains(["S", "N", "B"], var.range_key_type)
    error_message = "Range key type must be S, N, or B."
  }
}

variable "billing_mode" {
  description = "Billing mode (PAY_PER_REQUEST or PROVISIONED)"
  type        = string
  default     = "PAY_PER_REQUEST"

  validation {
    condition     = contains(["PAY_PER_REQUEST", "PROVISIONED"], var.billing_mode)
    error_message = "Billing mode must be PAY_PER_REQUEST or PROVISIONED."
  }
}

variable "ttl_attribute" {
  description = "TTL attribute name (optional, enables automatic item expiration)"
  type        = string
  default     = null
}

variable "global_secondary_indexes" {
  description = "List of GSI configurations"
  type = list(object({
    name            = string
    hash_key        = string
    range_key       = optional(string)
    projection_type = optional(string, "ALL")
  }))
  default = []
}

variable "additional_attributes" {
  description = "Additional attributes for GSI keys (beyond hash_key and range_key)"
  type = list(object({
    name = string
    type = string
  }))
  default = []
}

variable "tags" {
  description = "Tags to apply to the table"
  type        = map(string)
  default     = {}
}
