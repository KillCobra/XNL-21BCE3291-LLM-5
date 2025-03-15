provider "aws" {
  region = var.region
}

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
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

# Use AWS free tier compatible resources
# Note: EKS itself is not free tier, but we're using minimal resources for demo purposes

# VPC for EKS
module "vpc" {
  source = "../modules/vpc"
  
  name               = "llm-pipeline-vpc"
  cidr               = "10.0.0.0/16"
  azs                = ["${var.region}a", "${var.region}b"]
  private_subnets    = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets     = ["10.0.101.0/24", "10.0.102.0/24"]
  enable_nat_gateway = true
  single_nat_gateway = true
  
  tags = {
    Environment = var.environment
    Project     = "XNL-21BCE3291-LLM-5"
  }
}

# IAM role for EKS
resource "aws_iam_role" "eks_cluster" {
  name = "eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

# EKS Cluster (minimal configuration)
resource "aws_eks_cluster" "main" {
  name     = "llm-pipeline-cluster"
  role_arn = aws_iam_role.eks_cluster.arn
  
  vpc_config {
    subnet_ids = module.vpc.private_subnets
  }
  
  # Ensure that IAM Role permissions are created before and deleted after EKS Cluster handling
  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy
  ]
}

# IAM role for EKS node group
resource "aws_iam_role" "eks_nodes" {
  name = "eks-node-group-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "eks_container_registry_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_nodes.name
}

# EKS Node Group (using t3.small instances which are free tier eligible)
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "llm-pipeline-nodes"
  node_role_arn   = aws_iam_role.eks_nodes.arn
  subnet_ids      = module.vpc.private_subnets
  
  scaling_config {
    desired_size = 2
    max_size     = 3
    min_size     = 1
  }
  
  instance_types = ["t3.small"]
  
  # Ensure that IAM Role permissions are created before and deleted after EKS Node Group handling
  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
  ]
  
  tags = {
    Environment = var.environment
    Project     = "XNL-21BCE3291-LLM-5"
  }
}

# Output the kubeconfig for connecting to the cluster
locals {
  kubeconfig = <<KUBECONFIG
apiVersion: v1
clusters:
- cluster:
    server: ${aws_eks_cluster.main.endpoint}
    certificate-authority-data: ${aws_eks_cluster.main.certificate_authority[0].data}
  name: ${aws_eks_cluster.main.arn}
contexts:
- context:
    cluster: ${aws_eks_cluster.main.arn}
    user: ${aws_eks_cluster.main.arn}
  name: aws
current-context: aws
kind: Config
preferences: {}
users:
- name: ${aws_eks_cluster.main.arn}
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: aws
      args:
        - "eks"
        - "get-token"
        - "--cluster-name"
        - "${aws_eks_cluster.main.name}"
        - "--region"
        - "${var.region}"
KUBECONFIG
}

output "kubeconfig" {
  value     = local.kubeconfig
  sensitive = true
} 