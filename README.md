# XNL-21BCE3291-LLM-5: AWS CI/CD Pipeline for LLM Applications

A production-grade AWS CI/CD pipeline for deploying and managing Large Language Model applications with zero downtime, automatic scaling, and high availability.

## Architecture Overview

![Architecture Diagram](docs/images/architecture-diagram.png)

This pipeline implements a modern GitOps approach to deploying LLM applications on AWS with the following features:

### Core Features
- **AWS Infrastructure**: Deploy across multiple AWS regions for high availability
- **Zero-Downtime Deployments**: Blue/green deployment strategy for seamless updates
- **GitOps Workflow**: Infrastructure and application changes driven by Git
- **Automatic Scaling**: Scale based on traffic patterns and resource utilization
- **Comprehensive Monitoring**: Real-time metrics, logs, and alerts

### Advanced Capabilities
- **Optimized LLM Inference**: NVIDIA Triton Inference Server with model optimization
- **Cross-Region Federation**: Unified management of Kubernetes clusters
- **Service Mesh**: Secure service-to-service communication with Istio
- **Edge Deployment**: Optimized models for edge devices
- **Data Synchronization**: Cross-region model and data replication with MinIO

## Implementation Phases

This project is structured in phases to allow incremental implementation:

### Phase 1: Core Infrastructure
- AWS EKS clusters across multiple regions
- CI/CD pipeline with GitHub Actions
- Basic monitoring with Prometheus and Grafana


### Phase 2: LLM Optimization
- NVIDIA Triton Inference Server deployment
- Model optimization (ONNX, TensorRT)
- Auto-scaling with KEDA

### Phase 3: Advanced Federation
- Kubernetes Federation with KubeFed
- Service Mesh with Istio
- Cross-region data synchronization with MinIO

### Phase 4: Edge Deployment
- Edge-optimized LLM models
- TensorFlow Lite integration
- Edge device deployment configurations

## Project Structure

```
.
├── docs/                       # Documentation and diagrams
├── infrastructure/             # Infrastructure as Code (IaC)
│   ├── terraform/              # Terraform configurations for multi-cloud setup
│   │   └── aws/                # AWS resources
│   └── kubernetes/             # Kubernetes manifests
│       ├── base/               # Base configurations
│       ├── overlays/           # Environment-specific overlays
│       ├── federation/         # KubeFed configurations
│       └── service-mesh/       # Istio configurations
├── applications/               # Application code
│   ├── llm-service/            # Main LLM service
│   └── monitoring/             # Monitoring stack configurations
└── scripts/                    # Utility scripts for deployment and testing
```

## Getting Started

### Prerequisites
- AWS account (free tier compatible)
- kubectl, terraform, and git installed locally
- Docker for local development

### Setup Instructions
1. Clone this repository
2. Configure AWS credentials
3. Run the initialization script: `./scripts/init.sh`
4. Deploy the infrastructure: `./scripts/deploy-infra.sh`

## AI-Powered Containerized Workloads

The project includes several AI-powered components:

### NVIDIA Triton Inference Server

The NVIDIA Triton Inference Server provides a cloud and edge inferencing solution optimized for both GPUs and CPUs. It supports multiple frameworks (TensorRT, TensorFlow, PyTorch, ONNX Runtime) and can run multiple models concurrently.

To deploy the Triton Inference Server:
```bash
kubectl apply -f infrastructure/kubernetes/base/triton-inference-server.yaml
```

### Model Optimization

The project includes scripts for optimizing LLM models:
- Convert models to ONNX format for better performance
- Quantize models to reduce size and improve inference speed
- Optimize with TensorRT for GPU acceleration

To optimize a model:
```bash
python applications/llm-service/model_optimization.py --model distilgpt2 --output-dir optimized_models --quantize
```

### Edge AI Deployment

For edge devices like Raspberry Pi or Jetson Nano, the project includes:
- TensorFlow Lite models for efficient inference
- Edge-optimized container images
- Deployment configurations for edge environments

To deploy to edge devices:
```bash
kubectl apply -f infrastructure/edge/edge-deployment.yaml
```

## Multi-Cloud Kubernetes Federation

The project uses KubeFed to federate multiple Kubernetes clusters across cloud providers:

### KubeFed Setup

To set up KubeFed:
```bash
./scripts/setup-kubefed.sh
```

This will:
1. Install KubeFed in the host cluster
2. Join other clusters to the federation
3. Configure federated resources

### Service Mesh with Istio

Istio provides a service mesh for inter-cluster communication:
- Traffic management across clusters
- Security with mTLS
- Observability with distributed tracing

To set up Istio:
```bash
./scripts/setup-istio.sh --multi-cluster
```

### Cross-Cloud Data Synchronization

MinIO provides S3-compatible object storage with cross-cloud replication:
- Store and replicate models across clouds
- Cache data for faster access
- Provide a unified storage interface

To set up MinIO:
```bash
./scripts/setup-minio.sh
```

## Deployment Workflow

The CI/CD pipeline follows these steps:
1. Code changes are pushed to GitHub
2. GitHub Actions triggers the CI pipeline
3. Code is tested, built, and containerized
4. Container images are pushed to container registries
5. ArgoCD detects changes and initiates deployment
6. Blue/Green deployment ensures zero downtime
7. Monitoring confirms successful deployment

## Monitoring and Observability

The pipeline includes:
- Prometheus for metrics collection
- Grafana for visualization
- OpenTelemetry for distributed tracing
- AI-powered anomaly detection

## Security Features

- Zero-trust network architecture
- Secret management with HashiCorp Vault
- Policy enforcement with Open Policy Agent
- Automated security scanning

## Rollback Strategy

In case of deployment issues:
1. Automated health checks detect problems
2. ArgoCD automatically reverts to the previous stable version
3. Traffic is redirected to the stable deployment
4. Alerts notify the team of the rollback

## Demo

[Link to Demo Video](https://drive.google.com/file/d/1KCaGycopz98cCL8PiI9UcH17LGjEbXsa/view?usp=sharing)

## License

MIT 