# LLM Pipeline Setup Guide (AWS Only)

This guide provides detailed instructions for setting up the LLM pipeline on AWS.

## Prerequisites

Before you begin, ensure you have the following:

1. **AWS Account** with Free Tier access
   - AWS CLI installed and configured
   - Permissions to create EKS clusters, IAM roles, and VPCs

2. **Local Development Environment**
   - Git
   - Docker
   - kubectl
   - Terraform (v1.0.0+)
   - Python 3.10+

## Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/XNL-21BCE3291-LLM-5.git
cd XNL-21BCE3291-LLM-5
```

## Step 2: Initialize the Project Structure

Run the initialization script to set up the project structure:

```bash
chmod +x scripts/init.sh
./scripts/init.sh
```

## Step 3: Configure AWS Credentials

Create an AWS credentials file:

```bash
mkdir -p ~/.aws
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = YOUR_AWS_ACCESS_KEY
aws_secret_access_key = YOUR_AWS_SECRET_KEY
region = us-east-1
EOF
```

## Step 4: Update Terraform Variables

Create a `terraform.tfvars` file for AWS:

```bash
cat > infrastructure/terraform/aws/terraform.tfvars << EOF
region = "us-east-1"
environment = "dev"
EOF
```

## Step 5: Deploy the Infrastructure

Run the deployment script to create the infrastructure:

```bash
chmod +x scripts/deploy-infra.sh
./scripts/deploy-infra.sh
```

This script will:
1. Deploy AWS infrastructure using Terraform
2. Configure kubectl for the EKS cluster
3. Install ArgoCD for GitOps-based deployments

## Step 6: Deploy the Monitoring Stack

Deploy Prometheus and Grafana for monitoring:

```bash
chmod +x scripts/deploy-monitoring.sh
./scripts/deploy-monitoring.sh
```

## Step 7: Configure GitHub Actions

1. Go to your GitHub repository settings > Secrets
2. Add the following secrets:
   - `AWS_ACCESS_KEY_ID`: Your AWS access key
   - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key

## Step 8: Deploy the LLM Service

The LLM service will be automatically deployed by ArgoCD once you push changes to the repository. To manually trigger a deployment:

```bash
kubectl apply -f ci-cd/argocd/applications.yaml
```

## Step 9: Test the Blue-Green Deployment

To perform a blue-green deployment:

```bash
chmod +x scripts/blue-green-deploy.sh
./scripts/blue-green-deploy.sh prod v2
```

## Step 10: Test the Rollback Procedure

If you need to rollback to a previous version:

```bash
chmod +x scripts/rollback.sh
./scripts/rollback.sh prod
```

## Accessing the Services

### ArgoCD UI

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Then access ArgoCD at: https://localhost:8080

Username: admin
Password: (Get the initial password with the following command)

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

### Prometheus UI

```bash
kubectl port-forward svc/prometheus -n monitoring 9090:9090
```

Then access Prometheus at: http://localhost:9090

### Grafana UI

```bash
kubectl port-forward svc/grafana -n monitoring 3000:3000
```

Then access Grafana at: http://localhost:3000

Username: admin
Password: admin

## Troubleshooting

### Common Issues

1. **Terraform Errors**
   - Check your cloud provider credentials
   - Ensure you have sufficient permissions
   - Verify the region has the required resources available

2. **Kubernetes Connectivity Issues**
   - Verify your kubeconfig is correctly set up
   - Check if the clusters are running
   - Ensure network connectivity to the clusters

3. **ArgoCD Sync Failures**
   - Check the ArgoCD UI for error messages
   - Verify the Git repository is accessible
   - Check the Kubernetes manifests for syntax errors

### Getting Help

If you encounter any issues, please:
1. Check the logs of the specific component
2. Refer to the official documentation
3. Open an issue in the GitHub repository 