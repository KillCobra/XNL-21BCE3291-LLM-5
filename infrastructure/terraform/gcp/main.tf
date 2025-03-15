provider "google" {
  project = var.project_id
  region  = var.region
}

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
  
  backend "local" {
    path = "terraform.tfstate"
  }
}

# VPC for GKE
resource "google_compute_network" "vpc" {
  name                    = "llm-pipeline-vpc"
  auto_create_subnetworks = false
}

# Subnet for GKE
resource "google_compute_subnetwork" "subnet" {
  name          = "llm-pipeline-subnet"
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = "10.10.0.0/16"
  
  secondary_ip_range {
    range_name    = "services-range"
    ip_cidr_range = "10.20.0.0/16"
  }
  
  secondary_ip_range {
    range_name    = "pod-ranges"
    ip_cidr_range = "10.30.0.0/16"
  }
}

# GKE cluster (minimal configuration)
resource "google_container_cluster" "primary" {
  name     = "llm-pipeline-cluster"
  location = var.region
  
  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1
  
  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.subnet.name
  
  ip_allocation_policy {
    cluster_secondary_range_name  = "pod-ranges"
    services_secondary_range_name = "services-range"
  }
  
  # Enable Workload Identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
}

# Separately Managed Node Pool
resource "google_container_node_pool" "primary_nodes" {
  name       = "llm-pipeline-node-pool"
  location   = var.region
  cluster    = google_container_cluster.primary.name
  node_count = var.node_count
  
  node_config {
    oauth_scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
      "https://www.googleapis.com/auth/devstorage.read_only"
    ]
    
    labels = {
      env = var.environment
    }
    
    # Use preemptible nodes to reduce costs (not for production)
    preemptible  = true
    machine_type = "e2-small"  # Free tier eligible
    
    # Enable workload identity on the node pool
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
    
    tags = ["llm-pipeline-node"]
  }
}

# Output the kubeconfig for connecting to the cluster
data "google_client_config" "default" {}

locals {
  kubeconfig = <<KUBECONFIG
apiVersion: v1
clusters:
- cluster:
    server: https://${google_container_cluster.primary.endpoint}
    certificate-authority-data: ${google_container_cluster.primary.master_auth.0.cluster_ca_certificate}
  name: ${google_container_cluster.primary.name}
contexts:
- context:
    cluster: ${google_container_cluster.primary.name}
    user: ${google_container_cluster.primary.name}
  name: gcp
current-context: gcp
kind: Config
preferences: {}
users:
- name: ${google_container_cluster.primary.name}
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: gcloud
      args:
        - "container"
        - "clusters"
        - "get-credentials"
        - "${google_container_cluster.primary.name}"
        - "--region"
        - "${var.region}"
        - "--project"
        - "${var.project_id}"
KUBECONFIG
}

output "kubeconfig" {
  value     = local.kubeconfig
  sensitive = true
} 