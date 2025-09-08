# S3 Platform Monitoring - Enhanced Multi-Bucket Support

## Overview

The Platform Monitor now supports comprehensive S3 storage monitoring with **multi-bucket, multi-endpoint, and per-bucket credential support** - perfect for on-premises S3 deployments with multiple storage systems.

## 🌟 Key Features

### 1. **Multi-Bucket Architecture**
- **Per-bucket credentials**: Each S3 bucket can have its own access keys and endpoints
- **Mixed environments**: Support different S3 systems (MinIO, Dell ECS, NetApp StorageGRID, etc.)
- **Centralized monitoring**: Single dashboard for all your S3 storage infrastructure

### 2. **Flexible Configuration**
```yaml
s3:
  enabled: true
  # Global defaults
  default_endpoint_url: "https://s3-primary.company.local:9000"
  default_access_key_id: ""
  default_secret_access_key: ""
  
  buckets:
    - name: "spark-data-dev"
      display_name: "Spark Data (Dev)"
      quota_gb: 100
      alert_threshold: 80
      # Per-bucket overrides
      endpoint_url: "https://s3-spark-data.company.local:9000"
      access_key_id: ""  # From SPARK_DATA_DEV_ACCESS_KEY_ID env var
      secret_access_key: ""  # From SPARK_DATA_DEV_SECRET_KEY env var
```

### 3. **Environment-Specific Scaling**
- **Development**: 3 buckets with moderate quotas
- **Staging**: 5 buckets with realistic production-like quotas  
- **Production**: 7 buckets including data lake, customer data, ML models

### 4. **Intelligent Mock Mode**
- **Realistic data patterns**: Different usage patterns per bucket type
- **Volatility simulation**: Storage usage fluctuates realistically over time
- **Error scenarios**: Occasional connection/permission errors for testing
- **Status variety**: Mix of healthy, warning, and critical buckets

## 📊 Bucket Types Supported

| Bucket Type | Pattern | Typical Usage | Object Count Range |
|-------------|---------|---------------|-------------------|
| **Spark Data** | 45-75% utilization | Moderate growth | 5K - 50K objects |
| **Spark Logs** | 60-85% utilization | High volatility | 10K - 100K objects |
| **Platform Backups** | 30-60% utilization | Low volatility | 100 - 2K objects |
| **Data Lake** | 70-90% utilization | Steady growth | 50K - 500K objects |
| **ML Models** | 25-55% utilization | Moderate volatility | 500 - 5K objects |
| **Analytics Data** | 55-80% utilization | High volatility | 20K - 150K objects |
| **Customer Data** | 40-70% utilization | Steady patterns | 30K - 200K objects |
| **Shared Storage** | 35-65% utilization | High volatility | 8K - 60K objects |

## 🔧 Configuration Examples

### Single Endpoint, Multiple Buckets
```yaml
s3:
  enabled: true
  default_endpoint_url: "https://minio.company.local:9000"
  default_access_key_id: ""  # From AWS_ACCESS_KEY_ID
  default_secret_access_key: ""  # From AWS_SECRET_ACCESS_KEY
  
  buckets:
    - name: "app-data"
      display_name: "Application Data"
      quota_gb: 500
      alert_threshold: 85
      # Uses default endpoint and credentials
```

### Multiple Endpoints, Per-Bucket Credentials
```yaml
s3:
  enabled: true
  buckets:
    - name: "spark-data"
      display_name: "Spark Processing Data"
      quota_gb: 1000
      alert_threshold: 90
      endpoint_url: "https://s3-spark.company.local:9000"
      access_key_id: ""  # SPARK_DATA_ACCESS_KEY_ID
      
    - name: "backup-storage"
      display_name: "System Backups"
      quota_gb: 2000
      alert_threshold: 95
      endpoint_url: "https://s3-backup.company.local:9443"
      access_key_id: ""  # BACKUP_STORAGE_ACCESS_KEY_ID
```

## 🎭 Demo Mode Features

When demo mode is enabled, the S3 monitoring showcases:

- **Realistic utilization patterns** based on bucket types
- **Dynamic data generation** with each refresh
- **Varied bucket statuses** (healthy, warning, critical, error)
- **Comprehensive metrics** including object counts and trends
- **Error simulation** for testing alert workflows

## 🌍 Environment Variables

The system supports flexible credential management:

```bash
# Global credentials
export AWS_ACCESS_KEY_ID="your-default-key"
export AWS_SECRET_ACCESS_KEY="your-default-secret"

# Per-bucket credentials (auto-generated from bucket names)
export SPARK_DATA_DEV_ACCESS_KEY_ID="spark-specific-key"
export SPARK_DATA_DEV_SECRET_KEY="spark-specific-secret"
export BACKUP_STORAGE_ACCESS_KEY_ID="backup-specific-key"
export BACKUP_STORAGE_SECRET_KEY="backup-specific-secret"
```

## 🚀 Benefits for On-Premises Deployments

1. **Multi-System Support**: Monitor MinIO, Dell ECS, NetApp StorageGRID, and other S3-compatible storage
2. **Security Isolation**: Each bucket can use different credentials for security separation
3. **Scalable Architecture**: Easy to add new buckets and storage systems
4. **Zero AWS Dependencies**: No hardcoded regions or AWS-specific settings
5. **Comprehensive Monitoring**: Single pane of glass for all S3 storage infrastructure

## 📈 UI Features

- **Platform Storage Tiles**: Total storage, average utilization, object counts, alert status
- **Bucket Utilization Tiles**: Individual bucket metrics with color-coded status
- **Storage Utilization Chart**: Horizontal bar chart with threshold indicators
- **Detailed Metrics Table**: Comprehensive bucket information with sorting and filtering
- **Real-time Updates**: Configurable refresh with cache management

This enhanced S3 monitoring solution provides enterprise-grade visibility into your on-premises S3 infrastructure while maintaining the flexibility to work with diverse storage systems and security requirements.
