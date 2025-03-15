#!/bin/bash

# XNL-21BCE3291-LLM-5 Script to make all scripts executable
# This script makes all .sh files in the scripts directory executable

set -e

echo "🔧 Making all scripts executable..."

# Find all .sh files in the scripts directory and make them executable
find scripts -name "*.sh" -exec chmod +x {} \;

echo "✅ All scripts are now executable!" 