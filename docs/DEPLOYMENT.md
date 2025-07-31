# Production Deployment Guide

This guide provides step-by-step instructions for deploying the E-commerce Analytics Pipeline to production environments.

## Prerequisites

### System Requirements

- **CPU**: Minimum 8 cores, recommended 16+ cores
- **RAM**: Minimum 16GB, recommended 32GB+
- **Storage**: Minimum 100GB SSD, recommended 500GB+ NVMe
- **Network**: High-speed internet connection for data ingestion
- **OS**: Ubuntu 20.04+ or CentOS 8+

### Software Requirements

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+
- Git

## Environment Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd "Project GOAT"
```

### 2. Environment Configuration

Create a `.env` file with production settings:

```bash
# Database Configuration
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_USER=analytics_user
POSTGRES_DB=ecommerce_analytics

# Redis Configuration
REDIS_PASSWORD=your_redis_password_here

# Airflow Configuration
AIRFLOW_FERNET_KEY=your_fernet_key_here
AIRFLOW_SECRET_KEY=your_secret_key_here

# Grafana Configuration
GRAFANA_PASSWORD=your_grafana_password_here

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka-1:29092,kafka-2:29092,kafka-3:29092

# Monitoring Configuration
PROMETHEUS_RETENTION_DAYS=30
```

### 3. Generate Security Keys

```bash
# Generate Fernet key for Airflow
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate secret key for Airflow
python -c "import secrets; print(secrets.token_hex(32))"
```

## Production Deployment

### 1. Infrastructure Setup

```bash
# Start production services
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be ready
docker-compose -f docker-compose.prod.yml ps
```

### 2. Database Initialization

```bash
# Initialize database schema
python src/utils/setup_database.py

# Verify database setup
python -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost', port=5432, 
    database='ecommerce_analytics',
    user='analytics_user', 
    password='your_secure_password_here'
)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = \'public\'')
print(f'Tables created: {cur.fetchone()[0]}')
conn.close()
"
```

### 3. Kafka Topic Creation

```bash
# Create required Kafka topics
docker exec -it kafka-1 kafka-topics --create \
    --bootstrap-server kafka-1:29092 \
    --topic ecommerce-events \
    --partitions 6 \
    --replication-factor 3

docker exec -it kafka-1 kafka-topics --create \
    --bootstrap-server kafka-1:29092 \
    --topic processed-events \
    --partitions 3 \
    --replication-factor 3

docker exec -it kafka-1 kafka-topics --create \
    --bootstrap-server kafka-1:29092 \
    --topic daily-aggregations \
    --partitions 1 \
    --replication-factor 3

# Verify topics
docker exec -it kafka-1 kafka-topics --list --bootstrap-server kafka-1:29092
```

### 4. Application Deployment

```bash
# Install Python dependencies
pip install -r requirements-minimal.txt

# Start the streaming job
python src/spark_jobs/streaming_job.py --mode streaming &

# Start the dashboard
python src/dashboard/realtime_dashboard.py --port 5000 &

# Start the event simulator (for testing)
python src/event_simulator/main.py --events-per-second 50 --duration 60 &
```

### 5. Monitoring Setup

```bash
# Verify Prometheus is collecting metrics
curl http://localhost:9090/api/v1/targets

# Verify Grafana is accessible
curl http://localhost:3000/api/health

# Import Grafana dashboards
# Navigate to http://localhost:3000 and import the provided dashboards
```

## Configuration Management

### 1. Application Configuration

Update configuration files for production:

```yaml
# config/kafka-config.yml
kafka:
  bootstrap_servers: kafka-1:29092,kafka-2:29092,kafka-3:29092
  topics:
    ecommerce_events: ecommerce-events
    processed_events: processed-events
    daily_aggregations: daily-aggregations
  producer_config:
    acks: all
    retries: 5
    batch_size: 32768
    linger_ms: 10
    buffer_memory: 67108864
  consumer_config:
    auto_offset_reset: earliest
    enable_auto_commit: true
    auto_commit_interval_ms: 5000
    session_timeout_ms: 30000
    heartbeat_interval_ms: 3000
```

### 2. Database Configuration

```yaml
# config/database-config.yml
database:
  host: postgres
  port: 5432
  database: ecommerce_analytics
  user: analytics_user
  password: ${POSTGRES_PASSWORD}
  pool_size: 20
  max_overflow: 30
  pool_timeout: 30
  pool_recycle: 3600
```

### 3. Monitoring Configuration

```yaml
# config/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'streaming-job'
    static_configs:
      - targets: ['localhost:8000']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'kafka'
    static_configs:
      - targets: ['kafka-exporter:9308']
```

## Security Configuration

### 1. Network Security

```bash
# Configure firewall rules
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8080/tcp  # Airflow
sudo ufw allow 9000/tcp  # Kafka UI
sudo ufw allow 3000/tcp  # Grafana
sudo ufw allow 9090/tcp  # Prometheus
sudo ufw enable
```

### 2. SSL/TLS Configuration

```bash
# Generate SSL certificates
mkdir -p config/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout config/nginx/ssl/nginx.key \
    -out config/nginx/ssl/nginx.crt
```

### 3. Authentication Setup

```bash
# Create Airflow admin user
docker exec -it airflow-webserver airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password your_secure_password
```

## Monitoring and Alerting

### 1. Health Checks

```bash
# Create health check script
cat > health_check.sh << 'EOF'
#!/bin/bash

# Check database connectivity
python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost', port=5432,
        database='ecommerce_analytics',
        user='analytics_user',
        password='${POSTGRES_PASSWORD}'
    )
    print('Database: OK')
    conn.close()
except Exception as e:
    print(f'Database: ERROR - {e}')
    exit(1)
"

# Check Kafka connectivity
python -c "
from kafka import KafkaProducer
try:
    producer = KafkaProducer(bootstrap_servers='localhost:9092')
    producer.close()
    print('Kafka: OK')
except Exception as e:
    print(f'Kafka: ERROR - {e}')
    exit(1)
"

# Check Airflow
curl -f http://localhost:8080/health || exit(1)
echo "Airflow: OK"

# Check Grafana
curl -f http://localhost:3000/api/health || exit(1)
echo "Grafana: OK"
EOF

chmod +x health_check.sh
```

### 2. Alerting Rules

```yaml
# config/prometheus/alert_rules.yml
groups:
  - name: ecommerce_analytics
    rules:
      - alert: HighErrorRate
        expr: rate(events_failed_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in event processing"
          description: "Error rate is {{ $value }} errors per second"

      - alert: LowThroughput
        expr: rate(events_processed_total[5m]) < 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low event processing throughput"
          description: "Processing rate is {{ $value }} events per second"

      - alert: DatabaseConnectionFailed
        expr: pg_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failed"
          description: "PostgreSQL is not responding"
```

## Backup and Recovery

### 1. Database Backup

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker exec postgres pg_dump -U analytics_user ecommerce_analytics > $BACKUP_DIR/db_backup_$DATE.sql

# Backup configuration files
tar -czf $BACKUP_DIR/config_backup_$DATE.tar.gz config/

# Clean up old backups (keep last 7 days)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x backup.sh

# Add to crontab for daily backups
echo "0 2 * * * /path/to/backup.sh" | crontab -
```

### 2. Recovery Procedures

```bash
# Database recovery
docker exec -i postgres psql -U analytics_user ecommerce_analytics < backup_file.sql

# Configuration recovery
tar -xzf config_backup.tar.gz
```

## Scaling and Performance

### 1. Horizontal Scaling

```bash
# Scale Kafka consumers
docker-compose -f docker-compose.prod.yml up -d --scale airflow-worker=4

# Scale streaming jobs
# Run multiple instances of the streaming job
python src/spark_jobs/streaming_job.py --mode streaming --instance-id 1 &
python src/spark_jobs/streaming_job.py --mode streaming --instance-id 2 &
```

### 2. Performance Tuning

```bash
# PostgreSQL performance tuning
docker exec -it postgres psql -U analytics_user -d ecommerce_analytics -c "
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
SELECT pg_reload_conf();
"
```

## Troubleshooting

### Common Issues

1. **Kafka Connection Issues**
   ```bash
   # Check Kafka cluster health
   docker exec -it kafka-1 kafka-broker-api-versions --bootstrap-server kafka-1:29092
   ```

2. **Database Connection Issues**
   ```bash
   # Check PostgreSQL logs
   docker logs postgres
   
   # Test connection
   docker exec -it postgres psql -U analytics_user -d ecommerce_analytics -c "SELECT 1;"
   ```

3. **Airflow Issues**
   ```bash
   # Check Airflow logs
   docker logs airflow-webserver
   docker logs airflow-scheduler
   
   # Restart Airflow services
   docker-compose -f docker-compose.prod.yml restart airflow-webserver airflow-scheduler
   ```

### Log Analysis

```bash
# View all logs
docker-compose -f docker-compose.prod.yml logs -f

# View specific service logs
docker-compose -f docker-compose.prod.yml logs -f streaming-job

# Search for errors
docker-compose -f docker-compose.prod.yml logs | grep -i error
```

## Maintenance

### 1. Regular Maintenance Tasks

```bash
# Weekly maintenance script
cat > maintenance.sh << 'EOF'
#!/bin/bash

# Vacuum database
docker exec postgres psql -U analytics_user -d ecommerce_analytics -c "VACUUM ANALYZE;"

# Clean up old logs
find logs/ -name "*.log" -mtime +30 -delete

# Restart services for updates
docker-compose -f docker-compose.prod.yml restart

# Run health checks
./health_check.sh
EOF

chmod +x maintenance.sh
```

### 2. Updates and Upgrades

```bash
# Update application code
git pull origin main

# Update dependencies
pip install -r requirements-minimal.txt --upgrade

# Rebuild and restart services
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

## Support and Monitoring

### 1. Monitoring Dashboard

Access monitoring tools:
- **Grafana**: http://your-domain:3000 (admin/admin)
- **Prometheus**: http://your-domain:9090
- **Kafka UI**: http://your-domain:9000
- **Airflow**: http://your-domain:8080

### 2. Alerting

Configure alert notifications:
- Email alerts for critical issues
- Slack/Teams integration for team notifications
- PagerDuty integration for on-call alerts

### 3. Support Contacts

- **Technical Support**: tech-support@company.com
- **Emergency Contact**: +1-555-0123
- **Documentation**: https://docs.company.com/analytics-pipeline 