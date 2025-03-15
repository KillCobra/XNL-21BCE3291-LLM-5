#!/bin/bash

# XNL-21BCE3291-LLM-5 Istio Setup Script
# This script sets up Istio Service Mesh

set -e

echo "Setting up Istio Service Mesh (AWS only)"

# Check for required tools
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed. Please install it first."
    exit 1
fi

if ! command -v curl &> /dev/null; then
    echo "Error: curl is not installed. Please install it first."
    exit 1
fi

# Download Istio
ISTIO_VERSION="1.17.2"
echo "Downloading Istio ${ISTIO_VERSION}..."
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=${ISTIO_VERSION} sh -

# Add Istio binaries to PATH
export PATH=$PWD/istio-${ISTIO_VERSION}/bin:$PATH

# Create istio-system namespace
kubectl create namespace istio-system --dry-run=client -o yaml | kubectl apply -f -

# Install Istio using IstioOperator
echo "Installing Istio..."
istioctl install -f infrastructure/kubernetes/service-mesh/istio-setup.yaml -y

# Enable automatic sidecar injection for the llm-applications namespace
kubectl label namespace llm-applications istio.io/inject=enabled --overwrite

# Install Istio addons (Kiali, Prometheus, Grafana, Jaeger)
echo "Installing Istio addons..."
kubectl apply -f istio-${ISTIO_VERSION}/samples/addons/kiali.yaml
kubectl apply -f istio-${ISTIO_VERSION}/samples/addons/prometheus.yaml
kubectl apply -f istio-${ISTIO_VERSION}/samples/addons/grafana.yaml
kubectl apply -f istio-${ISTIO_VERSION}/samples/addons/jaeger.yaml

# Wait for Istio components to be ready
echo "Waiting for Istio components to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/istiod -n istio-system
kubectl wait --for=condition=available --timeout=300s deployment/kiali -n istio-system

# Apply Istio resources
echo "Applying Istio resources..."
kubectl apply -f infrastructure/kubernetes/service-mesh/istio-setup.yaml

# Setup for multi-region if specified
if [ "$1" == "--multi-region" ]; then
    echo "Setting up multi-region Istio mesh..."
    
    # Get AWS contexts
    AWS_CONTEXTS=$(kubectl config get-contexts -o name | grep aws)
    
    # Setup Istio for multi-region
    for CONTEXT in $AWS_CONTEXTS; do
        echo "Setting up Istio for $CONTEXT..."
        kubectl config use-context $CONTEXT
        
        # Create remote secrets for cross-cluster communication
        istioctl x create-remote-secret --name=$CONTEXT | kubectl apply -f -
    done
fi

echo "Istio setup completed successfully!"
echo "You can access the Kiali dashboard by running: istioctl dashboard kiali"
echo "You can access the Grafana dashboard by running: istioctl dashboard grafana" 