#!/bin/bash

# XNL-21BCE3291-LLM-5 Initialization Script
# This script sets up the project structure and initializes required components

set -e

echo "🚀 Initializing Multi-Cloud CI/CD Pipeline for LLM Applications..."

# Create project directory structure
mkdir -p docs/images
mkdir -p infrastructure/terraform/{aws,gcp,modules}
mkdir -p infrastructure/kubernetes/{base,overlays/{dev,staging,prod}}
mkdir -p ci-cd/{github-actions,argocd}
mkdir -p applications/{llm-service,monitoring}
mkdir -p scripts

# Make scripts executable
chmod +x scripts/*.sh

# Initialize Git repository if not already initialized
if [ ! -d .git ]; then
  git init
  echo "Git repository initialized"
fi

# Create .gitignore
cat > .gitignore << EOF
# Local .terraform directories
**/.terraform/*

# .tfstate files
*.tfstate
*.tfstate.*

# Crash log files
crash.log

# Exclude all .tfvars files, which are likely to contain sensitive data
*.tfvars

# Ignore override files
override.tf
override.tf.json
*_override.tf
*_override.tf.json

# Ignore CLI configuration files
.terraformrc
terraform.rc

# Node modules
node_modules/

# Python virtual environment
venv/
__pycache__/
*.py[cod]

# Environment variables
.env
.env.*

# IDE files
.idea/
.vscode/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db
EOF

echo "✅ Project structure initialized successfully!"
echo "Next steps:"
echo "1. Configure cloud provider credentials"
echo "2. Run './scripts/deploy-infra.sh' to deploy the infrastructure" 