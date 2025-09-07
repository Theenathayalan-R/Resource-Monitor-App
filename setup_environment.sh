#!/bin/bash

# Environment Setup Script for Spark Pod Resource Monitor
# Usage: ./setup_environment.sh [development|staging|production]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Emojis
CHECK="✅"
CROSS="❌"
WARNING="⚠️"
INFO="ℹ️"
GEAR="⚙️"

echo -e "${BLUE}🔧 Environment Setup for Spark Pod Resource Monitor${NC}"
echo -e "${BLUE}=================================================${NC}"

# Get environment parameter
ENVIRONMENT="${1:-development}"
echo -e "${INFO} Setting up environment: ${ENVIRONMENT}"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    echo -e "${CROSS} Invalid environment. Use: development, staging, or production"
    exit 1
fi

# Set environment variable
export ENVIRONMENT="$ENVIRONMENT"
echo -e "${CHECK} Environment variable set: ENVIRONMENT=$ENVIRONMENT"

# Create environment-specific directories
echo -e "${GEAR} Creating environment-specific directories..."
mkdir -p "logs"
mkdir -p "config"
mkdir -p "data/$ENVIRONMENT"

# Set up environment-specific log file
LOG_DIR="logs"
case "$ENVIRONMENT" in
    "development")
        LOG_FILE="$LOG_DIR/spark_monitor_dev.log"
        ;;
    "staging")
        LOG_FILE="$LOG_DIR/spark_monitor_staging.log"
        ;;
    "production")
        LOG_FILE="$LOG_DIR/spark_monitor_prod.log"
        ;;
esac

# Create log file with proper permissions
touch "$LOG_FILE"
chmod 664 "$LOG_FILE"
echo -e "${CHECK} Log file created: $LOG_FILE"

# Create environment-specific database directory for SQLite
DB_DIR="data/$ENVIRONMENT"
case "$ENVIRONMENT" in
    "development")
        DB_FILE="$DB_DIR/spark_pods_history_dev.db"
        ;;
    "staging")
        DB_FILE="$DB_DIR/spark_pods_history_staging.db"
        ;;
    "production")
        DB_FILE="$DB_DIR/spark_pods_history_prod.db"
        ;;
esac

# Create database directory
mkdir -p "$DB_DIR"
echo -e "${CHECK} Database directory created: $DB_DIR"

# Environment-specific configuration validation
echo -e "${GEAR} Validating configuration for $ENVIRONMENT..."

# Check if configuration files exist
if [[ -f "config/environments.yaml" ]]; then
    echo -e "${CHECK} Configuration file found"
else
    echo -e "${WARNING} No configuration file found. Creating default configuration..."
    
    # This would be where we copy from templates or create default configs
    echo -e "${INFO} Please ensure config/environments.yaml exists"
fi

# Environment-specific setup
case "$ENVIRONMENT" in
    "development")
        echo -e "${INFO} Development environment setup:"
        echo -e "  • Debug logging enabled"
        echo -e "  • SQLite database (default)"
        echo -e "  • Relaxed security settings"
        echo -e "  • Short data retention (3 days)"
        ;;
    "staging")
        echo -e "${INFO} Staging environment setup:"
        echo -e "  • Info logging level"
        echo -e "  • Can use Oracle or SQLite"
        echo -e "  • Standard security settings"
        echo -e "  • Medium data retention (7 days)"
        ;;
    "production")
        echo -e "${INFO} Production environment setup:"
        echo -e "  • Info logging level"
        echo -e "  • Recommended: Oracle database"
        echo -e "  • Strict security settings"
        echo -e "  • Long data retention (30 days)"
        
        # Additional production checks
        if [[ -z "${ORACLE_PASSWORD:-}" ]]; then
            echo -e "${WARNING} ORACLE_PASSWORD environment variable not set"
            echo -e "${INFO} Set it with: export ORACLE_PASSWORD='your_password'"
        fi
        
        if [[ -z "${KUBERNETES_TOKEN:-}" ]]; then
            echo -e "${WARNING} KUBERNETES_TOKEN environment variable not set"
            echo -e "${INFO} Set it with: export KUBERNETES_TOKEN='your_token'"
        fi
        ;;
esac

# Create startup script for the environment
STARTUP_SCRIPT="start_${ENVIRONMENT}.sh"
cat > "$STARTUP_SCRIPT" << EOF
#!/bin/bash
# Startup script for $ENVIRONMENT environment

export ENVIRONMENT="$ENVIRONMENT"

# Add any environment-specific variables here
# export ORACLE_PASSWORD="\${ORACLE_PASSWORD:-}"
# export KUBERNETES_TOKEN="\${KUBERNETES_TOKEN:-}"

echo "Starting Spark Pod Resource Monitor in $ENVIRONMENT mode..."
./run.sh
EOF

chmod +x "$STARTUP_SCRIPT"
echo -e "${CHECK} Created startup script: $STARTUP_SCRIPT"

# Environment summary
echo -e "\n${GREEN}${CHECK} Environment setup complete!${NC}"
echo -e "\n${BLUE}Next steps:${NC}"
echo -e "1. Review config/environments.yaml for $ENVIRONMENT settings"
echo -e "2. Set required environment variables if needed:"

case "$ENVIRONMENT" in
    "production"|"staging")
        echo -e "   ${YELLOW}export ORACLE_PASSWORD='your_oracle_password'${NC}"
        echo -e "   ${YELLOW}export KUBERNETES_TOKEN='your_k8s_token'${NC}"
        ;;
esac

echo -e "3. Install dependencies: ${YELLOW}./install.sh${NC}"
echo -e "4. Start the application: ${YELLOW}./$STARTUP_SCRIPT${NC}"

echo -e "\n${GREEN}Environment: $ENVIRONMENT${NC}"
echo -e "${GREEN}Log file: $LOG_FILE${NC}"
echo -e "${GREEN}Config: config/environments.yaml${NC}"
echo -e "${GREEN}Startup: ./$STARTUP_SCRIPT${NC}"
