# AstroML Docker Production Deployment Guide

## Pre-Deployment Checklist

### Security
- [ ] Generate strong passwords for all services
- [ ] Update `.env` with production values
- [ ] Configure HTTPS/TLS certificates
- [ ] Set up firewall rules
- [ ] Enable database backups
- [ ] Configure logging aggregation
- [ ] Review and update CORS settings
- [ ] Configure rate limiting

### Infrastructure
- [ ] Provision Docker host (minimum 8GB RAM, 4 CPU cores)
- [ ] Allocate storage volumes (recommendation: 100GB+)
- [ ] Configure network policies
- [ ] Set up monitoring and alerting
- [ ] Plan backup and disaster recovery
- [ ] Configure log rotation

### Application
- [ ] Build and test application images
- [ ] Load performance tests
- [ ] Update configuration files
- [ ] Configure environment variables
- [ ] Test database migrations
- [ ] Verify all dependencies

## Step 1: Prepare the Environment

```bash
# 1. Create production environment file
cp .env.example .env.prod

# 2. Edit with production values
nano .env.prod

# 3. Generate strong passwords
openssl rand -base64 32 | xargs echo "POSTGRES_PASSWORD=" >> .env.prod
openssl rand -base64 32 | xargs echo "REDIS_PASSWORD=" >> .env.prod

# 4. Set permissions
chmod 600 .env.prod
```

## Step 2: Prepare Docker Host

```bash
# 1. Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 2. Configure Docker daemon for production
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "debug": false,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "5"
  },
  "live-restore": true,
  "userland-proxy": false
}
EOF

# 3. Restart Docker
sudo systemctl restart docker

# 4. Create persistent volumes
docker volume create postgres_data
docker volume create redis_data
docker volume create prometheus_data
docker volume create grafana_data
```

## Step 3: Build and Push Images

```bash
# 1. Build production images
docker-compose build --no-cache

# 2. Tag images for registry
docker tag astroml:ingestion your-registry/astroml:ingestion-latest
docker tag astroml:production your-registry/astroml:production-latest
docker tag astroml:training your-registry/astroml:training-latest

# 3. Push to registry
docker push your-registry/astroml:ingestion-latest
docker push your-registry/astroml:production-latest
docker push your-registry/astroml:training-latest
```

## Step 4: Deploy Services

```bash
# 1. Pull latest images
docker-compose pull

# 2. Start core services
docker-compose --env-file .env.prod up -d postgres redis

# 3. Wait for database to be ready
sleep 30

# 4. Run migrations
docker-compose --env-file .env.prod exec postgres \
  psql -U astroml -d astroml -f /docker-entrypoint-initdb.d/migrations.sql

# 5. Start application services
docker-compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d

# 6. Enable monitoring
docker-compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml \
  --profile monitoring up -d
```

## Step 5: Verify Deployment

```bash
# 1. Check service status
docker-compose ps

# 2. Run health checks
./scripts/docker-health-check.sh

# 3. View logs
docker-compose logs -f

# 4. Test application
curl -X GET http://localhost:8000/health
curl -X GET http://localhost:3000/  # Grafana

# 5. Monitor metrics
# Access Prometheus: http://localhost:9090
# Access Grafana: http://localhost:3000
```

## Step 6: Backup Configuration

```bash
# 1. Create backup directory
mkdir -p /backups/astroml/$(date +%Y%m%d)

# 2. Backup PostgreSQL
docker-compose exec postgres pg_dump \
  -U astroml -d astroml > /backups/astroml/$(date +%Y%m%d)/postgres.sql

# 3. Backup Redis
docker-compose exec redis redis-cli BGSAVE

# 4. Copy backup to host
docker cp astroml-redis:/data/dump.rdb /backups/astroml/$(date +%Y%m%d)/

# 5. Backup configuration
cp .env.prod /backups/astroml/$(date +%Y%m%d)/
cp docker-compose.yml /backups/astroml/$(date +%Y%m%d)/
cp docker-compose.prod.yml /backups/astroml/$(date +%Y%m%d)/
```

## Maintenance Operations

### Database Maintenance

```bash
# Backup database daily
docker-compose exec postgres pg_dump -U astroml -d astroml | gzip > backup-$(date +%Y%m%d).sql.gz

# Vacuum and analyze
docker-compose exec postgres psql -U astroml -d astroml -c "VACUUM ANALYZE;"

# Check database size
docker-compose exec postgres psql -U astroml -d astroml -c "SELECT pg_size_pretty(pg_database_size('astroml'));"
```

### Monitoring and Logging

```bash
# View service logs with rotation
docker-compose logs -f --tail 100

# Export metrics
curl http://localhost:9090/api/v1/query?query=up > metrics.json

# Generate Grafana dashboard snapshot
# Via Grafana UI: Dashboard -> Share -> Snapshot
```

### Updates and Upgrades

```bash
# 1. Pull latest images
docker-compose pull

# 2. Rebuild images with new source
docker-compose build --no-cache

# 3. Stop services gracefully
docker-compose stop

# 4. Backup data
./scripts/backup.sh

# 5. Start updated services
docker-compose up -d

# 6. Verify deployment
./scripts/docker-health-check.sh
```

### Disaster Recovery

```bash
# 1. Restore from backup
docker-compose down -v
docker volume create postgres_data
docker volume create redis_data

# 2. Restore PostgreSQL
cat /backups/astroml/20240101/postgres.sql | \
  docker-compose exec -T postgres psql -U astroml -d astroml

# 3. Restore Redis
docker cp /backups/astroml/20240101/dump.rdb astroml-redis:/data/
docker-compose restart redis

# 4. Start services
docker-compose up -d

# 5. Verify restore
./scripts/docker-health-check.sh
```

## Performance Tuning

### Database Optimization

```sql
-- Connection pooling
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '2GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';

-- Restart PostgreSQL for changes to take effect
```

### Redis Optimization

```bash
# Monitor Redis memory usage
docker-compose exec redis redis-cli INFO memory

# Adjust memory policy in docker-compose.yml:
# command: redis-server --appendonly yes --maxmemory 1gb --maxmemory-policy allkeys-lru
```

### Container Resources

```bash
# Monitor resource usage
docker stats

# Adjust limits in docker-compose.prod.yml as needed
```

## Troubleshooting

### Services Won't Start

```bash
# 1. Check logs
docker-compose logs <service>

# 2. Verify configuration
docker-compose config | grep <service> -A 20

# 3. Check port conflicts
netstat -tuln | grep -E "(5432|6379|8000|9090|3000)"

# 4. Verify network
docker network ls
docker network inspect astroml-network
```

### Database Connection Issues

```bash
# 1. Check PostgreSQL status
docker-compose ps postgres

# 2. Test connection
docker-compose exec postgres psql -U astroml -d astroml -c "SELECT 1"

# 3. Check connection string
echo $DATABASE_URL

# 4. Review PostgreSQL logs
docker-compose logs postgres | tail -50
```

### Performance Issues

```bash
# 1. Monitor resource usage
docker stats

# 2. Check database query performance
docker-compose exec postgres psql -U astroml -d astroml \
  -c "SELECT query, calls, total_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# 3. Review slow query logs
docker-compose logs postgres | grep "slow query"

# 4. Analyze Prometheus metrics
# Visit http://localhost:9090 and query specific metrics
```

### Disk Space Issues

```bash
# 1. Check volume usage
docker volume ls
docker system df

# 2. Prune unused data
docker system prune -a -f

# 3. Clean up logs
docker-compose logs --no-log-prefix <service> > /dev/null

# 4. Check database size
docker-compose exec postgres psql -U astroml -d astroml \
  -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 20;"
```

## Monitoring and Alerting

### Prometheus Queries

```promql
# CPU usage
rate(container_cpu_usage_seconds_total[5m]) * 100

# Memory usage
container_memory_usage_bytes / 1024 / 1024

# Database connections
sum(pg_stat_activity_count)

# Redis memory
redis_memory_used_bytes / 1024 / 1024
```

### Grafana Dashboards

Import pre-built dashboards:
- PostgreSQL: https://grafana.com/grafana/dashboards/9628
- Redis: https://grafana.com/grafana/dashboards/763
- Docker: https://grafana.com/grafana/dashboards/1860

## Support and Maintenance

### Documentation
- [Docker Setup Guide](./DOCKER_SETUP.md)
- [Environment Configuration](./docker-env-guide.md)
- [Main README](./README.md)

### Useful Commands

```bash
# View all services
docker-compose ps

# Execute command in service
docker-compose exec <service> <command>

# Rebuild specific service
docker-compose build --no-cache <service>

# Scale service
docker-compose up -d --scale <service>=3

# View resource limits
docker inspect <container> | grep -A 10 "HostConfig"
```

## Rollback Procedures

```bash
# 1. Stop current services
docker-compose down

# 2. Restore previous backup
cat /backups/astroml/previous-date/postgres.sql | \
  docker-compose exec -T postgres psql -U astroml

# 3. Restore previous image versions
docker pull your-registry/astroml:previous-version
docker tag your-registry/astroml:previous-version your-registry/astroml:latest

# 4. Start with previous version
docker-compose up -d

# 5. Verify
./scripts/docker-health-check.sh
```
