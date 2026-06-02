# Docker Quick Reference Guide

Quick commands and tips for using AstroML with Docker.

## Quick Start

```bash
# 1. Start everything
./scripts/docker-start.sh all

# 2. Check status
./scripts/docker-start.sh status

# 3. View logs
./scripts/docker-start.sh logs

# 4. Check health
./scripts/docker-health-check.sh

# 5. Stop services
./scripts/docker-start.sh stop
```

## Common Tasks

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f ingestion

# Last 100 lines
docker-compose logs --tail 100

# With timestamps
docker-compose logs --timestamps
```

### Execute Commands
```bash
# Run in service
docker-compose exec postgres psql -U astroml -d astroml

# Run in interactive shell
docker-compose exec ingestion /bin/bash

# Run one-off command
docker-compose run --rm ingestion python -c "import astroml; print(astroml.__version__)"
```

### Rebuild Images
```bash
# Rebuild all
docker-compose build --no-cache

# Rebuild specific service
docker-compose build --no-cache ingestion

# Build and restart
docker-compose up -d --build ingestion
```

### Database Access
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U astroml -d astroml

# Backup database
docker-compose exec postgres pg_dump -U astroml astroml | gzip > backup.sql.gz

# Restore database
zcat backup.sql.gz | docker-compose exec -T postgres psql -U astroml astroml
```

### View Resources
```bash
# Real-time resource usage
docker stats

# Service details
docker-compose ps -a

# Container information
docker inspect astroml-postgres

# Network details
docker network inspect astroml-network
```

### Clean Up
```bash
# Stop services
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove everything including volumes
docker-compose down -v

# Remove unused images/volumes
docker system prune -a --volumes
```

## Service URLs

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| API | http://localhost:8000 | - |
| Ingestion | http://localhost:8000 | - |
| Streaming | http://localhost:8001 | - |
| Jupyter | http://localhost:8888 | - |
| TensorBoard (CPU) | http://localhost:6007 | - |
| TensorBoard (GPU) | http://localhost:6006 | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin/admin |
| PostgreSQL | localhost:5432 | astroml/astroml_password |
| Redis | localhost:6379 | (no password) |

## Environment Variables

Key environment variables for configuration:

```bash
# Database
DATABASE_URL=postgresql://astroml:password@postgres:5432/astroml
REDIS_URL=redis://redis:6379/0

# Application
LOG_LEVEL=INFO
DEBUG=False
APP_ENV=development

# Training
TRAINING_BATCH_SIZE=32
CUDA_VISIBLE_DEVICES=0
```

See [docker-env-guide.md](./docker-env-guide.md) for full reference.

## Docker Compose Profiles

Use profiles to run subsets of services:

```bash
# Development
docker-compose --profile dev up -d

# Training (CPU)
docker-compose --profile cpu up -d

# Training (GPU)
docker-compose --profile gpu up -d

# Monitoring
docker-compose --profile monitoring up -d

# Soroban
docker-compose --profile soroban up -d

# Multiple profiles
docker-compose --profile dev --profile monitoring up -d
```

## Useful Docker Commands

```bash
# List images
docker images

# Search local images
docker images | grep astroml

# Remove image
docker rmi astroml:latest

# Login to registry
docker login

# Push image
docker push registry.example.com/astroml:latest

# Pull image
docker pull registry.example.com/astroml:latest

# Save image to file
docker save astroml:latest | gzip > astroml.tar.gz

# Load image from file
gunzip -c astroml.tar.gz | docker load
```

## Troubleshooting Cheat Sheet

```bash
# Check if Docker is running
docker info

# View system resources
docker system df

# Restart Docker daemon
sudo systemctl restart docker

# Reset Docker state (destructive!)
docker system prune -a --volumes

# Debug network
docker network inspect astroml-network
docker exec astroml-ingestion ping postgres

# Check disk usage
du -sh /var/lib/docker/

# Monitor in real-time
docker stats --no-stream

# Extract logs to file
docker-compose logs > all-logs.txt

# Check Docker events in real-time
docker events

# Prune stopped containers
docker container prune

# Prune dangling images
docker image prune

# Prune unused volumes
docker volume prune
```

## Performance Tips

1. **Use .dockerignore** - Exclude unnecessary files from builds
2. **Multi-stage builds** - Reduce final image size
3. **Named volumes** - Better performance than bind mounts for databases
4. **Resource limits** - Prevent one service from consuming all resources
5. **Image caching** - Order Dockerfile commands by change frequency
6. **Local volume caching** - Speed up builds
7. **Network optimization** - Use host network mode carefully

## Security Tips

1. **Don't run as root** - Use USER astroml in Dockerfile
2. **Secrets management** - Use Docker secrets or environment variables
3. **Read-only filesystems** - Run containers with read-only root when possible
4. **Network isolation** - Use custom networks instead of default bridge
5. **Image scanning** - Scan images for vulnerabilities
6. **Registry authentication** - Use authentication for private registries
7. **Update base images** - Keep base images current

## Advanced Topics

### Building for Multiple Architectures
```bash
docker buildx build --platform linux/amd64,linux/arm64 -t astroml:latest .
```

### Using BuildKit Cache
```bash
docker build --build-arg BUILDKIT_INLINE_CACHE=1 -t astroml:latest .
```

### Docker Compose Extension
```bash
# Use extension file for overrides
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Health Checks
Services include health checks. Monitor with:
```bash
docker-compose exec <service> healthcheck-command
```

## For More Information

- [Full Docker Setup Guide](./docs/DOCKER_SETUP.md)
- [Environment Configuration](./docker-env-guide.md)
- [Production Deployment](./DOCKER_PRODUCTION_DEPLOYMENT.md)
- [Troubleshooting Guide](./DOCKER_TROUBLESHOOTING.md)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
