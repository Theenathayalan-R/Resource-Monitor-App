#!/bin/bash
# Startup script for development environment

export ENVIRONMENT="development"

# Add any environment-specific variables here
# export ORACLE_PASSWORD="${ORACLE_PASSWORD:-}"
# export KUBERNETES_TOKEN="${KUBERNETES_TOKEN:-}"

echo "Starting Spark Pod Resource Monitor in development mode..."
./run.sh
