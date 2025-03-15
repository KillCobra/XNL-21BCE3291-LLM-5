#!/bin/bash

# XNL-21BCE3291-LLM-5 KubeFed Setup Script
# This script sets up Kubernetes Federation (KubeFed) across multiple clusters

set -e

echo "Setting up Kubernetes Federation (AWS only)"

# Check for required tools
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed. Please install it first."
    exit 1
fi

if ! command -v helm &> /dev/null; then
    echo "Error: helm is not installed. Please install it first."
    exit 1
fi

# Get available AWS contexts
CONTEXTS=$(kubectl config get-contexts -o name | grep aws)
if [ -z "$CONTEXTS" ]; then
    echo "Error: No AWS Kubernetes contexts found. Please ensure your AWS EKS clusters are configured."
    exit 1
fi

# Select the first context as the host cluster
HOST_CONTEXT=$(echo "$CONTEXTS" | head -n 1)
echo "Using $HOST_CONTEXT as the host cluster for KubeFed"

# Switch to the host cluster context
kubectl config use-context $HOST_CONTEXT

# Create kubefed namespace
kubectl create namespace kube-federation-system --dry-run=client -o yaml | kubectl apply -f -

# Add the KubeFed Helm repository
helm repo add kubefed-charts https://raw.githubusercontent.com/kubernetes-sigs/kubefed/master/charts
helm repo update

# Install KubeFed
helm install kubefed kubefed-charts/kubefed \
    --namespace kube-federation-system \
    --version=0.9.0

# Wait for KubeFed to be ready
echo "Waiting for KubeFed to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/kubefed-controller-manager -n kube-federation-system

# Join clusters to the federation
for CONTEXT in $CONTEXTS; do
    echo "Joining cluster $CONTEXT to federation..."
    kubefedctl join $CONTEXT --cluster-context=$CONTEXT --host-cluster-context=$HOST_CONTEXT --v=2
done

# Apply federated resources
echo "Applying federated resources..."
kubectl apply -f infrastructure/kubernetes/federation/kubefed-setup.yaml

echo "KubeFed setup completed successfully!"
echo ""
echo "You can now deploy federated resources across multiple clusters."
echo "Example: kubectl apply -f infrastructure/kubernetes/federation/federated-deployment.yaml" 