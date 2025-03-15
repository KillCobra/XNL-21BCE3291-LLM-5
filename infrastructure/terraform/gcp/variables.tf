variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region to deploy resources"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "cluster_name" {
  description = "Name of the GKE cluster"
  type        = string
  default     = "llm-pipeline-cluster"
}

variable "node_count" {
  description = "Number of GKE nodes"
  type        = number
  default     = 2
}

variable "machine_type" {
  description = "Machine type for GKE nodes"
  type        = string
  default     = "e2-small"  # Free tier eligible
} 