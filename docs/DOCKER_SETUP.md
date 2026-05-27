# Docker Setup Guide for AstroML

## Overview

This guide provides comprehensive instructions for setting up and running AstroML using Docker containers. The AstroML project includes multiple Docker configurations for different use cases including data ingestion, machine learning training, smart contract development, and production deployment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Docker Services](#docker-services)
4. [Docker Stages](#docker-stages)
5. [Environment Configuration](#environment-configuration)
6. [Common Operations](#common-operations)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Usage](#advanced-usage)

## Prerequisites

### Required Software

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **NVIDIA Docker** (for GPU support): If using GPU training

### Installation

#### Docker Installation

**Linux:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**macOS:**
```bash
brew install --cask docker
```

**Windows:**
Download Docker Desktop from https://www.docker.com/products/docker-desktop

#### NVIDIA Docker (GPU Support)

```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

## Quick Start

### Start Core Services

```bash
# Start PostgreSQL and Redis
docker-compose up postgres redis -d

# Start ingestion service
docker-compose up ingestion -d

# Verify services are running
docker-compose ps
```

### Start Development Environment

```bash
# Start development environment with Jupyter
docker-compose --profile dev up -d

# Access Jupyter Lab
# Open browser to http://localhost:8888
```

### Start Training

```bash
# CPU training
docker-compose --profile cpu up training-cpu

# GPU training (requires NVIDIA Docker)
docker-compose --profile gpu up training-gpu
```

### Start Soroban Development

```bash
# Start Soroban contract development
docker-compose --profile soroban up soroban-dev -d

# Build Soroban contracts
docker-compose --profile soroban-build up soroban-build

# Test Soroban contracts
docker-compose --profile soroban-test up soroban-test
```

## Docker Services

### Core Infrastructure

#### PostgreSQL Database
- **Service Name**: `postgres`
- **Image**: `postgres:15-alpine`
- **Port**: `5432`
- **Environment Variables**:
  - `POSTGRES_DB`: astroml
  - `POSTGRES_USER`: astroml
  - `POSTGRES_PASSWORD`: astroml_password
- **Volumes**: `postgres_data`

#### Redis Cache
- **Service Name**: `redis`
- **Image**: `redis:7-alpine`
- **Port**: `6379`
- **Volumes**: `redis_data`
- **Features**: AOF persistence enabled

### Application Services

#### Ingestion Service
- **Service Name**: `ingestion`
- **Port**: `8000` (HTTP), `8080` (Health)
- **Environment Variables**:
  - `DATABASE_URL`: PostgreSQL connection string
  - `REDIS_URL`: Redis connection string
  - `LOG_LEVEL`: INFO
- **Volumes**: `ingestion_logs`, `ingestion_data`

#### Streaming Service
- **Service Name**: `streaming`
- **Port**: `8001`
- **Purpose**: Enhanced streaming for Stellar data
- **Volumes**: `streaming_logs`

#### Training Services
- **CPU Training**: `training-cpu` (Port: 6007)
- **GPU Training**: `training-gpu` (Port: 6006)
- **Profiles**: `cpu`, `gpu`
- **Volumes**: `training_models`, `training_data`, `training_logs`

#### Development Environment
- **Service Name**: `dev`
- **Ports**: `8002` (API), `8888` (Jupyter), `6008` (TensorBoard)
- **Profile**: `dev`
- **Features**: Live code editing, testing, Jupyter Lab

#### Production Service
- **Service Name**: `production`
- **Port**: `8000`
- **Profile**: `prod`
- **Features**: Minimal image, optimized for production

### Soroban Services

#### Soroban Development
- **Service Name**: `soroban-dev`
- **Port**: `8000`
- **Profile**: `soroban`
- **Features**: Live contract development with cargo-watch

#### Soroban Build
- **Service Name**: `soroban-build`
- **Profile**: `soroban-build`
- **Purpose**: Build contracts in release mode

#### Soroban Testing
- **Service Name**: `soroban-test`
- **Profile**: `soroban-test`
- **Purpose**: Run contract tests

### Monitoring Services

#### Prometheus
- **Service Name**: `prometheus`
- **Port**: `9090`
- **Profile**: `monitoring`
- **Purpose**: Metrics collection

#### Grafana
- **Service Name**: `grafana`
- **Port**: `3000`
- **Profile**: `monitoring`
- **Purpose**: Metrics visualization
- **Default Credentials**: admin / admin

## Docker Stages

### Main Dockerfile Stages

#### Base Stage
- **Purpose**: Common dependencies and Python environment
- **Python Version**: 3.11-slim
- **System Dependencies**: build-essential, curl, git, postgresql-client
- **User**: astroml (non-root)

#### Ingestion Stage
- **Purpose**: Data ingestion and streaming
- **Additional Tools**: jq, netcat-openbsd
- **Health Check**: Python module import check
- **Default Command**: `python -m astroml.ingestion`

#### Training Base Stage
- **Purpose**: ML training with GPU support
- **Base Image**: nvidia/cuda:12.1-runtime-base-ubuntu22.04
- **Python**: 3.11
- **PyTorch**: CUDA 12.1 support
- **PyTorch Geometric**: CUDA 12.1 support

#### Training CPU Stage
- **Purpose**: CPU-only training
- **Base**: Base stage
- **Use Case**: Environments without GPU

#### Development Stage
- **Purpose**: Development and testing
- **Additional Tools**: pytest, black, flake8, mypy, jupyter
- **Ports**: 8000, 8080, 8888, 6006
- **Default Command**: pytest

#### Production Stage
- **Purpose**: Production deployment
- **Features**: Minimal image, optimized for production
- **Health Check**: Basic import check

### Soroban Dockerfile Stages

#### Soroban Base Stage
- **Purpose**: Soroban development environment
- **Rust Version**: 1.75-slim
- **Soroban CLI**: v20.0.0
- **System Dependencies**: build-essential, pkg-config, libssl-dev

#### Development Stage
- **Purpose**: Full development environment
- **Additional Tools**: cargo-watch, cargo-expand
- **Default Command**: cargo-watch with build

#### Build Stage
- **Purpose**: Optimized build for deployment
- **Output**: WASM files in `/app/target/wasm`

#### Testing Stage
- **Purpose**: Run contract tests
- **Command**: cargo test --all-features

#### Verification Stage
- **Purpose**: Verify contract build
- **Command**: Build and verify WASM output

## Environment Configuration

### Environment Variables

#### Database Configuration
```bash
DATABASE_URL=postgresql://astroml:astroml_password@postgres:5432/astroml
```

#### Redis Configuration
```bash
REDIS_URL=redis://redis:6379/0
```

#### Stellar Configuration
```bash
STELLAR_NETWORK_PASSPHRASE=Public Global Stellar Network ; September 2015
STELLAR_HORIZON_URL=https://horizon.stellar.org
```

#### Logging Configuration
```bash
LOG_LEVEL=INFO
PYTHONPATH=/app
```

#### GPU Configuration
```bash
CUDA_VISIBLE_DEVICES=0
```

### Configuration Files

#### Docker Compose Override
Create `docker-compose.override.yml` for local development:

```yaml
version: '3.8'

services:
  postgres:
    environment:
      POSTGRES_PASSWORD: your_secure_password

  ingestion:
    environment:
      LOG_LEVEL: DEBUG
    volumes:
      - ./local_data:/app/data
```

#### Environment File
Create `.env` file for sensitive data:

```bash
POSTGRES_PASSWORD=your_secure_password
REDIS_PASSWORD=your_redis_password
STELLAR_SECRET_KEY=your_stellar_secret
```

## Common Operations

### Build Images

```bash
# Build all images
docker-compose build

# Build specific service
docker-compose build ingestion

# Build with no cache
docker-compose build --no-cache

# Build specific stage
docker build --target development -t astroml:dev .
```

### Start Services

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up postgres redis -d

# Start with profile
docker-compose --profile dev up -d

# Start with multiple profiles
docker-compose --profile dev --profile monitoring up -d
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop specific service
docker-compose stop ingestion

# Stop and remove volumes
docker-compose down -v
```

### View Logs

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs ingestion

# Follow logs
docker-compose logs -f ingestion

# View last 100 lines
docker-compose logs --tail=100 ingestion
```

### Execute Commands

```bash
# Execute command in running container
docker-compose exec ingestion bash

# Execute command in new container
docker-compose run ingestion python -m pytest

# Execute as root
docker-compose exec -u root ingestion bash
```

### Database Operations

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U astroml -d astroml

# Run migrations
docker-compose exec ingestion alembic upgrade head

# Create database backup
docker-compose exec postgres pg_dump -U astroml astroml > backup.sql

# Restore database
docker-compose exec -T postgres psql -U astroml astroml < backup.sql
```

### Redis Operations

```bash
# Connect to Redis
docker-compose exec redis redis-cli

# Flush Redis cache
docker-compose exec redis redis-cli FLUSHALL

# Monitor Redis
docker-compose exec redis redis-cli MONITOR
```

### Training Operations

```bash
# Start CPU training
docker-compose --profile cpu run training-cpu python train.py

# Start GPU training
docker-compose --profile gpu run training-gpu python train.py

# View TensorBoard
docker-compose --profile gpu up training-gpu
# Open browser to http://localhost:6006
```

### Soroban Operations

```bash
# Start Soroban development
docker-compose --profile soroban up soroban-dev -d

# Build contracts
docker-compose --profile soroban-build run soroban-build

# Test contracts
docker-compose --profile soroban-test run soroban-test

# Execute Soroban CLI
docker-compose --profile soroban run soroban-dev soroban --help
```

### Monitoring Operations

```bash
# Start monitoring stack
docker-compose --profile monitoring up -d

# Access Prometheus
# Open browser to http://localhost:9090

# Access Grafana
# Open browser to http://localhost:3000
# Default credentials: admin / admin
```

## Troubleshooting

### Common Issues

#### Container Won't Start

**Problem**: Container fails to start or crashes immediately

**Solution**:
```bash
# Check logs
docker-compose logs <service_name>

# Check container status
docker-compose ps

# Restart service
docker-compose restart <service_name>

# Rebuild image
docker-compose build --no-cache <service_name>
```

#### Database Connection Issues

**Problem**: Cannot connect to PostgreSQL

**Solution**:
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Verify database is ready
docker-compose exec postgres pg_isready -U astroml

# Check network connectivity
docker-compose exec ingestion ping postgres
```

#### Permission Issues

**Problem**: Permission denied errors

**Solution**:
```bash
# Fix volume permissions
docker-compose exec ingestion chown -R astroml:astroml /app

# Run as root
docker-compose exec -u root ingestion bash

# Check user permissions
docker-compose exec ingestion whoami
```

#### GPU Not Available

**Problem**: GPU training fails with CUDA errors

**Solution**:
```bash
# Check NVIDIA Docker installation
docker run --rm --gpus all nvidia/cuda:12.1-runtime-base-ubuntu22.04 nvidia-smi

# Verify GPU access
docker-compose --profile gpu config

# Use CPU training instead
docker-compose --profile cpu up training-cpu
```

#### Out of Memory

**Problem**: Container OOM killed

**Solution**:
```bash
# Increase Docker memory limit in Docker Desktop settings

# Check container memory usage
docker stats

# Reduce batch size in training configuration

# Use CPU training instead
docker-compose --profile cpu up training-cpu
```

#### Port Conflicts

**Problem**: Port already in use

**Solution**:
```bash
# Check what's using the port
netstat -tulpn | grep <port>

# Change port mapping in docker-compose.yml
ports:
  - "8001:8000"  # Change to different host port

# Stop conflicting service
docker-compose stop <conflicting_service>
```

### Health Checks

#### Service Health Status

```bash
# Check all service health
docker-compose ps

# Check specific service health
docker-compose exec ingestion python -c "import astroml.ingestion"

# Check PostgreSQL health
docker-compose exec postgres pg_isready -U astroml

# Check Redis health
docker-compose exec redis redis-cli ping
```

### Debug Mode

#### Enable Debug Logging

```bash
# Set log level to DEBUG
docker-compose exec ingestion bash
export LOG_LEVEL=DEBUG

# Or update docker-compose.yml
environment:
  - LOG_LEVEL=DEBUG
```

#### Interactive Debugging

```bash
# Start container with interactive shell
docker-compose run --rm ingestion bash

# Attach to running container
docker attach <container_name>

# Use docker exec for debugging
docker-compose exec ingestion python -m pdb your_script.py
```

## Advanced Usage

### Custom Networks

```yaml
networks:
  astroml-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### Resource Limits

```yaml
services:
  training-gpu:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

### Multi-Stage Builds

```bash
# Build specific stage
docker build --target development -t astroml:dev .

# Use specific stage in docker-compose
build:
  context: .
  target: development
```

### Volume Management

```bash
# List volumes
docker volume ls

# Remove unused volumes
docker volume prune

# Backup volume
docker run --rm -v astroml_postgres_data:/data -v $(pwd):/backup ubuntu tar czf /backup/postgres_backup.tar.gz /data

# Restore volume
docker run --rm -v astroml_postgres_data:/data -v $(pwd):/backup ubuntu tar xzf /backup/postgres_backup.tar.gz -C /
```

### Container Orchestration

```bash
# Scale services
docker-compose up -d --scale ingestion=3

# Update services without downtime
docker-compose up -d --no-deps --build <service>

# Rolling update
docker-compose up -d --build --no-deps ingestion
```

### Production Deployment

#### Build Production Image

```bash
# Build production image
docker-compose build production

# Tag image
docker tag astroml_production:latest your-registry/astroml:latest

# Push to registry
docker push your-registry/astroml:latest
```

#### Deploy to Production

```bash
# Use production profile
docker-compose --profile prod up -d

# Set environment variables
export DATABASE_URL=production_db_url
export REDIS_URL=production_redis_url

# Start production services
docker-compose --profile prod up -d
```

### CI/CD Integration

#### GitHub Actions Example

```yaml
name: Docker Build and Test

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build Docker images
        run: docker-compose build
      - name: Run tests
        run: docker-compose run --rm dev pytest
      - name: Build Soroban contracts
        run: docker-compose --profile soroban-build run soroban-build
```

### Security Best Practices

#### Scan Images for Vulnerabilities

```bash
# Use Trivy
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image astroml:latest

# Use Docker Scout
docker scout quickview astroml:latest
```

#### Use Non-Root Users

```dockerfile
# Already implemented in Dockerfile
RUN groupadd -r astroml && useradd -r -g astroml astroml
USER astroml
```

#### Limit Container Capabilities

```yaml
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE
```

### Performance Optimization

#### Use BuildKit

```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1

# Build with BuildKit
docker-compose build
```

#### Layer Caching

```dockerfile
# Order Dockerfile instructions to maximize cache hits
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

#### Multi-Stage Builds

```dockerfile
# Use multi-stage builds to reduce final image size
FROM base as builder
# Build steps here

FROM base as final
COPY --from=builder /app/target /app/target
```

## Maintenance

### Clean Up

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove unused networks
docker network prune

# Complete cleanup
docker system prune -a
```

### Updates

```bash
# Pull latest images
docker-compose pull

# Rebuild with latest base images
docker-compose build --pull

# Update specific service
docker-compose pull postgres
docker-compose up -d postgres
```

### Backups

#### Database Backup

```bash
# Automated backup script
docker-compose exec postgres pg_dump -U astroml astroml > backup_$(date +%Y%m%d).sql
```

#### Volume Backup

```bash
# Backup all volumes
for vol in $(docker volume ls -q); do
  docker run --rm -v $vol:/data -v $(pwd):/backup ubuntu tar czf /backup/${vol}.tar.gz /data
done
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/jaynomyaro/astroml/issues
- Documentation: https://github.com/jaynomyaro/astroml/docs
- Docker Documentation: https://docs.docker.com

## License

This Docker setup is part of the AstroML project and is licensed under the MIT License.
