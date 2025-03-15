#!/bin/bash

# XNL-21BCE3291-LLM-5 MinIO Setup Script
# This script sets up MinIO for cross-region data synchronization (AWS only)

set -e

echo "Setting up MinIO for cross-region data synchronization (AWS only)"

# Check for kubectl
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed. Please install it first."
    exit 1
fi

# Get available AWS contexts
AWS_CONTEXTS=$(kubectl config get-contexts -o name | grep aws)
if [ -z "$AWS_CONTEXTS" ]; then
    echo "Error: No AWS Kubernetes contexts found. Please ensure your AWS EKS clusters are configured."
    exit 1
fi

# Deploy MinIO to each AWS cluster
for CONTEXT in $AWS_CONTEXTS; do
    echo "Deploying MinIO to $CONTEXT..."
    kubectl config use-context $CONTEXT
    
    # Apply MinIO setup
    kubectl apply -f infrastructure/kubernetes/storage/minio-setup.yaml
    
    # Wait for MinIO to be ready
    echo "Waiting for MinIO to be ready in $CONTEXT..."
    kubectl wait --for=condition=available --timeout=300s deployment/minio -n minio-system
done

# Setup cross-region replication
echo "Setting up cross-region replication..."

# Get the first two contexts for source and destination
SOURCE_CONTEXT=$(echo "$AWS_CONTEXTS" | head -n 1)
DEST_CONTEXT=$(echo "$AWS_CONTEXTS" | head -n 2 | tail -n 1)

if [ "$SOURCE_CONTEXT" == "$DEST_CONTEXT" ]; then
    echo "Warning: Only one AWS context found. Cross-region replication requires at least two regions."
else
    # Get MinIO service endpoints
    kubectl config use-context $SOURCE_CONTEXT
    SOURCE_ENDPOINT=$(kubectl get svc minio -n minio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    
    kubectl config use-context $DEST_CONTEXT
    DEST_ENDPOINT=$(kubectl get svc minio -n minio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    
    # Create ConfigMap with endpoints
    kubectl create configmap minio-endpoints -n minio-system \
        --from-literal=source-endpoint=$SOURCE_ENDPOINT \
        --from-literal=dest-endpoint=$DEST_ENDPOINT \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Update replication ConfigMap
    kubectl patch configmap minio-replication-config -n minio-system \
        --patch "{\"data\":{\"SOURCE_ENDPOINT\":\"$SOURCE_ENDPOINT\",\"DEST_ENDPOINT\":\"$DEST_ENDPOINT\"}}"
    
    # Restart replication deployment
    kubectl rollout restart deployment/minio-replication -n minio-system
fi

echo "MinIO setup completed successfully!"
echo "You can access the MinIO console at: http://<MINIO_ENDPOINT>:9001"
echo "Default credentials: minioadmin / minioadmin" 