#!/bin/bash

# XNL-21BCE3291-LLM-5 Infrastructure Deployment Script
# This script deploys the multi-cloud infrastructure using Terraform

set -e

echo "Deploying infrastructure for LLM service (AWS only)"

# Check for AWS CLI and install if not present
if ! command -v aws &> /dev/null; then
    echo "AWS CLI not found. Installing..."
    # Determine the package manager and install AWS CLI
    if command -v apk &> /dev/null; then
        # Alpine Linux
        apk update
        apk add --no-cache aws-cli
    elif command -v apt-get &> /dev/null; then
        # Debian/Ubuntu
        apt-get update
        apt-get install -y awscli
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL/Fedora
        yum install -y awscli
    else
        echo "Unsupported package manager. Please install AWS CLI manually."
        exit 1
    fi
    
    # Verify installation
    if ! command -v aws &> /dev/null; then
        echo "Failed to install AWS CLI. Please install it manually."
        exit 1
    fi
    echo "AWS CLI installed successfully."
fi

# Check for Terraform and install if not present
if ! command -v terraform &> /dev/null; then
    echo "Terraform not found. Installing..."
    
    # Create temporary directory for downloads
    mkdir -p /tmp/terraform_install
    cd /tmp/terraform_install
    
    # Download and install Terraform
    TERRAFORM_VERSION="1.5.7"
    
    if command -v curl &> /dev/null; then
        curl -s -O https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip
    elif command -v wget &> /dev/null; then
        wget -q https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip
    else
        echo "Neither curl nor wget found. Please install one of them or install Terraform manually."
        exit 1
    fi
    
    # Check if unzip is installed
    if ! command -v unzip &> /dev/null; then
        echo "Installing unzip..."
        if command -v apk &> /dev/null; then
            apk add --no-cache unzip
        elif command -v apt-get &> /dev/null; then
            apt-get update && apt-get install -y unzip
        elif command -v yum &> /dev/null; then
            yum install -y unzip
        else
            echo "Unsupported package manager. Please install unzip manually."
            exit 1
        fi
    fi
    
    unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip
    mv terraform /usr/local/bin/
    
    # Verify installation
    if ! command -v terraform &> /dev/null; then
        echo "Failed to install Terraform. Please install it manually."
        exit 1
    fi
    
    # Clean up
    cd - > /dev/null
    rm -rf /tmp/terraform_install
    
    echo "Terraform installed successfully."
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "Error: AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

# Deploy AWS infrastructure using Terraform
echo "Deploying AWS infrastructure..."
cd infrastructure/terraform/aws
terraform init
terraform apply -auto-approve

# Get EKS cluster info
CLUSTER_NAME=$(terraform output -raw eks_cluster_name)
REGION=$(terraform output -raw region)

# Configure kubectl for AWS
echo "Configuring kubectl for AWS EKS cluster..."
aws eks update-kubeconfig --name $CLUSTER_NAME --region $REGION

# Create namespaces
echo "Creating Kubernetes namespaces..."
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace llm-applications --dry-run=client -o yaml | kubectl apply -f -

# Install ArgoCD
echo "Installing ArgoCD..."
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
echo "Waiting for ArgoCD to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd

# Apply ArgoCD applications
echo "Configuring ArgoCD applications..."
kubectl apply -f ci-cd/argocd/applications.yaml

echo "Infrastructure deployment completed successfully!"
echo "You can access the ArgoCD UI by running: kubectl port-forward svc/argocd-server -n argocd 8080:443" 