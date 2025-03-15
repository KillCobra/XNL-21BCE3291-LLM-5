#!/bin/bash

# XNL-21BCE3291-LLM-5 Blue-Green Deployment Script
# This script performs a blue-green deployment for the LLM service

set -e

# Check for required tools
command -v kubectl >/dev/null 2>&1 || { echo "❌ kubectl is required but not installed. Aborting."; exit 1; }

# Get parameters
ENVIRONMENT=${1:-prod}
NEW_VERSION=${2:-latest}
NAMESPACE="llm-applications"

echo "🔄 Performing Blue-Green Deployment for LLM Service..."
echo "Environment: $ENVIRONMENT"
echo "New Version: $NEW_VERSION"

# Determine current active deployment (blue or green)
CURRENT_SERVICE=$(kubectl get service -n $NAMESPACE llm-service -o jsonpath='{.spec.selector.version}' 2>/dev/null || echo "v1")
echo "Current active version: $CURRENT_SERVICE"

# Determine new deployment color
if [[ "$CURRENT_SERVICE" == "blue" ]]; then
  NEW_COLOR="green"
  OLD_COLOR="blue"
else
  NEW_COLOR="blue"
  OLD_COLOR="green"
fi

echo "Deploying new $NEW_COLOR version..."

# Create or update the new deployment
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-service-$NEW_COLOR
  namespace: $NAMESPACE
  labels:
    app: llm-service
    version: $NEW_COLOR
spec:
  replicas: 2
  selector:
    matchLabels:
      app: llm-service
      version: $NEW_COLOR
  template:
    metadata:
      labels:
        app: llm-service
        version: $NEW_COLOR
    spec:
      containers:
      - name: llm-service
        image: llm-service:$NEW_VERSION
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 15
          periodSeconds: 20
        env:
        - name: ENVIRONMENT
          value: "$ENVIRONMENT"
        - name: VERSION
          value: "$NEW_COLOR"
EOF

# Wait for the new deployment to be ready
echo "⏳ Waiting for new deployment to be ready..."
kubectl -n $NAMESPACE rollout status deployment/llm-service-$NEW_COLOR --timeout=300s

# Verify the new deployment is healthy
READY_PODS=$(kubectl -n $NAMESPACE get pods -l "app=llm-service,version=$NEW_COLOR" -o jsonpath='{.items[*].status.containerStatuses[0].ready}' | tr ' ' '\n' | grep -c "true")
TOTAL_PODS=$(kubectl -n $NAMESPACE get pods -l "app=llm-service,version=$NEW_COLOR" --no-headers | wc -l)

if [[ "$READY_PODS" -eq "$TOTAL_PODS" && "$TOTAL_PODS" -gt 0 ]]; then
  echo "✅ New deployment is healthy. Switching traffic..."
  
  # Update the service to point to the new deployment
  kubectl -n $NAMESPACE patch service llm-service -p "{\"spec\":{\"selector\":{\"app\":\"llm-service\",\"version\":\"$NEW_COLOR\"}}}"
  
  echo "🔄 Traffic switched to the new $NEW_COLOR deployment"
  
  # Wait for a while to ensure everything is stable
  echo "⏳ Waiting for 30 seconds to verify stability..."
  sleep 30
  
  # Check if the new deployment is still healthy
  READY_PODS_AFTER=$(kubectl -n $NAMESPACE get pods -l "app=llm-service,version=$NEW_COLOR" -o jsonpath='{.items[*].status.containerStatuses[0].ready}' | tr ' ' '\n' | grep -c "true")
  
  if [[ "$READY_PODS_AFTER" -eq "$TOTAL_PODS" ]]; then
    echo "✅ New deployment is stable. Scaling down old deployment..."
    
    # Scale down the old deployment
    kubectl -n $NAMESPACE scale deployment llm-service-$OLD_COLOR --replicas=0
    
    echo "🎉 Blue-Green deployment completed successfully!"
  else
    echo "❌ New deployment became unstable after switching traffic. Rolling back..."
    
    # Roll back to the old deployment
    kubectl -n $NAMESPACE patch service llm-service -p "{\"spec\":{\"selector\":{\"app\":\"llm-service\",\"version\":\"$OLD_COLOR\"}}}"
    
    echo "✅ Traffic rolled back to the old $OLD_COLOR deployment"
  fi
else
  echo "❌ New deployment is not healthy. Aborting switch..."
fi 