# AstroML Docker Troubleshooting Guide

## Common Issues and Solutions

### Build Issues

#### Issue: "ERROR: unsupported platforms"

**Problem**: Docker can't build for certain architectures

**Solution**:
```bash
# Check Docker buildx
docker buildx ls

# Create builder for multi-arch builds
docker buildx create --name multiarch-builder
docker buildx use multiarch-builder

# Build for specific platform
docker buildx build --platform linux/amd64 -t astroml:latest .
```

#### Issue: "Docker daemon is not running"

**Problem**: Docker service is stopped

**Solution**:
```bash
# Linux
sudo systemctl start docker

# macOS
open /Applications/Docker.app

# Windows
# Open Docker Desktop from Start menu

# Verify
docker info
```

#### Issue: "Failed to build image: context deadline exceeded"

**Problem**: Build timed out (usually due to large dependencies)

**Solution**:
```bash
# Increase timeout
docker build --build-arg BUILDKIT_CONTEXT_KEEP_GIT_DIR=1 \
  --build-arg DOCKER_BUILDKIT=1 \
  -t astroml:latest .

# Or build with no cache
docker-compose build --no-cache

# Or increase memory
docker run --memory=4g astroml:latest
```

### Container Startup Issues

#### Issue: "Container exits immediately"

**Problem**: Container crashes on startup

**Solution**:
```bash
# 1. Check logs
docker-compose logs <service>

# 2. Run with interactive terminal
docker-compose run --rm <service> /bin/bash

# 3. Check entrypoint script permissions
docker-compose exec <service> ls -la /docker-entrypoint-ingestion.sh

# 4. Make script executable in Dockerfile
# RUN chmod +x /docker-entrypoint-ingestion.sh
```

#### Issue: "Port already in use"

**Problem**: Another service is using the port

**Solution**:
```bash
# Find process using port
lsof -i :<port>
netstat -tuln | grep <port>

# Stop the process
kill -9 <PID>

# Or change port in docker-compose.yml
# ports:
#   - "9000:8000"  # Change 9000 to different port

# Verify port is free
curl http://localhost:<port>
```

#### Issue: "Cannot connect to Docker daemon"

**Problem**: Docker socket permission issue

**Solution**:
```bash
# Linux
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker ps

# Or use sudo
sudo docker-compose up -d
```

### Networking Issues

#### Issue: "Cannot reach other containers"

**Problem**: Containers can't communicate

**Solution**:
```bash
# 1. Verify network exists
docker network ls
docker network inspect astroml-network

# 2. Check container network settings
docker inspect <container> | grep -A 20 "NetworkSettings"

# 3. Test connectivity
docker-compose exec <service> ping <other_service>

# 4. Check DNS resolution
docker-compose exec <service> nslookup <service_name>

# 5. Verify service names match docker-compose.yml
docker-compose config | grep "container_name:"
```

#### Issue: "Network timeout errors"

**Problem**: Slow or unstable network

**Solution**:
```bash
# Check network interface
docker network inspect astroml-network

# Increase timeout in application
# Modify astroml configuration files

# Check Docker bridge settings
docker network inspect astroml-network --format='{{json .IPAM}}'

# Restart network
docker network rm astroml-network
docker-compose up -d  # Recreates network
```

### Database Issues

#### Issue: "PostgreSQL Connection refused"

**Problem**: Can't connect to PostgreSQL

**Solution**:
```bash
# 1. Check if PostgreSQL is running
docker-compose ps postgres

# 2. Check logs
docker-compose logs postgres

# 3. Verify connection string
echo $DATABASE_URL

# 4. Test connection manually
docker-compose exec postgres psql -U astroml -d astroml -c "SELECT 1"

# 5. Check listening ports
docker-compose exec postgres netstat -tuln | grep 5432

# 6. Verify credentials
# Check .env file matches docker-compose.yml
grep POSTGRES .env
```

#### Issue: "Database is locked"

**Problem**: Concurrent access or incomplete transaction

**Solution**:
```bash
# 1. Check locks
docker-compose exec postgres psql -U astroml -d astroml \
  -c "SELECT pid, usename, pg_blocking_pids(pid) as blocked_by, query FROM pg_stat_activity WHERE cardinality(pg_blocking_pids(pid)) > 0;"

# 2. Terminate blocking query
docker-compose exec postgres psql -U astroml -d astroml \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid != pg_backend_pid() AND duration > interval '1 hour';"

# 3. Restart PostgreSQL
docker-compose restart postgres
```

#### Issue: "Disk full - PostgreSQL won't start"

**Problem**: Not enough disk space

**Solution**:
```bash
# Check disk usage
du -sh /var/lib/docker/volumes/astroml_postgres_data/_data

# Clean up old data
docker-compose exec postgres psql -U astroml -d astroml \
  -c "VACUUM FULL;"

# Expand volume (if using separate storage)
# Or clean Docker system
docker system prune -a --volumes

# Check available space
df -h
```

### Redis Issues

#### Issue: "Redis Connection refused"

**Problem**: Can't connect to Redis

**Solution**:
```bash
# 1. Check if Redis is running
docker-compose ps redis

# 2. Test connection
docker-compose exec redis redis-cli ping

# 3. Check logs
docker-compose logs redis

# 4. Verify port binding
docker-compose exec redis netstat -tuln | grep 6379

# 5. Check password
docker-compose exec redis redis-cli -a $REDIS_PASSWORD ping
```

#### Issue: "Redis memory limit exceeded"

**Problem**: Redis is using too much memory

**Solution**:
```bash
# 1. Check memory usage
docker-compose exec redis redis-cli INFO memory

# 2. Clear cache
docker-compose exec redis redis-cli FLUSHDB

# 3. Adjust eviction policy in docker-compose.yml
# command: redis-server --appendonly yes --maxmemory 1gb --maxmemory-policy allkeys-lru

# 4. Restart Redis
docker-compose restart redis
```

### Volume Issues

#### Issue: "Permission denied when mounting volume"

**Problem**: Volume ownership mismatch

**Solution**:
```bash
# 1. Check volume permissions
ls -la /var/lib/docker/volumes/astroml_postgres_data/_data

# 2. Fix permissions
sudo chown -R 999:999 /var/lib/docker/volumes/astroml_postgres_data/_data

# 3. Or in Dockerfile
# RUN chown -R astroml:astroml /app

# 4. Check container user
docker-compose exec <service> whoami
docker-compose exec <service> id
```

#### Issue: "Volume not persisting data"

**Problem**: Data lost after container stops

**Solution**:
```bash
# 1. Verify volume exists
docker volume ls | grep astroml

# 2. Check volume mount in docker-compose.yml
docker-compose config | grep -A 5 "volumes:"

# 3. Verify volume type
docker volume inspect astroml_postgres_data

# 4. Use named volumes (not tmpfs)
# volumes:
#   postgres_data:
#     driver: local

# 5. Restart container without -v flag
docker-compose down  # DON'T use -v
docker-compose up -d
```

### Performance Issues

#### Issue: "High CPU usage"

**Problem**: Services consuming too much CPU

**Solution**:
```bash
# 1. Monitor resource usage
docker stats

# 2. Check which process is consuming CPU
docker-compose exec <service> top

# 3. Limit CPU in docker-compose.yml
# deploy:
#   resources:
#     limits:
#       cpus: '2'

# 4. Optimize application code
# Profile with py-spy or cProfile
```

#### Issue: "High memory usage"

**Problem**: Services consuming too much memory

**Solution**:
```bash
# 1. Check memory usage
docker stats
free -h

# 2. Limit memory in docker-compose.yml
# deploy:
#   resources:
#     limits:
#       memory: 2G

# 3. Enable memory swapping carefully
# deploy:
#   resources:
#     limits:
#       memswap_limit: 4G

# 4. Monitor garbage collection
docker-compose exec <service> ps aux
```

#### Issue: "Slow query performance"

**Problem**: Database queries are slow

**Solution**:
```bash
# 1. Enable query logging
docker-compose exec postgres psql -U astroml -d astroml \
  -c "ALTER DATABASE astroml SET log_min_duration_statement = 1000;"

# 2. Analyze query plan
EXPLAIN ANALYZE SELECT ...;

# 3. Create indexes
CREATE INDEX idx_name ON table_name(column);

# 4. Check statistics
ANALYZE;

# 5. Monitor active queries
docker-compose exec postgres psql -U astroml -d astroml \
  -c "SELECT pid, usename, state, query FROM pg_stat_activity;"
```

### Logging Issues

#### Issue: "Logs are too large / Disk filling up"

**Problem**: Docker logs consuming disk space

**Solution**:
```bash
# 1. Check log size
du -sh /var/lib/docker/containers/*/

# 2. Configure log rotation in docker-compose.yml
# logging:
#   driver: json-file
#   options:
#     max-size: "10m"
#     max-file: "5"

# 3. Clean old logs
docker system prune

# 4. View logs efficiently
docker-compose logs --tail 100 -f
```

#### Issue: "Can't view logs"

**Problem**: Logs not accessible

**Solution**:
```bash
# 1. Check log driver
docker inspect <container> | grep LogDriver

# 2. View logs directly
docker-compose logs <service>

# 3. Stream logs
docker-compose logs -f

# 4. View specific container logs
cat /var/lib/docker/containers/<container_id>/<container_id>-json.log

# 5. Export logs
docker-compose logs > logs.txt
```

### Monitoring Issues

#### Issue: "Prometheus not scraping metrics"

**Problem**: No metrics data in Prometheus

**Solution**:
```bash
# 1. Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# 2. Verify service endpoints are running
curl http://localhost:8080/metrics

# 3. Check prometheus.yml configuration
docker-compose exec prometheus cat /etc/prometheus/prometheus.yml

# 4. Restart Prometheus
docker-compose restart prometheus

# 5. Check service connectivity
docker-compose exec prometheus curl http://ingestion:8080/metrics
```

#### Issue: "Grafana dashboards not loading"

**Problem**: Dashboards show no data

**Solution**:
```bash
# 1. Verify datasource connectivity
# Grafana UI -> Configuration -> Data Sources -> Test

# 2. Check Prometheus is accessible
curl http://prometheus:9090

# 3. Verify dashboard JSON
docker-compose exec grafana cat /etc/grafana/provisioning/dashboards/<dashboard>.json

# 4. Check Grafana logs
docker-compose logs grafana

# 5. Restart Grafana
docker-compose restart grafana
```

## Debugging Techniques

### Interactive Debugging

```bash
# Start container interactively
docker-compose run --rm <service> /bin/bash

# Execute command in running container
docker-compose exec <service> /bin/bash

# Debug a service with additional tools
docker-compose run --rm <service> bash -c "apt-get update && apt-get install -y curl && curl ..."
```

### Environment Variable Debugging

```bash
# Print all environment variables
docker-compose exec <service> env | sort

# Check specific variable
docker-compose exec <service> echo $DATABASE_URL

# Debug entrypoint
docker-compose run --rm <service> /bin/bash -x /docker-entrypoint-ingestion.sh
```

### Network Debugging

```bash
# Install network tools
docker-compose exec <service> apt-get install -y net-tools iproute2 curl

# Test connectivity
docker-compose exec <service> curl -v http://other-service:8000

# Check DNS
docker-compose exec <service> nslookup postgres
docker-compose exec <service> getent hosts postgres

# Trace network
docker-compose exec <service> traceroute postgres
```

### File System Debugging

```bash
# List files in container
docker-compose exec <service> ls -la /app

# Check file permissions
docker-compose exec <service> stat /app/astroml

# Copy files from container
docker-compose cp <service>:/app/logs/error.log ./error.log

# Copy files to container
docker-compose cp ./config.yaml <service>:/app/config.yaml
```

## Getting Help

### Useful Commands for Diagnosis

```bash
# Complete environment diagnosis
docker-compose ps
docker-compose config
docker-compose logs --tail 50
docker stats
df -h

# Save diagnostic info
mkdir -p /tmp/astroml-diagnosis
docker-compose ps > /tmp/astroml-diagnosis/services.txt
docker-compose logs > /tmp/astroml-diagnosis/logs.txt
docker stats --no-stream > /tmp/astroml-diagnosis/stats.txt
```

### Support Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [AstroML GitHub Issues](https://github.com/stellar/astroml/issues)
- Docker Community Forums
