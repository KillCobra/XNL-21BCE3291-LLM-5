#!/bin/bash

# XNL-21BCE3291-LLM-5 Rollback Script
# This script performs a rollback to a previous version

set -e

# Check for required tools
command -v kubectl >/dev/null 2>&1 || { echo "❌ kubectl is required but not installed. Aborting."; exit 1; }

# Get parameters
ENVIRONMENT=${1:-prod}
NAMESPACE="llm-applications"

echo "⏮️ Performing Rollback for LLM Service..."
echo "Environment: $ENVIRONMENT"

# Determine current active deployment (blue or green)
CURRENT_COLOR=$(kubectl get service -n $NAMESPACE llm-service -o jsonpath='{.spec.selector.version}' 2>/dev/null || echo "blue")
echo "Current active color: $CURRENT_COLOR"

# Determine previous deployment color
if [[ "$CURRENT_COLOR" == "blue" ]]; then
  PREVIOUS_COLOR="green"
else
  PREVIOUS_COLOR="blue"
fi

# Check if previous deployment exists
PREVIOUS_DEPLOYMENT=$(kubectl -n $NAMESPACE get deployment llm-service-$PREVIOUS_COLOR 2>/dev/null || echo "")

if [[ -z "$PREVIOUS_DEPLOYMENT" ]]; then
  echo "❌ Previous deployment (llm-service-$PREVIOUS_COLOR) not found. Cannot rollback."
  exit 1
fi

echo "🔄 Rolling back to previous $PREVIOUS_COLOR deployment..."

# Scale up the previous deployment if it's scaled down
REPLICAS=$(kubectl -n $NAMESPACE get deployment llm-service-$PREVIOUS_COLOR -o jsonpath='{.spec.replicas}')
if [[ "$REPLICAS" -eq 0 ]]; then
  echo "Scaling up previous deployment..."
  kubectl -n $NAMESPACE scale deployment llm-service-$PREVIOUS_COLOR --replicas=2
  
  # Wait for the previous deployment to be ready
  echo "⏳ Waiting for previous deployment to be ready..."
  kubectl -n $NAMESPACE rollout status deployment/llm-service-$PREVIOUS_COLOR --timeout=300s
fi

# Verify the previous deployment is healthy
READY_PODS=$(kubectl -n $NAMESPACE get pods -l "app=llm-service,version=$PREVIOUS_COLOR" -o jsonpath='{.items[*].status.containerStatuses[0].ready}' | tr ' ' '\n' | grep -c "true")
TOTAL_PODS=$(kubectl -n $NAMESPACE get pods -l "app=llm-service,version=$PREVIOUS_COLOR" --no-headers | wc -l)

if [[ "$READY_PODS" -eq "$TOTAL_PODS" && "$TOTAL_PODS" -gt 0 ]]; then
  echo "✅ Previous deployment is healthy. Switching traffic..."
  
  # Update the service to point to the previous deployment
  kubectl -n $NAMESPACE patch service llm-service -p "{\"spec\":{\"selector\":{\"app\":\"llm-service\",\"version\":\"$PREVIOUS_COLOR\"}}}"
  
  echo "🔄 Traffic switched to the previous $PREVIOUS_COLOR deployment"
  
  # Scale down the current deployment
  echo "Scaling down current deployment..."
  kubectl -n $NAMESPACE scale deployment llm-service-$CURRENT_COLOR --replicas=0
  
  echo "✅ Rollback completed successfully!"
else
  echo "❌ Previous deployment is not healthy. Cannot rollback."
  exit 1
fi

# Log the rollback event
echo "$(date) - Rollback performed from $CURRENT_COLOR to $PREVIOUS_COLOR for environment $ENVIRONMENT" >> rollback-history.log 