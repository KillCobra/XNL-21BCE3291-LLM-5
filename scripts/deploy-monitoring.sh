#!/bin/bash

# XNL-21BCE3291-LLM-5 Monitoring Deployment Script
# This script deploys the monitoring stack (Prometheus and Grafana)

set -e

echo "🔍 Deploying Monitoring Stack..."

# Check for required tools
command -v kubectl >/dev/null 2>&1 || { echo "❌ kubectl is required but not installed. Aborting."; exit 1; }

# Create monitoring namespace if it doesn't exist
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -

# Deploy Prometheus
echo "📊 Deploying Prometheus..."
kubectl apply -f applications/monitoring/prometheus-config.yaml
kubectl apply -f applications/monitoring/prometheus-deployment.yaml

# Deploy Grafana
echo "📈 Deploying Grafana..."
kubectl apply -f applications/monitoring/grafana-deployment.yaml

# Wait for deployments to be ready
echo "⏳ Waiting for monitoring deployments to be ready..."
kubectl -n monitoring wait --for=condition=available --timeout=300s deployment/prometheus
kubectl -n monitoring wait --for=condition=available --timeout=300s deployment/grafana

# Create port-forwarding for local access (optional)
echo "🔌 Setting up port forwarding for local access..."
echo "Prometheus will be available at http://localhost:9090"
echo "Grafana will be available at http://localhost:3000 (admin/admin)"

# Start port forwarding in the background
kubectl -n monitoring port-forward svc/prometheus 9090:9090 > /dev/null 2>&1 &
PROMETHEUS_PID=$!
kubectl -n monitoring port-forward svc/grafana 3000:3000 > /dev/null 2>&1 &
GRAFANA_PID=$!

echo "✅ Monitoring stack deployed successfully!"
echo ""
echo "🔍 Access Information:"
echo "Prometheus UI: http://localhost:9090"
echo "Grafana UI: http://localhost:3000 (admin/admin)"
echo ""
echo "Press Ctrl+C to stop port forwarding"

# Trap Ctrl+C to kill port forwarding processes
trap "kill $PROMETHEUS_PID $GRAFANA_PID; echo 'Port forwarding stopped'" INT

# Keep script running to maintain port forwarding
wait 